"""
PKCE (Proof Key for Code Exchange) verification
RFC 7636 implementation for OAuth 2.1
"""

import hashlib
import base64


def verify_pkce_challenge(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """
    Verify PKCE code challenge against code verifier.

    Args:
        code_verifier: Plain text verifier sent in token request
        code_challenge: Challenge sent in authorization request
        method: Challenge method (only S256 supported per MCP spec)

    Returns:
        True if verification succeeds, False otherwise

    Spec Requirements:
    - MUST support S256 (SHA256)
    - code_challenge = BASE64URL(SHA256(ASCII(code_verifier)))
    """
    if method != "S256":
        # MCP spec requires S256
        return False

    # Generate challenge from verifier
    verifier_bytes = code_verifier.encode('ascii')
    sha256_hash = hashlib.sha256(verifier_bytes).digest()
    computed_challenge = base64.urlsafe_b64encode(sha256_hash).decode('ascii').rstrip('=')

    return computed_challenge == code_challenge


def generate_code_challenge(code_verifier: str) -> str:
    """
    Generate S256 code challenge from verifier (for testing).

    Args:
        code_verifier: Plain text verifier

    Returns:
        Base64URL-encoded SHA256 hash
    """
    verifier_bytes = code_verifier.encode('ascii')
    sha256_hash = hashlib.sha256(verifier_bytes).digest()
    return base64.urlsafe_b64encode(sha256_hash).decode('ascii').rstrip('=')
