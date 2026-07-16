"""Constants for the clone service."""

from typing import Dict, List

# Files used for smart technology detection
DETECTION_RULES: Dict[str, str] = {
    "package.json": "javascript",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "Pipfile": "python",
    "Gemfile": "ruby",
    "build.gradle": "java",
    "CMakeLists.txt": "cpp",
    "composer.json": "php",
}

# Files that indicate a technology (for detection), ordered by specificity
DETECTION_FILES: List[str] = list(DETECTION_RULES.keys())

# License text to add after clone if README placeholder exists
README_CLONE_GUIDE = "git clone <your-repo-url>"
