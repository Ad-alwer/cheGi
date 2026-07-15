"""Constants for the auth module."""

from typing import Dict

from .models import AuthProvider

AUTH_DIR_NAME: str = "auth"
AUTH_KEY_FILE: str = "auth.key"
AUTH_DATA_FILE: str = "auth.json"

# Mapping of provider → (label, default host, default API URL, required scopes)
PROVIDER_INFO: Dict[AuthProvider, Dict[str, object]] = {
    AuthProvider.GITHUB: {
        "label": "GitHub",
        "default_host": "github.com",
        "default_api_url": "https://api.github.com",
        "doc_url": "https://github.com/settings/tokens/new",
        "scopes": ["repo", "read:user", "workflow"],
    },
    AuthProvider.GITLAB: {
        "label": "GitLab",
        "default_host": "gitlab.com",
        "default_api_url": "https://gitlab.com",
        "doc_url": "https://gitlab.com/-/user_settings/personal_access_tokens",
        "scopes": ["api", "read_user"],
    },
}

# Token prefix → provider detection magic
TOKEN_PREFIX_MAP: Dict[str, AuthProvider] = {
    "ghp_": AuthProvider.GITHUB,
    "gho_": AuthProvider.GITHUB,
    "github_pat_": AuthProvider.GITHUB,
    "glpat-": AuthProvider.GITLAB,
}

# Endpoints for token validation per provider
VALIDATION_ENDPOINTS: Dict[AuthProvider, str] = {
    AuthProvider.GITHUB: "/user",
    AuthProvider.GITLAB: "/api/v4/user",
}

# Git credential helper config prefix
CREDENTIAL_HELPER_CMD: str = "chegi auth get-credential"
