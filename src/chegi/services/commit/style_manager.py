"""Manager for commit style preferences, hints, and configuration."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from chegi.services.commit.constants import BUILTIN_STYLES
from chegi.services.commit.models import CommitStyle

HINTS_DIR_NAME = "hints"
PREFS_FILE_NAME = "prefs.json"


class CommitStyleManager:
    """Manages commit style preferences, hints, and custom styles.

    Handles:
    - Saving/loading the user's last used commit style
    - One-time hints for brand signature feature
    - Custom user-defined styles from .chegi/commit-styles.json

    Attributes:
        repo_path (Path): The path to the Git repository.
    """

    def __init__(self, repo_path: Path):
        """Initializes the CommitStyleManager.

        Args:
            repo_path (Path): The local directory path of the git repository.
        """
        self.repo_path = repo_path
        self.config_dir = Path.home() / ".config" / "chegi"
        self.hints_dir = self.config_dir / HINTS_DIR_NAME
        self.prefs_file = self.config_dir / PREFS_FILE_NAME

    def get_styles(self) -> List[CommitStyle]:
        """Returns the list of available styles including custom ones.

        Custom styles are loaded from .chegi/commit-styles.json if it exists.

        Returns:
            List[CommitStyle]: All available commit styles.
        """
        styles = list(BUILTIN_STYLES)
        custom = self._load_custom_styles()
        styles.extend(custom)
        return styles

    def get_last_style(self) -> Optional[str]:
        """Returns the name of the user's last used commit style.

        Returns:
            Optional[str]: The style name, or None if not set.
        """
        prefs = self._load_prefs()
        return prefs.get("last_commit_style")

    def save_last_style(self, style_name: str) -> None:
        """Persists the user's last used commit style.

        Args:
            style_name (str): The style name to save.
        """
        prefs = self._load_prefs()
        prefs["last_commit_style"] = style_name
        self._save_prefs(prefs)

    def should_show_hint(self, hint_name: str) -> bool:
        """Checks whether a one-time hint should be shown.

        Args:
            hint_name (str): The hint identifier.

        Returns:
            bool: True if the hint has not been shown yet.
        """
        hint_file = self.hints_dir / hint_name
        return not hint_file.exists()

    def mark_hint_shown(self, hint_name: str) -> None:
        """Marks a one-time hint as shown.

        Args:
            hint_name (str): The hint identifier.
        """
        self.hints_dir.mkdir(parents=True, exist_ok=True)
        hint_file = self.hints_dir / hint_name
        hint_file.write_text(json.dumps({"shown": True}))

    def _load_prefs(self) -> Dict:
        """Loads user preferences from the prefs file.

        Returns:
            Dict: The preferences dictionary.
        """
        if self.prefs_file.exists():
            try:
                return json.loads(self.prefs_file.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_prefs(self, prefs: Dict) -> None:
        """Saves user preferences to the prefs file.

        Args:
            prefs (Dict): The preferences dictionary to save.
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.prefs_file.write_text(json.dumps(prefs, indent=2))

    def _load_custom_styles(self) -> List[CommitStyle]:
        """Loads custom commit styles from .chegi/commit-styles.json.

        Returns:
            List[CommitStyle]: Custom commit styles.
        """
        custom_file = self.repo_path / ".chegi" / "commit-styles.json"
        if not custom_file.exists():
            return []
        try:
            data = json.loads(custom_file.read_text())
            styles = data.get("styles", [])
            return [
                CommitStyle(
                    name=s["name"],
                    label=s.get("label", s["name"]),
                    description=s.get("description", ""),
                    fields=s["fields"],
                    types=s.get("types"),
                    emojis=s.get("emojis"),
                )
                for s in styles
            ]
        except (json.JSONDecodeError, OSError, KeyError):
            return []
