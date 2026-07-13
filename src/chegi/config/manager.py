import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .constants import SUPPORTED_PMS
from .exceptions import InvalidMirrorFormatError, UnsupportedPackageManagerError
from .models import ChegiConfigModel


class ChegiConfig:
    """Manages loading, updating, and saving configurations for the cheGi CLI.

    This class handles the core state of the configuration using `ChegiConfigModel`
    and provides an interface to interact with settings like exclusions, depth limits,
    and package manager mirrors.
    """

    def __init__(self, base_path: str = ".") -> None:
        """Initializes the configuration manager and loads user settings.

        Args:
            base_path (str, optional): The base directory where the `.chegi.json`
                or `.chegi/config.json` configuration file is located. Defaults to ".".
        """
        self.base_path: Path = Path(base_path).resolve()
        self.config_file: Path = self.base_path / ".chegi.json"
        self.project_config_file: Path = self.base_path / ".chegi" / "config.json"

        # Core state is managed by the data class model
        self._state = ChegiConfigModel()

        self.load()

    # --- Properties for Backward Compatibility ---

    @property
    def exclude_dirs(self) -> Set[str]:
        """Set[str]: A set of directory names to exclude from operations."""
        return self._state.exclude_dirs

    @property
    def max_depth(self) -> int:
        """int: The maximum depth for directory traversal operations."""
        return self._state.max_depth

    @max_depth.setter
    def max_depth(self, value: int) -> None:
        self._state.max_depth = value

    @property
    def mcts(self) -> int:
        """int: The maximum concurrent tasks/threads setting."""
        return self._state.mcts

    @mcts.setter
    def mcts(self, value: int) -> None:
        self._state.mcts = value

    @property
    def mirrors(self) -> Dict[str, List[str]]:
        """Dict[str, List[str]]: A dictionary mapping package managers to their mirror URLs."""
        return self._state.mirrors

    # --- Core Methods ---

    def load(self) -> None:
        """Loads configuration from `.chegi.json` and/or `.chegi/config.json`.

        Reads the JSON files and updates the internal state (`_state`).
        Values in `.chegi/config.json` take precedence over `.chegi.json`.
        Ignores JSON decoding errors if a file is malformed.
        """
        self._load_config_file(self.config_file)

        if self.project_config_file.exists() and self.project_config_file.is_file():
            self._load_config_file(self.project_config_file)

    def _load_config_file(self, config_path: Path) -> None:
        """Loads and applies settings from a single JSON config file.

        Args:
            config_path: Path to the JSON config file.
        """
        if not config_path.is_file():
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                if "exclude_dirs" in data:
                    self._state.exclude_dirs.clear()
                    self._state.exclude_dirs.update(data["exclude_dirs"])

                self._state.max_depth = data.get("max_depth", self._state.max_depth)
                self._state.mcts = data.get("mcts", self._state.mcts)

                loaded_mirrors = data.get("mirrors", {})
                if isinstance(loaded_mirrors, dict):
                    for pm, urls in loaded_mirrors.items():
                        if pm in SUPPORTED_PMS:
                            if isinstance(urls, str):
                                self._state.mirrors[pm] = [urls]
                            elif isinstance(urls, list):
                                self._state.mirrors[pm] = [str(u) for u in urls if u]
        except json.JSONDecodeError:
            pass

    def save(self) -> None:
        """Saves the current configuration state to the `.chegi.json` file.

        Dumps the properties (exclude_dirs, max_depth, mcts, mirrors)
        into a formatted JSON file.
        """
        data: Dict[str, Any] = {
            "exclude_dirs": list(self._state.exclude_dirs),
            "max_depth": self._state.max_depth,
            "mcts": self._state.mcts,
            "mirrors": self._state.mirrors,
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def update_setting(self, key: str, value: Any) -> bool:
        """Updates a specific configuration key and saves the changes.

        Args:
            key (str): The configuration key to update (e.g., 'max_depth', 'mirrors').
            value (Any): The new value for the configuration key.

        Returns:
            bool: True if the setting was successfully updated, False if the key is unknown.
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
        """Retrieves all current configurations as a dictionary.

        Returns:
            Dict[str, Any]: A dictionary containing all configuration settings.
        """
        return {
            "exclude_dirs": list(self.exclude_dirs),
            "max_depth": self.max_depth,
            "mcts": self.mcts,
            "mirrors": self.mirrors,
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
            bool: True if the folder was found and removed, False otherwise.
        """
        folder_name = folder_name.strip()
        if folder_name in self.exclude_dirs:
            self.exclude_dirs.remove(folder_name)
            self.save()
            return True
        return False

    # --- Methods for Mirror Management ---

    def set_mirror(self, pm_name: str, url: str) -> None:
        """Adds a permanent mirror URL for a specific package manager.

        Args:
            pm_name (str): The name of the package manager (e.g., 'npm', 'pip').
            url (str): The mirror URL to add.

        Raises:
            UnsupportedPackageManagerError: If the package manager is not in `SUPPORTED_PMS`.
        """
        pm_name = pm_name.strip().lower()
        if pm_name not in SUPPORTED_PMS:
            raise UnsupportedPackageManagerError(
                f"Unsupported package manager: '{pm_name}'. "
                f"Supported ones are: {', '.join(SUPPORTED_PMS)}"
            )

        if pm_name not in self.mirrors:
            self.mirrors[pm_name] = []

        clean_url = url.strip()
        if clean_url and clean_url not in self.mirrors[pm_name]:
            self.mirrors[pm_name].append(clean_url)
            self.save()

    def add_mirrors_from_string(self, mirrors_str: str) -> None:
        """Parses a string of multiple mirrors and adds them to their respective lists.

        Args:
            mirrors_str (str): A comma-separated string of mirrors in 'pm_name=url' format.

        Raises:
            InvalidMirrorFormatError: If a part of the string does not match the expected format.
            UnsupportedPackageManagerError: If a parsed package manager is not supported.
        """
        if not mirrors_str or not mirrors_str.strip():
            return

        parts = mirrors_str.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if "=" not in part:
                raise InvalidMirrorFormatError(
                    f"Invalid format '{part}'. Expected format: 'pm_name=url'"
                )

            pm, url = part.split("=", 1)
            self.set_mirror(pm, url)

    def remove_mirror(self, pm_name: str, url: Optional[str] = None) -> bool:
        """Removes a specific mirror URL or all mirrors for a package manager.

        Args:
            pm_name (str): The name of the package manager.
            url (Optional[str], optional): The specific URL to remove. If None, all mirrors
                for the specified package manager are removed. Defaults to None.

        Returns:
            bool: True if the removal was successful, False if the package manager
                or URL was not found.
        """
        pm_name = pm_name.lower()
        if pm_name not in self.mirrors:
            return False

        if url:
            if url in self.mirrors[pm_name]:
                self.mirrors[pm_name].remove(url)
                if not self.mirrors[pm_name]:
                    del self.mirrors[pm_name]
                return True
            return False
        else:
            del self.mirrors[pm_name]
            return True

    def get_mirror(self, pm_name: str) -> List[str]:
        """Retrieves the list of permanent mirror URLs for a specific package manager.

        Args:
            pm_name (str): The name of the package manager.

        Returns:
            List[str]: A list of configured mirror URLs for the package manager.
        """
        return self.mirrors.get(pm_name.strip().lower(), [])
