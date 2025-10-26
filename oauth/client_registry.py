"""
OAuth Client Registry
Implements Dynamic Client Registration (RFC 7591)
"""

import secrets
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC


@dataclass
class OAuthClient:
    """OAuth 2.1 client registration data."""
    client_id: str
    client_secret: str
    client_name: str
    redirect_uris: List[str]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    registration_access_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON responses."""
        return asdict(self)


class ClientRegistry:
    """
    In-memory OAuth client registry with Dynamic Client Registration.

    Note: For production with multiple instances, consider persistent storage (Neo4j).
    """

    def __init__(self):
        self.clients: Dict[str, OAuthClient] = {}
        self.authorization_codes: Dict[str, Dict] = {}  # code -> {client_id, code_challenge, expires_at, redirect_uri}

    def register_client(self, client_name: str, redirect_uris: List[str]) -> OAuthClient:
        """
        Register new OAuth client (RFC 7591).

        Args:
            client_name: Human-readable client name
            redirect_uris: List of allowed redirect URIs

        Returns:
            OAuthClient with generated credentials
        """
        client = OAuthClient(
            client_id=f"mcp_{secrets.token_urlsafe(16)}",
            client_secret=secrets.token_urlsafe(32),
            client_name=client_name,
            redirect_uris=redirect_uris
        )

        self.clients[client.client_id] = client
        return client

    def get_client(self, client_id: str) -> Optional[OAuthClient]:
        """
        Retrieve client by ID.

        Args:
            client_id: Client identifier

        Returns:
            OAuthClient if found, None otherwise
        """
        return self.clients.get(client_id)

    def validate_client(self, client_id: str, client_secret: str) -> bool:
        """
        Validate client credentials.

        Args:
            client_id: Client identifier
            client_secret: Client secret

        Returns:
            True if credentials valid, False otherwise
        """
        client = self.get_client(client_id)
        return client is not None and client.client_secret == client_secret

    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """
        Validate redirect URI against registered URIs.

        Args:
            client_id: Client identifier
            redirect_uri: URI to validate

        Returns:
            True if URI registered for client, False otherwise
        """
        client = self.get_client(client_id)
        return client is not None and redirect_uri in client.redirect_uris

    def create_authorization_code(
        self,
        client_id: str,
        code_challenge: str,
        code_challenge_method: str,
        redirect_uri: str,
        expiry_seconds: int = 600
    ) -> str:
        """
        Generate authorization code for PKCE flow.

        Args:
            client_id: Client identifier
            code_challenge: PKCE code challenge
            code_challenge_method: Challenge method (must be S256)
            redirect_uri: Redirect URI for this authorization
            expiry_seconds: Code lifetime (default 10 minutes)

        Returns:
            Authorization code
        """
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC).timestamp() + expiry_seconds

        self.authorization_codes[code] = {
            "client_id": client_id,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "redirect_uri": redirect_uri,
            "expires_at": expires_at,
            "used": False
        }

        return code

    def validate_authorization_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str
    ) -> Optional[Dict]:
        """
        Validate authorization code and return PKCE data.

        Args:
            code: Authorization code
            client_id: Client identifier
            redirect_uri: Redirect URI

        Returns:
            Code data if valid and not expired/used, None otherwise
        """
        code_data = self.authorization_codes.get(code)

        if not code_data:
            return None

        # Check expiry
        if datetime.now(UTC).timestamp() > code_data["expires_at"]:
            del self.authorization_codes[code]
            return None

        # Check if already used
        if code_data["used"]:
            return None

        # Validate client_id and redirect_uri match
        if code_data["client_id"] != client_id or code_data["redirect_uri"] != redirect_uri:
            return None

        # Mark as used
        code_data["used"] = True

        return code_data

    def cleanup_expired_codes(self):
        """Remove expired authorization codes."""
        now = datetime.now(UTC).timestamp()
        expired = [code for code, data in self.authorization_codes.items() if data["expires_at"] < now]
        for code in expired:
            del self.authorization_codes[code]
