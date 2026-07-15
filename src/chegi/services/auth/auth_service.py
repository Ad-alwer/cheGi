"""Service for managing Git provider authentication tokens."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken

from chegi.config.global_config import GLOBAL_CONFIG_DIR

from .constants import (
    AUTH_DATA_FILE,
    AUTH_DIR_NAME,
    AUTH_KEY_FILE,
    PROVIDER_INFO,
    TOKEN_PREFIX_MAP,
    VALIDATION_ENDPOINTS,
)
from .exceptions import AuthError, TokenValidationError
from .models import AuthProvider, Credential

AUTH_DIR: Path = GLOBAL_CONFIG_DIR / AUTH_DIR_NAME


class AuthService:
    """Manages encrypted token storage and credential helper for Git providers."""

    # ── Path helpers ───────────────────────────────────────────

    @classmethod
    def _key_path(cls) -> Path:
        """Returns the path to the Fernet key file."""
        return AUTH_DIR / AUTH_KEY_FILE

    @classmethod
    def _data_path(cls) -> Path:
        """Returns the path to the encrypted credentials file."""
        return AUTH_DIR / AUTH_DATA_FILE

    # ── Public API ──────────────────────────────────────────────

    @classmethod
    def login(
        cls,
        provider: AuthProvider,
        label: str,
        username: str,
        token: str,
        api_url: str = "",
        make_default: bool = True,
        username_from_api: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> Credential:
        """Validates and stores a new credential.

        Args:
            provider: The Git provider.
            label: Human-friendly label for this account.
            username: Git username.
            token: Personal access token.
            api_url: Base API URL (for self-hosted GitLab).
            make_default: Whether to set as default for its host.
            username_from_api: Pre-validated username (skips validation if given with scopes).
            scopes: Pre-validated scopes (skips validation if given with username_from_api).

        Returns:
            The stored Credential.

        Raises:
            TokenValidationError: If the token is invalid.
        """
        host = PROVIDER_INFO[provider]["default_host"]  # type: ignore[arg-type]
        if provider == AuthProvider.GITLAB and api_url:
            host = urllib.parse.urlparse(api_url).hostname or host

        # Validate before storing (skip if pre-validated data provided)
        if username_from_api is not None and scopes is not None:
            effective_username = username_from_api or username
        else:
            username_from_api, scopes = cls.validate_token(provider, token, api_url)
            effective_username = username_from_api or username

        cred = Credential(
            provider=provider,
            label=label,
            username=effective_username,
            token=token,
            host=host,
            api_url=api_url,
            is_default=make_default,
            scope_hint=", ".join(scopes) if scopes else "",
        )

        data = cls._load_data()
        key = cls._cred_key(provider, label)

        # If making this default, un-default others for the same host
        if make_default:
            for existing_key, existing_cred in data.items():
                if existing_cred["host"] == host:
                    existing_cred["is_default"] = False

        data[key] = {
            "provider": provider.value,
            "label": label,
            "username": effective_username,
            "token": token,
            "host": host,
            "api_url": api_url,
            "is_default": make_default,
            "scope_hint": ", ".join(scopes) if scopes else "",
        }
        cls._save_data(data)

        return cred

    @classmethod
    def get_credential_by_label(cls, label: str) -> Optional[Credential]:
        """Finds a stored credential by its label.

        Args:
            label: The account label to find.

        Returns:
            The Credential, or None if not found.
        """
        data = cls._load_data()
        key = cls._find_key_by_label(data, label)
        if not key:
            return None
        return cls._dict_to_cred(data[key])

    @classmethod
    def logout(cls, label: str) -> bool:
        """Removes a stored credential by label.

        Args:
            label: The account label to remove.

        Returns:
            True if removed, False if not found.
        """
        data = cls._load_data()
        key = cls._find_key_by_label(data, label)
        if not key:
            return False
        del data[key]
        cls._save_data(data)
        return True

    @classmethod
    def status(cls) -> List[Credential]:
        """Returns all stored credentials.

        Returns:
            List of Credential objects.
        """
        data = cls._load_data()
        return [cls._dict_to_cred(v) for v in data.values()]

    @classmethod
    def switch(cls, label: str) -> Optional[Credential]:
        """Makes the credential with the given label the default for its host.

        Args:
            label: The account label to make default.

        Returns:
            The updated Credential, or None if not found.
        """
        data = cls._load_data()
        target_key = cls._find_key_by_label(data, label)
        if not target_key:
            return None

        target = data[target_key]
        host = target["host"]

        # Un-default all for this host, then set target as default
        for existing_key, existing_cred in data.items():
            if existing_cred["host"] == host:
                existing_cred["is_default"] = False

        target["is_default"] = True
        cls._save_data(data)
        return cls._dict_to_cred(target)

    @classmethod
    def get_credential_for_host(cls, host: str) -> Optional[Credential]:
        """Finds the default credential for a given Git host.

        Called by the Git credential helper (chegi auth get-credential).

        Args:
            host: Git hostname (e.g. github.com).

        Returns:
            The default Credential for that host, or None.
        """
        data = cls._load_data()
        for cred_dict in data.values():
            if cred_dict["host"] == host and cred_dict.get("is_default", False):
                return cls._dict_to_cred(cred_dict)
        # Fallback: first credential for this host
        for cred_dict in data.values():
            if cred_dict["host"] == host:
                return cls._dict_to_cred(cred_dict)
        return None

    @classmethod
    def get_token(cls, provider: AuthProvider) -> Optional[str]:
        """Returns the raw token for the default credential of a provider.

        Args:
            provider: The Git provider.

        Returns:
            The token string, or None.
        """
        creds = cls.status()
        for c in creds:
            if c.provider == provider and c.is_default:
                return c.token
        for c in creds:
            if c.provider == provider:
                return c.token
        return None

    # ── Token validation ───────────────────────────────────────

    @classmethod
    def validate_token(
        cls, provider: AuthProvider, token: str, api_url: str = ""
    ) -> Tuple[Optional[str], List[str]]:
        """Validates a token against the provider's API.

        Args:
            provider: The Git provider.
            token: The token to validate.
            api_url: Base API URL (for self-hosted GitLab).

        Returns:
            Tuple of (username, list of scope strings).

        Raises:
            TokenValidationError: If the token is invalid or unreachable.
        """
        if not api_url:
            info = PROVIDER_INFO[provider]
            api_url = str(info["default_api_url"])  # type: ignore[arg-type]

        endpoint = VALIDATION_ENDPOINTS[provider]
        url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"

        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "cheGi",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read())
                header_scopes = resp.headers.get("X-OAuth-Scopes", "")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise TokenValidationError(
                    "Token is invalid or has been revoked."
                ) from e
            raise TokenValidationError(f"API returned HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, OSError) as e:
            raise TokenValidationError(f"Could not reach {url}: {e}") from e

        # Extract username
        username: Optional[str] = None
        if provider == AuthProvider.GITHUB:
            username = body.get("login")
        elif provider == AuthProvider.GITLAB:
            username = body.get("username")

        # Detect scopes from response
        scopes: List[str] = []
        if provider == AuthProvider.GITHUB:
            scopes = [s.strip() for s in header_scopes.split(",") if s.strip()]
        elif provider == AuthProvider.GITLAB:
            scopes = body.get("scopes", [])

        return username, scopes

    @classmethod
    def check_required_scopes(
        cls, provider: AuthProvider, actual_scopes: List[str]
    ) -> List[str]:
        """Checks whether the required scopes for a provider are present.

        Args:
            provider: The Git provider.
            actual_scopes: The list of scopes from the validated token.

        Returns:
            List of missing required scope strings (empty if all present).
        """
        info = PROVIDER_INFO.get(provider, {})
        required: List[str] = list(info.get("scopes", []))  # type: ignore[arg-type]
        if not required:
            return []
        actual_lower = [s.lower() for s in actual_scopes]
        return [s for s in required if s.lower() not in actual_lower]

    @classmethod
    def validate_github_scopes(cls, token: str) -> List[str]:
        """Validates a GitHub token and returns its scopes.

        Args:
            token: The GitHub token.

        Returns:
            List of scope strings from the X-OAuth-Scopes header.
        """
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "cheGi",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                header = resp.headers.get("X-OAuth-Scopes", "")
                return [s.strip() for s in header.split(",") if s.strip()]
        except Exception:
            return []

    @classmethod
    def detect_provider(cls, token: str) -> Optional[AuthProvider]:
        """Detects the Git provider from the token prefix.

        Args:
            token: The token string.

        Returns:
            AuthProvider if detected, None otherwise.
        """
        for prefix, provider in TOKEN_PREFIX_MAP.items():
            if token.startswith(prefix):
                return provider
        return None

    # ── Encryption ─────────────────────────────────────────────

    @classmethod
    def _ensure_key(cls) -> bytes:
        """Loads or generates a Fernet encryption key.

        Returns:
            The key as bytes.
        """
        os.makedirs(str(AUTH_DIR), exist_ok=True)
        key_path = cls._key_path()
        if key_path.is_file():
            return key_path.read_bytes()
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        return key

    @classmethod
    def _encrypt(cls, data: Dict[str, Any]) -> str:
        """Encrypts a dict to an encrypted string.

        Args:
            data: The data to encrypt.

        Returns:
            Base64-encoded encrypted string.
        """
        key = cls._ensure_key()
        fernet = Fernet(key)
        raw = json.dumps(data, indent=2).encode("utf-8")
        return fernet.encrypt(raw).decode("utf-8")

    @classmethod
    def _decrypt(cls, payload: str) -> Dict[str, Any]:
        """Decrypts an encrypted string back to a dict.

        Args:
            payload: The encrypted string.

        Returns:
            The decrypted data.
        """
        key = cls._ensure_key()
        fernet = Fernet(key)
        try:
            raw = fernet.decrypt(payload.encode("utf-8"))
            return json.loads(raw.decode("utf-8"))
        except InvalidToken as exc:
            raise AuthError("Auth data is corrupted or key has changed.") from exc

    # ── Data persistence ───────────────────────────────────────

    @classmethod
    def _load_data(cls) -> Dict[str, Any]:
        """Loads and decrypts the credentials file.

        Returns:
            Dict of credential key → credential dict.
        """
        data_path = cls._data_path()
        if not data_path.is_file():
            return {}
        try:
            encrypted = data_path.read_text().strip()
            if not encrypted:
                return {}
            return cls._decrypt(encrypted)
        except Exception:
            return {}

    @classmethod
    def _save_data(cls, data: Dict[str, Any]) -> None:
        """Encrypts and writes the credentials file.

        Args:
            data: The credentials dict to save.
        """
        os.makedirs(str(AUTH_DIR), exist_ok=True)
        encrypted = cls._encrypt(data)
        cls._data_path().write_text(encrypted)

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _cred_key(provider: AuthProvider, label: str) -> str:
        """Builds a storage key for a credential.

        Args:
            provider: The Git provider.
            label: The account label.

        Returns:
            A unique key string.
        """
        return f"{provider.value}-{label}"

    @staticmethod
    def _find_key_by_label(data: Dict[str, Any], label: str) -> Optional[str]:
        """Finds a credential key by its label.

        Args:
            data: The credentials dict.
            label: The label to search for.

        Returns:
            The key string, or None.
        """
        for key, cred in data.items():
            if cred.get("label") == label:
                return key
        return None

    @staticmethod
    def _dict_to_cred(d: Dict[str, Any]) -> Credential:
        """Converts a stored dict back to a Credential.

        Args:
            d: The stored dict.

        Returns:
            A Credential object.
        """
        return Credential(
            provider=AuthProvider(d.get("provider", "github")),
            label=d.get("label", ""),
            username=d.get("username", ""),
            token=d.get("token", ""),
            host=d.get("host", ""),
            api_url=d.get("api_url", ""),
            is_default=d.get("is_default", False),
            scope_hint=d.get("scope_hint", ""),
        )
