"""Custom exceptions for the auth module."""


class AuthError(Exception):
    """Base exception for all auth-related errors."""

    pass


class TokenNotFoundError(AuthError):
    """Raised when no token is found for the requested provider or host."""

    pass


class TokenValidationError(AuthError):
    """Raised when token validation fails (invalid, expired, or insufficient scopes)."""

    pass
