"""Global user-level configuration for cheGi (stored in ~/.config/chegi/)."""

import json
import os
from pathlib import Path
from typing import Any, Dict

GLOBAL_CONFIG_DIR = Path.home() / ".config" / "chegi"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.json"

DEFAULT_THEME = "default"


class GlobalConfig:
    """Manages user-level (non-project) cheGi preferences.

    Stored in ~/.config/chegi/config.json.
    Currently supports: theme.
    """

    def __init__(self) -> None:
        """Loads the global config file on init."""
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Reads the global config file from disk."""
        if not GLOBAL_CONFIG_FILE.is_file():
            self._data = {"theme": DEFAULT_THEME}
            return
        try:
            with open(GLOBAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._data = {"theme": DEFAULT_THEME}

    def save(self) -> None:
        """Writes the global config to disk."""
        os.makedirs(str(GLOBAL_CONFIG_DIR), exist_ok=True)
        with open(GLOBAL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a config value.

        Args:
            key: The config key.
            default: Default value if key is missing.

        Returns:
            The value, or default.
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Sets a config value and saves.

        Args:
            key: The config key.
            value: The value to set.
        """
        self._data[key] = value
        self.save()

    @property
    def theme(self) -> str:
        """str: The active theme name."""
        return str(self.get("theme", DEFAULT_THEME))

    @theme.setter
    def theme(self, value: str) -> None:
        self.set("theme", value)
