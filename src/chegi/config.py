import json
from pathlib import Path

# Default list of blacklisted directories to skip scanning
DEFAULT_EXCLUDES = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".tox",
    "__pycache__",
    ".idea",
    ".vscode",
    ".git"  # Skip scanning inside .git (we only need to find the folder itself)
}

def load_config(base_path: str) -> set:
    """
    Load custom configurations from .chegi.json if it exists,
    and merge them with the default exclude list.

    Args:
        base_path (str): The root directory where the configuration file might be located.

    Returns:
        set: A combined set of default and user-defined directory names to exclude from scanning.
    """
    config_file = Path(base_path) / ".chegi.json"
    
    # Create a copy of the default excludes
    excludes = set(DEFAULT_EXCLUDES)

    # Read user config if it exists
    if config_file.exists() and config_file.is_file():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                custom_excludes = data.get("exclude_dirs", [])
                
                # Merge user excludes with defaults
                excludes.update(custom_excludes)
        except json.JSONDecodeError:
            # Silently fallback to defaults if JSON is invalid
            pass 

    return excludes
