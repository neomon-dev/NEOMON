"""Authentication Security & Cryptographic Utilities (Milestone 10).

Standardized, secure implementations:
- NIST-compliant PBKDF2-HMAC-SHA256 password hashing (600,000 iterations).
- Constant-time password verification with secrets.compare_digest.
- 256-bit cryptographically secure token generation for sessions and invitations.
- SHA-256 token hashing for secure database storage.
- Password strength validation and email format checks.
"""

import hashlib
import re
import secrets
from typing import Tuple

PBKDF2_ITERATIONS = 600_000
PBKDF2_ALGORITHM = "sha256"


def hash_password(password: str) -> str:
    """Hash a password using salted PBKDF2-HMAC-SHA256 with 600,000 iterations."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify password against stored hash using constant-time comparison."""
    if not plain_password or not password_hash:
        return False
    try:
        parts = password_hash.split("$")
        if len(parts) != 4:
            return False
        scheme, iter_str, salt_hex, hash_hex = parts
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(hash_hex)

        actual_dk = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return secrets.compare_digest(actual_dk, expected_dk)
    except Exception:
        return False


def generate_secure_token() -> str:
    """Generate a 256-bit URL-safe cryptographically secure random token."""
    return secrets.token_urlsafe(32)


generate_session_token = generate_secure_token


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for persistent database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password against complexity and length requirements."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numerical digit."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    return True, ""


def validate_email_format(email: str) -> bool:
    """Validate email format."""
    if not email or len(email) > 254:
        return False
    # Standard email regex pattern
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))
