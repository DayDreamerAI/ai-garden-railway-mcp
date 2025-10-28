"""
JWT Token Manager for OAuth 2.1
Handles access token generation and validation
"""

import jwt
import time
import secrets
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, UTC

logger = logging.getLogger(__name__)


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

    def validate_token_detailed(self, token: str) -> Tuple[Optional[Dict[str, Any]], str, Optional[Dict[str, Any]]]:
        """
        Validate JWT access token with detailed failure reasons (Issue #12 debugging).

        Args:
            token: JWT token string

        Returns:
            Tuple of (payload, reason, token_info)
            - payload: Decoded payload if valid, None otherwise
            - reason: "valid", "expired", "invalid_signature", "invalid_claims", "malformed"
            - token_info: Partial token info for debugging (iat, exp, jti) even if invalid
        """
        token_info = None

        try:
            # First, decode WITHOUT verification to extract token metadata
            try:
                unverified = jwt.decode(token, options={"verify_signature": False})
                token_info = {
                    "client_id": unverified.get("sub", "unknown"),
                    "issued_at": unverified.get("iat"),
                    "expires_at": unverified.get("exp"),
                    "token_id": unverified.get("jti", "unknown")[:8],
                    "scope": unverified.get("scope", "unknown")
                }

                # Calculate age
                if token_info["issued_at"] and token_info["expires_at"]:
                    now = int(datetime.now(UTC).timestamp())
                    age = now - token_info["issued_at"]
                    time_until_expiry = token_info["expires_at"] - now
                    token_info["age_seconds"] = age
                    token_info["time_until_expiry"] = time_until_expiry

            except Exception as e:
                logger.warning(f"⚠️ Failed to decode token metadata: {e}")

            # Now validate with full verification
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience
            )

            logger.debug(f"✅ Token validated: client={payload.get('sub')} jti={payload.get('jti', '')[:8]}")
            return payload, "valid", token_info

        except jwt.ExpiredSignatureError:
            logger.warning(f"🔒 Token expired | client={token_info.get('client_id') if token_info else 'unknown'} | "
                          f"age={token_info.get('age_seconds')}s | "
                          f"expired_by={abs(token_info.get('time_until_expiry', 0))}s")
            return None, "expired", token_info

        except jwt.InvalidSignatureError:
            logger.warning(f"🔒 Invalid signature | client={token_info.get('client_id') if token_info else 'unknown'}")
            return None, "invalid_signature", token_info

        except jwt.InvalidIssuerError:
            logger.warning(f"🔒 Invalid issuer | expected={self.issuer}")
            return None, "invalid_claims", token_info

        except jwt.InvalidAudienceError:
            logger.warning(f"🔒 Invalid audience | expected={self.audience}")
            return None, "invalid_claims", token_info

        except jwt.DecodeError as e:
            logger.warning(f"🔒 Malformed token | error={e}")
            return None, "malformed", token_info

        except Exception as e:
            logger.error(f"❌ Unexpected token validation error: {e}")
            return None, "error", token_info

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
