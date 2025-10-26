"""
OAuth 2.1 Module for Daydreamer MCP Server
Implements MCP Authorization Specification 2025-03-26

Components:
- token_manager: JWT generation and validation
- pkce: PKCE S256 verification
- client_registry: Dynamic client registration storage
- server: OAuth endpoint handlers
"""

from .token_manager import TokenManager
from .client_registry import ClientRegistry
from .pkce import verify_pkce_challenge
from .server import setup_oauth_routes

__all__ = [
    "TokenManager",
    "ClientRegistry",
    "verify_pkce_challenge",
    "setup_oauth_routes",
]
