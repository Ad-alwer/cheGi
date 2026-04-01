import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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

# Supported Package Managers for Mirrors (Restrict to valid names)
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
# Changed to support lists of URLs instead of a single string
DEFAULT_MIRRORS: Dict[str, List[str]] = {}


class ChegiConfig:
    """Manages loading, updating, and saving configurations for the cheGi CLI.

    This class handles the persistent state of the application by reading from
    and writing to a `.chegi.json` file. It manages settings such as directories
    to exclude, maximum scan depth, maximum concurrent tasks, and custom mirrors.

    Attributes:
        config_file (Path): The absolute or relative path to the `.chegi.json` file.
        exclude_dirs (Set[str]): A collection of directory names to be ignored during the scan.
        max_depth (int): The maximum depth to traverse when scanning directories.
        mcts (int): Maximum Concurrent Tasks, limiting the number of async operations.
        mirrors (Dict[str, List[str]]): Persistent custom mirror URLs for package managers.
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
        # Deep copy the default mirrors to prevent shared state mutations
        self.mirrors: Dict[str, List[str]] = {
            k: list(v) for k, v in DEFAULT_MIRRORS.items()
        }

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

                    # Load mirrors and gracefully migrate legacy string formats to lists
                    loaded_mirrors = data.get("mirrors", {})
                    if isinstance(loaded_mirrors, dict):
                        for pm, urls in loaded_mirrors.items():
                            if pm in SUPPORTED_PMS:
                                if isinstance(urls, str):
                                    self.mirrors[pm] = [urls]
                                elif isinstance(urls, list):
                                    self.mirrors[pm] = [str(u) for u in urls if u]
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
            "mcts": self.mcts,
            "mirrors": self.mirrors,
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def update_setting(self, key: str, value: Any) -> bool:
        """Updates a specific configuration key and saves the changes.

        Args:
            key (str): The configuration key to update (e.g., 'max_depth', 'mcts', 'exclude_dirs', 'mirrors').
            value (Any): The new value for the configuration key.

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
        elif key == "mirrors":
            if isinstance(value, dict):
                for pm, url_data in value.items():
                    # Handle both single strings and lists of strings gracefully
                    if isinstance(url_data, list):
                        for u in url_data:
                            self.set_mirror(pm, str(u))
                    else:
                        self.set_mirror(pm, str(url_data))
            elif isinstance(value, str):
                self.add_mirrors_from_string(value)
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
            "mcts": self.mcts,
            "mirrors": self.mirrors,
        }

    def add_exclude(self, folder_name: str) -> None:
        """Adds a single folder name to the exclusion list and saves the changes."""
        self.exclude_dirs.add(folder_name.strip())
        self.save()

    def remove_exclude(self, folder_name: str) -> bool:
        """Removes a single folder name from the exclusion list and saves the changes."""
        folder_name = folder_name.strip()
        if folder_name in self.exclude_dirs:
            self.exclude_dirs.remove(folder_name)
            self.save()
            return True
        return False

    # --- Methods for Mirror Management ---

    def set_mirror(self, pm_name: str, url: str) -> None:
        """Adds a permanent mirror URL for a package manager without overwriting existing ones.

        Args:
            pm_name (str): The name of the package manager (e.g., 'pip', 'npm').
            url (str): The URL of the mirror to append.

        Raises:
            ValueError: If the package manager is not in SUPPORTED_PMS.
        """
        pm_name = pm_name.strip().lower()
        if pm_name not in SUPPORTED_PMS:
            raise ValueError(
                f"Unsupported package manager: '{pm_name}'. "
                f"Supported ones are: {', '.join(SUPPORTED_PMS)}"
            )

        if pm_name not in self.mirrors:
            self.mirrors[pm_name] = []

        clean_url = url.strip()
        # Prevent appending duplicate URLs for the same package manager
        if clean_url and clean_url not in self.mirrors[pm_name]:
            self.mirrors[pm_name].append(clean_url)
            self.save()

    def add_mirrors_from_string(self, mirrors_str: str) -> None:
        """Parses a string of multiple mirrors and appends them to their respective lists.

        Expects a comma-separated list of key=value pairs, e.g., 'pip=url1,npm=url2'.

        Args:
            mirrors_str (str): The string containing package managers and URLs.

        Raises:
            ValueError: If the string format is invalid or contains unsupported package managers.
        """
        if not mirrors_str or not mirrors_str.strip():
            return

        parts = mirrors_str.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if "=" not in part:
                raise ValueError(
                    f"Invalid format '{part}'. Expected format: 'pm_name=url'"
                )

            pm, url = part.split("=", 1)
            self.set_mirror(pm, url)

    def remove_mirror(self, pm_name: str, url: Optional[str] = None) -> bool:
        """Removes a specific mirror URL or all mirrors for a package manager.

        Args:
            pm_name (str): The package manager name.
            url (Optional[str]): The specific URL to remove. If None, removes all URLs for pm_name.

        Returns:
            bool: True if a removal occurred, False otherwise.
        """
        pm_name = pm_name.lower()
        if pm_name not in self.mirrors:
            return False

        if url:
            # Remove specific URL
            if url in self.mirrors[pm_name]:
                self.mirrors[pm_name].remove(url)
                # If the list is now empty, remove the pm_name key entirely
                if not self.mirrors[pm_name]:
                    del self.mirrors[pm_name]
                return True
            return False  # URL was not in the list
        else:
            # No URL specified, remove the entire package manager entry
            del self.mirrors[pm_name]
            return True

    def get_mirror(self, pm_name: str) -> List[str]:
        """Retrieves the list of permanent mirror URLs for a specific package manager.

        Args:
            pm_name (str): The name of the package manager.

        Returns:
            List[str]: A list of assigned URLs, or an empty list if none are set.
        """
        return self.mirrors.get(pm_name.strip().lower(), [])
