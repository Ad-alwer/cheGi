"""Service for initializing and managing .chegi/ project directories."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from chegi.services.init.constants import (
    CHEGI_DIR_NAME,
    CHEGIIGNORE_FILE_NAME,
    CONFIG_FILE_NAME,
    DEFAULT_CHEGIIGNORE,
    DEFAULT_CONFIG,
    DEFAULT_GUARD_RULES,
    GUARD_RULES_FILE_NAME,
)
from chegi.services.init.exceptions import InitError
from chegi.services.init.models import ChegiProject, GuardRules, ProjectConfig


class InitService:
    """Manages creation and loading of .chegi/ project directories."""

    @staticmethod
    def create_project_directory(path: Path) -> ChegiProject:
        """Creates a .chegi/ directory in the given path with default files.

        Args:
            path: The project root where .chegi/ should be created.

        Returns:
            ChegiProject representing the created project.

        Raises:
            InitError: If the .chegi/ directory already exists.
        """
        chegi_dir = path / CHEGI_DIR_NAME

        if chegi_dir.exists():
            raise InitError(
                f"A .chegi/ directory already exists at {chegi_dir}. "
                f"Use 'chegi init --force' to overwrite."
            )

        chegi_dir.mkdir(parents=True, exist_ok=False)

        config_path = chegi_dir / CONFIG_FILE_NAME
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
            f.write("\n")

        guard_path = chegi_dir / GUARD_RULES_FILE_NAME
        with open(guard_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_GUARD_RULES, f, indent=2)
            f.write("\n")

        chegiignore_path = chegi_dir / CHEGIIGNORE_FILE_NAME
        with open(chegiignore_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_CHEGIIGNORE)

        InitService._ensure_gitignore(path)

        return ChegiProject(
            root=path,
            chegi_dir=chegi_dir,
            config=InitService._parse_config(DEFAULT_CONFIG),
            guard_rules=InitService._parse_guard_rules(DEFAULT_GUARD_RULES),
            chegiignore=DEFAULT_CHEGIIGNORE.splitlines(),
        )

    @staticmethod
    def _ensure_gitignore(path: Path) -> None:
        """Ensures .chegi/ is listed in the project's .gitignore.

        Args:
            path: The project root directory.
        """
        gitignore_path = path / ".gitignore"
        chegi_entry = f"/{CHEGI_DIR_NAME}"

        if not gitignore_path.exists():
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(f"{chegi_entry}\n")
            return

        existing = gitignore_path.read_text(encoding="utf-8").splitlines()
        if chegi_entry not in existing:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(f"\n{chegi_entry}\n")

    @staticmethod
    def _parse_config(data: Dict) -> ProjectConfig:
        """Parses a dictionary into a ProjectConfig dataclass.

        Args:
            data: Raw dictionary from config.json.

        Returns:
            ProjectConfig instance.
        """
        return ProjectConfig(
            exclude_dirs=data.get("exclude_dirs", []),
            max_depth=data.get("max_depth"),
            mcts=data.get("mcts"),
            mirrors=data.get("mirrors", {}),
            guard_rules=data.get("guard_rules", []),
            guard_excludes=data.get("guard_excludes", []),
        )

    @staticmethod
    def _parse_guard_rules(data: Dict) -> GuardRules:
        """Parses a dictionary into a GuardRules dataclass.

        Args:
            data: Raw dictionary from guard-rules.json.

        Returns:
            GuardRules instance.
        """
        return GuardRules(
            patterns=data.get("patterns", []),
            exclude_patterns=data.get("exclude_patterns", []),
        )

    @staticmethod
    def load_project(path: Path) -> Optional[ChegiProject]:
        """Loads a cheGi project from a directory containing .chegi/.

        Args:
            path: The project root to load from.

        Returns:
            ChegiProject if .chegi/ exists, None otherwise.
        """
        chegi_dir = path / CHEGI_DIR_NAME
        if not chegi_dir.is_dir():
            return None

        config = None
        config_path = chegi_dir / CONFIG_FILE_NAME
        if config_path.is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = InitService._parse_config(json.load(f))
            except (json.JSONDecodeError, OSError):
                config = None

        guard_rules = None
        guard_path = chegi_dir / GUARD_RULES_FILE_NAME
        if guard_path.is_file():
            try:
                with open(guard_path, "r", encoding="utf-8") as f:
                    guard_rules = InitService._parse_guard_rules(json.load(f))
            except (json.JSONDecodeError, OSError):
                guard_rules = None

        chegiignore: List[str] = []
        chegiignore_path = chegi_dir / CHEGIIGNORE_FILE_NAME
        if chegiignore_path.is_file():
            try:
                chegiignore = [
                    line.strip()
                    for line in chegiignore_path.read_text(
                        encoding="utf-8"
                    ).splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
            except OSError:
                chegiignore = []

        return ChegiProject(
            root=path,
            chegi_dir=chegi_dir,
            config=config,
            guard_rules=guard_rules,
            chegiignore=chegiignore,
        )

    @staticmethod
    def find_project_root(start: Optional[Path] = None) -> Optional[Path]:
        """Walks up from start to find a directory containing .chegi/.

        Args:
            start: The directory to start searching from. Defaults to CWD.

        Returns:
            Path to the project root, or None if not found.
        """
        current = (start or Path.cwd()).resolve()
        while True:
            if (current / CHEGI_DIR_NAME).is_dir():
                return current
            parent = current.parent
            if parent == current:
                return None
            current = parent
