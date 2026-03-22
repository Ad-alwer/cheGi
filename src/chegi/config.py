import json
from pathlib import Path
from typing import Set, Dict, Any, List, Tuple

# Git requirements
MIN_GIT_VERSION: Tuple[int, int, int] = (2, 25, 0)

# Security Constants (Immutable)
DEFAULT_SENSITIVE_PATTERNS: Tuple[str, ...] = (
    ".env*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "*.pk8",
    "*secret*",
    "credentials.json",
)

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
    ".git"
]
DEFAULT_MAX_DEPTH: int = 3
DEFAULT_MCTS: int = 10


class ChegiConfig:
    """Manages loading, updating, and saving configurations for the cheGi CLI.

    This class handles the persistent state of the application by reading from
    and writing to a `.chegi.json` file. It manages settings such as directories
    to exclude, maximum scan depth, and maximum concurrent tasks.

    Attributes:
        config_file (Path): The absolute or relative path to the `.chegi.json` file.
        exclude_dirs (Set[str]): A collection of directory names to be ignored during the scan.
        max_depth (int): The maximum depth to traverse when scanning directories.
        mcts (int): Maximum Concurrent Tasks, limiting the number of async operations.
    """

    def __init__(self, base_path: str = ".") -> None:
        """Initializes the configuration manager with default values and loads user settings.

        Args:
            base_path (str, optional): The base directory where `.chegi.json` is located. 
                Defaults to "." (current working directory).
        """
        self.config_file: Path = Path(base_path) / ".chegi.json"
        
        self.exclude_dirs: Set[str] = set(DEFAULT_EXCLUDES)
        self.max_depth: int = DEFAULT_MAX_DEPTH
        self.mcts: int = DEFAULT_MCTS
        
        self.load()

    def load(self) -> None:
        """Loads configuration from the `.chegi.json` file if it exists.

        Reads the JSON file and overrides the default attributes with user-defined
        settings. If the JSON file is invalid or corrupted, it silently falls back 
        to the default values.
        """
        if self.config_file.exists() and self.config_file.is_file():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    custom_excludes = data.get("exclude_dirs", [])
                    self.exclude_dirs.update(custom_excludes)
                    
                    self.max_depth = data.get("max_depth", DEFAULT_MAX_DEPTH)
                    self.mcts = data.get("mcts", DEFAULT_MCTS)
            except json.JSONDecodeError:
                pass

    def save(self) -> None:
        """Saves the current configuration state to the `.chegi.json` file.

        Serializes the current attributes into JSON format and writes them to disk
        with an indentation of 4 spaces for readability.
        """
        data: Dict[str, Any] = {
            "exclude_dirs": list(self.exclude_dirs),
            "max_depth": self.max_depth,
            "mcts": self.mcts
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def update_setting(self, key: str, value: Any) -> bool:
        """Updates a specific configuration key and saves the changes.

        Args:
            key (str): The configuration key to update (e.g., 'max_depth', 'mcts', 'exclude_dirs').
            value (Any): The new value for the configuration key. Can be a string, integer, or list.

        Returns:
            bool: True if the key was successfully updated, False if the key is not recognized.
        """
        if key == "max_depth":
            self.max_depth = int(value)
        elif key == "mcts":
            self.mcts = int(value)
        elif key == "exclude_dirs":
            if isinstance(value, str):
                new_excludes = [x.strip() for x in value.split(",")]
            else:
                new_excludes = list(value)
            self.exclude_dirs.update(new_excludes)
        else:
            return False
        
        self.save()
        return True

    def get_all(self) -> Dict[str, Any]:
        """Retrieves all current configurations.

        Returns:
            Dict[str, Any]: A dictionary containing all configuration keys and their current values.
        """
        return {
            "exclude_dirs": list(self.exclude_dirs),
            "max_depth": self.max_depth,
            "mcts": self.mcts
        }

    def add_exclude(self, folder_name: str) -> None:
        """Adds a single folder name to the exclusion list and saves the changes.

        Args:
            folder_name (str): The name of the folder to exclude.
        """
        self.exclude_dirs.add(folder_name.strip())
        self.save()

    def remove_exclude(self, folder_name: str) -> bool:
        """Removes a single folder name from the exclusion list and saves the changes.

        Args:
            folder_name (str): The name of the folder to remove from exclusions.

        Returns:
            bool: True if the folder was successfully removed, False if it was not found in the list.
        """
        folder_name = folder_name.strip()
        if folder_name in self.exclude_dirs:
            self.exclude_dirs.remove(folder_name)
            self.save()
            return True
        return False
