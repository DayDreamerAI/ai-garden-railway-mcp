"""
JWT Token Manager for OAuth 2.1
Handles access token generation and validation
"""

import jwt
import time
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, UTC


class TokenManager:
    """Manages JWT access token creation and validation."""

    def __init__(self, secret_key: str, issuer: str, token_expiry: int = 3600):
        """
        Initialize token manager.

        Args:
            secret_key: Secret key for JWT signing (HS256)
            issuer: OAuth issuer URL
            token_expiry: Token lifetime in seconds (default 1 hour)
        """
        self.secret_key = secret_key
        self.issuer = issuer
        self.token_expiry = token_expiry
        self.algorithm = "HS256"
        self.audience = "daydreamer-mcp"

    def create_access_token(self, client_id: str, scope: str = "mcp:read mcp:write") -> Dict[str, Any]:
        """
        Create JWT access token for client.

        Args:
            client_id: Client identifier
            scope: Space-separated scope string

        Returns:
            Token response dict with access_token, token_type, expires_in
        """
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=self.token_expiry)

        payload = {
            "iss": self.issuer,
            "sub": client_id,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "scope": scope,
            "jti": secrets.token_urlsafe(16)  # Unique token ID
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.token_expiry,
            "scope": scope
        }

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT access token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_client_id(self, token: str) -> Optional[str]:
        """
        Extract client_id from valid token.

        Args:
            token: JWT token string

        Returns:
            Client ID if token valid, None otherwise
        """
        payload = self.validate_token(token)
        return payload.get("sub") if payload else None
