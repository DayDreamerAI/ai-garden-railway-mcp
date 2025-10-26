"""
OAuth 2.1 Server Endpoints for MCP
Implements MCP Authorization Specification 2025-03-26
"""

import json
import logging
from urllib.parse import urlencode, urlparse, parse_qs
from aiohttp import web

from .token_manager import TokenManager
from .client_registry import ClientRegistry
from .pkce import verify_pkce_challenge

logger = logging.getLogger(__name__)


async def handle_discovery(request: web.Request) -> web.Response:
    """
    OAuth 2.0 Authorization Server Metadata (RFC 8414).
    GET /.well-known/oauth-authorization-server
    """
    base_url = request.app["oauth_issuer"]

    metadata = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "registration_endpoint": f"{base_url}/register",
        "grant_types_supported": ["authorization_code"],
        "response_types_supported": ["code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": ["mcp:read", "mcp:write"],
        "service_documentation": "https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization"
    }

    return web.Response(
        text=json.dumps(metadata, indent=2),
        content_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
    )


async def handle_protected_resource(request: web.Request) -> web.Response:
    """
    OAuth 2.0 Protected Resource Metadata (RFC 8414 Section 5).
    GET /.well-known/oauth-protected-resource

    Indicates that this server is both an Authorization Server AND a Resource Server.
    """
    base_url = request.app["oauth_issuer"]

    metadata = {
        "resource": base_url,
        "authorization_servers": [base_url],
        "scopes_supported": ["mcp:read", "mcp:write"],
        "bearer_methods_supported": ["header"],
        "resource_signing_alg_values_supported": ["HS256"],
        "resource_documentation": "https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization"
    }

    return web.Response(
        text=json.dumps(metadata, indent=2),
        content_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
    )


async def handle_register(request: web.Request) -> web.Response:
    """
    Dynamic Client Registration (RFC 7591).
    POST /register
    """
    registry: ClientRegistry = request.app["oauth_registry"]

    try:
        data = await request.json()
    except Exception as e:
        return web.json_response(
            {"error": "invalid_request", "error_description": "Invalid JSON"},
            status=400
        )

    # Extract client metadata
    client_name = data.get("client_name", "Unnamed Client")
    redirect_uris = data.get("redirect_uris", [])

    # Validate redirect_uris
    if not redirect_uris or not isinstance(redirect_uris, list):
        return web.json_response(
            {"error": "invalid_redirect_uri", "error_description": "redirect_uris required and must be array"},
            status=400
        )

    # Validate redirect URI security (HTTPS or localhost only)
    for uri in redirect_uris:
        parsed = urlparse(uri)
        if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname == "localhost"):
            if not parsed.hostname.endswith(".claude.ai"):  # Allow Claude callback
                return web.json_response(
                    {"error": "invalid_redirect_uri", "error_description": "Redirect URIs must use HTTPS (except localhost)"},
                    status=400
                )

    # Register client
    client = registry.register_client(client_name, redirect_uris)

    logger.info(f"OAuth client registered: {client.client_id} ({client_name})")

    # Return registration response
    response = client.to_dict()
    response["registration_client_uri"] = f"{request.app['oauth_issuer']}/register/{client.client_id}"

    return web.json_response(response, status=201)


