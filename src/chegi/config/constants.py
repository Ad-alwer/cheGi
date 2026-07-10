from typing import Dict, List, Set, Tuple

# Security Constants (Immutable)
DEFAULT_SENSITIVE_PATTERNS: Tuple[str, ...] = (
    ".env*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "id_ecdsa*",
    "id_ed25519*",
    "*.pk8",
    "*secret*",
    "credentials.json",
    "*.jwt",
    "*.token",
    ".npmrc",
    ".dockercfg",
    "docker.json",
    "service-account*.json",
    "aws-credentials.json",
    "*.credential",
    "*.cred",
    "*.passwd",
)

# Supported Package Managers for Mirrors
SUPPORTED_PMS: Set[str] = {"pip", "npm", "yarn", "gem", "cargo", "composer"}

# Default settings
DEFAULT_EXCLUDES: List[str] = [
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".tox",
    "__pycache__",
    ".idea",
    ".vscode",
    ".git",
]
DEFAULT_MAX_DEPTH: int = 3
DEFAULT_MCTS: int = 10

# Default mirrors dict
DEFAULT_MIRRORS: Dict[str, List[str]] = {}

# Internal / Branding Constants (Not modifiable by user)
GITIGNORE_COMMIT_MESSAGE: str = "chore(gitignore): auto add .gitignore via cheGi 🐆"
