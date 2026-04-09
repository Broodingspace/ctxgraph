"""Authentication helpers for the sample project."""

import hashlib
import os

from .models import User


class AuthError(Exception):
    """Raised when authentication fails."""


class TokenStore:
    """In-memory token storage."""

    def __init__(self) -> None:
        """Initialize empty token store."""
        self._tokens: dict[str, int] = {}  # token -> user_id

    def store(self, token: str, user_id: int) -> None:
        """Store an authentication token.

        Args:
            token: Token string.
            user_id: User ID the token belongs to.
        """
        self._tokens[token] = user_id

    def lookup(self, token: str) -> int | None:
        """Look up the user ID for a token.

        Args:
            token: Token to look up.

        Returns:
            User ID or None if token is invalid.
        """
        return self._tokens.get(token)

    def revoke(self, token: str) -> bool:
        """Revoke a token.

        Args:
            token: Token to revoke.

        Returns:
            True if token existed and was revoked.
        """
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with a random salt.

    Args:
        password: Plain-text password.
        salt: Optional salt. If not provided, a random salt is generated.

    Returns:
        Tuple of (hashed_password, salt).
    """
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return hashed, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a password against a stored hash.

    Args:
        password: Plain-text password to verify.
        hashed: Stored password hash.
        salt: Salt used when hashing.

    Returns:
        True if password matches.
    """
    candidate, _ = hash_password(password, salt)
    return candidate == hashed


def generate_token() -> str:
    """Generate a random authentication token.

    Returns:
        Hex token string.
    """
    return os.urandom(32).hex()


def authenticate(user: User, password: str, stored_hash: str, salt: str) -> str:
    """Authenticate a user and return a session token.

    Args:
        user: User attempting authentication.
        password: Plain-text password.
        stored_hash: Stored password hash to verify against.
        salt: Salt used when the password was hashed.

    Returns:
        Session token string.

    Raises:
        AuthError: If authentication fails.
    """
    if not verify_password(password, stored_hash, salt):
        raise AuthError(f"Invalid credentials for user {user.id}")
    return generate_token()