async def handle_authorize(request: web.Request) -> web.Response:
    """
    Authorization Endpoint (OAuth 2.1 with PKCE).
    GET /authorize?response_type=code&client_id=...&redirect_uri=...&code_challenge=...&code_challenge_method=S256&state=...
    """
    registry: ClientRegistry = request.app["oauth_registry"]

    # Parse query parameters
    response_type = request.query.get("response_type")
    client_id = request.query.get("client_id")
    redirect_uri = request.query.get("redirect_uri")
    code_challenge = request.query.get("code_challenge")
    code_challenge_method = request.query.get("code_challenge_method")
    state = request.query.get("state", "")

    # Validate required parameters
    if not all([response_type, client_id, redirect_uri, code_challenge, code_challenge_method]):
        return web.json_response(
            {"error": "invalid_request", "error_description": "Missing required parameters"},
            status=400
        )

    # Validate response_type
    if response_type != "code":
        return web.json_response(
            {"error": "unsupported_response_type", "error_description": "Only 'code' response_type supported"},
            status=400
        )

    # Validate code_challenge_method
    if code_challenge_method != "S256":
        return web.json_response(
            {"error": "invalid_request", "error_description": "Only S256 code_challenge_method supported"},
            status=400
        )

    # Validate client exists
    client = registry.get_client(client_id)
    if not client:
        return web.json_response(
            {"error": "invalid_client", "error_description": "Unknown client_id"},
            status=401
        )

    # Validate redirect_uri
    if not registry.validate_redirect_uri(client_id, redirect_uri):
        return web.json_response(
            {"error": "invalid_request", "error_description": "Invalid redirect_uri for client"},
            status=400
        )

    # Generate authorization code
    code = registry.create_authorization_code(
        client_id=client_id,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        redirect_uri=redirect_uri
    )

    logger.info(f"Authorization code issued for client {client_id}")

    # Simplified flow: Auto-approve (no user interaction for personal server)
    # In production, this would render a consent screen

    # Redirect back to client with code
    callback_params = {
        "code": code,
        "state": state
    }

    callback_url = f"{redirect_uri}?{urlencode(callback_params)}"

    return web.Response(
        status=302,
        headers={"Location": callback_url}
    )


async def handle_token(request: web.Request) -> web.Response:
    """
    Token Endpoint (OAuth 2.1).
    POST /token

    Supports:
    - authorization_code grant (with PKCE verification)
    """
    registry: ClientRegistry = request.app["oauth_registry"]
    token_mgr: TokenManager = request.app["oauth_token_manager"]

    # Parse form data
    try:
        data = await request.post()
    except Exception as e:
        return web.json_response(
            {"error": "invalid_request", "error_description": "Invalid form data"},
            status=400
        )

    grant_type = data.get("grant_type")

    # Validate grant_type
    if grant_type != "authorization_code":
        return web.json_response(
            {"error": "unsupported_grant_type", "error_description": "Only authorization_code grant supported"},
            status=400
        )

    # Extract parameters
    code = data.get("code")
    redirect_uri = data.get("redirect_uri")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")
    code_verifier = data.get("code_verifier")

    # Validate required parameters
    if not all([code, redirect_uri, client_id, client_secret, code_verifier]):
        return web.json_response(
            {"error": "invalid_request", "error_description": "Missing required parameters"},
            status=400
        )

    # Validate client credentials
    if not registry.validate_client(client_id, client_secret):
        return web.json_response(
            {"error": "invalid_client", "error_description": "Invalid client credentials"},
            status=401
        )

    # Validate authorization code
    code_data = registry.validate_authorization_code(code, client_id, redirect_uri)
    if not code_data:
        return web.json_response(
            {"error": "invalid_grant", "error_description": "Invalid, expired, or already used authorization code"},
            status=400
        )

    # Verify PKCE challenge
    if not verify_pkce_challenge(code_verifier, code_data["code_challenge"], code_data["code_challenge_method"]):
        return web.json_response(
            {"error": "invalid_grant", "error_description": "PKCE verification failed"},
            status=400
        )

    # Generate access token
    token_response = token_mgr.create_access_token(client_id)

    logger.info(f"Access token issued for client {client_id}")

    return web.json_response(token_response)


def setup_oauth_routes(app: web.Application):
    """
    Setup OAuth 2.1 routes in aiohttp application.

    Args:
        app: aiohttp Application instance
    """
    # Discovery endpoints (RFC 8414)
    app.router.add_get("/.well-known/oauth-authorization-server", handle_discovery)
    app.router.add_get("/.well-known/oauth-protected-resource", handle_protected_resource)

    # OAuth endpoints
    app.router.add_post("/register", handle_register)
    app.router.add_get("/authorize", handle_authorize)
    app.router.add_post("/token", handle_token)

    logger.info("OAuth 2.1 routes configured (AS + RS metadata)")
