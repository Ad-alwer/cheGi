"""Default values and constants for the init/project module."""

from typing import Dict, List

DEFAULT_CONFIG: Dict[str, object] = {
    "exclude_dirs": [
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".tox",
        "__pycache__",
        ".idea",
        ".vscode",
        ".git",
    ],
    "max_depth": 3,
    "mcts": 10,
    "mirrors": {},
    "guard_rules": [],
    "guard_excludes": [],
}

DEFAULT_GUARD_RULES: Dict[str, List[str]] = {
    "patterns": [
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
    ],
    "exclude_patterns": [
        "*.example.env",
        "*.sample.key",
        "*.test.env",
        "docs/*",
    ],
}

DEFAULT_CHEGIIGNORE: str = """# cheGi ignore patterns
# Files and directories matching these patterns will be skipped during scans.
# Syntax follows .gitignore rules (glob patterns).

# Build output
build/
dist/
*.egg-info/

# Dependencies
node_modules/
vendor/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""

CHEGI_DIR_NAME: str = ".chegi"
CONFIG_FILE_NAME: str = "config.json"
GUARD_RULES_FILE_NAME: str = "guard-rules.json"
CHEGIIGNORE_FILE_NAME: str = ".chegiignore"
