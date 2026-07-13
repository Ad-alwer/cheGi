"""Tests for the InitService class."""

import json
from pathlib import Path

import pytest

from chegi.services.init import InitService
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


class TestInitServiceCreate:
    """Tests for InitService.create_project_directory."""

    def test_creates_directory_with_all_files(self, tmp_path: Path) -> None:
        """Test that create_project_directory creates .chegi/ with config.json, guard-rules.json, and .chegiignore."""
        project = InitService.create_project_directory(tmp_path)

        chegi_dir = tmp_path / CHEGI_DIR_NAME
        assert chegi_dir.is_dir()

        config_file = chegi_dir / CONFIG_FILE_NAME
        assert config_file.is_file()
        with open(config_file) as f:
            assert json.load(f) == DEFAULT_CONFIG

        guard_file = chegi_dir / GUARD_RULES_FILE_NAME
        assert guard_file.is_file()
        with open(guard_file) as f:
            assert json.load(f) == DEFAULT_GUARD_RULES

        chegiignore_file = chegi_dir / CHEGIIGNORE_FILE_NAME
        assert chegiignore_file.is_file()
        assert chegiignore_file.read_text() == DEFAULT_CHEGIIGNORE

        assert project.root == tmp_path
        assert project.chegi_dir == chegi_dir

    def test_raises_error_when_already_exists(self, tmp_path: Path) -> None:
        """Test that create_project_directory raises InitError when .chegi/ already exists."""
        chegi_dir = tmp_path / CHEGI_DIR_NAME
        chegi_dir.mkdir()

        with pytest.raises(InitError, match="already exists"):
            InitService.create_project_directory(tmp_path)

    def test_adds_entry_to_gitignore(self, tmp_path: Path) -> None:
        """Test that create_project_directory adds .chegi/ to .gitignore."""
        InitService.create_project_directory(tmp_path)

        gitignore = tmp_path / ".gitignore"
        assert gitignore.is_file()
        content = gitignore.read_text()
        assert f"/{CHEGI_DIR_NAME}" in content

    def test_appends_to_existing_gitignore(self, tmp_path: Path) -> None:
        """Test that create_project_directory appends to existing .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n")

        InitService.create_project_directory(tmp_path)

        content = gitignore.read_text()
        assert content.startswith("node_modules/")
        assert f"/{CHEGI_DIR_NAME}" in content

    def test_returns_chegi_project_with_defaults(self, tmp_path: Path) -> None:
        """Test that create_project_directory returns a ChegiProject with default values."""
        project = InitService.create_project_directory(tmp_path)

        assert project.config is not None
        assert project.config.exclude_dirs == DEFAULT_CONFIG["exclude_dirs"]
        assert project.config.max_depth == DEFAULT_CONFIG["max_depth"]
        assert project.config.mcts == DEFAULT_CONFIG["mcts"]

        assert project.guard_rules is not None
        assert project.guard_rules.patterns == DEFAULT_GUARD_RULES["patterns"]

        assert len(project.chegiignore) > 0


class TestInitServiceLoad:
    """Tests for InitService.load_project."""

    def test_loads_existing_project(self, tmp_path: Path) -> None:
        """Test that load_project returns a ChegiProject for an existing .chegi/ directory."""
        InitService.create_project_directory(tmp_path)

        project = InitService.load_project(tmp_path)

        assert project is not None
        assert project.root == tmp_path
        assert project.chegi_dir == tmp_path / CHEGI_DIR_NAME

    def test_returns_none_when_no_chegi_dir(self, tmp_path: Path) -> None:
        """Test that load_project returns None when no .chegi/ directory exists."""
        project = InitService.load_project(tmp_path)
        assert project is None

    def test_loads_custom_config_values(self, tmp_path: Path) -> None:
        """Test that load_project reads custom values from config.json."""
        InitService.create_project_directory(tmp_path)

        config_file = tmp_path / CHEGI_DIR_NAME / CONFIG_FILE_NAME
        custom_config = {
            "exclude_dirs": ["build", "dist"],
            "max_depth": 5,
            "mcts": 20,
            "mirrors": {"pip": ["https://mirror.local"]},
            "guard_rules": ["*.secret"],
            "guard_excludes": ["*.ok"],
        }
        with open(config_file, "w") as f:
            json.dump(custom_config, f)

        project = InitService.load_project(tmp_path)

        assert project is not None
        assert project.config is not None
        assert project.config.exclude_dirs == ["build", "dist"]
        assert project.config.max_depth == 5
        assert project.config.mcts == 20
        assert project.config.mirrors == {"pip": ["https://mirror.local"]}
        assert project.config.guard_rules == ["*.secret"]
        assert project.config.guard_excludes == ["*.ok"]

    def test_loads_custom_guard_rules(self, tmp_path: Path) -> None:
        """Test that load_project reads custom values from guard-rules.json."""
        InitService.create_project_directory(tmp_path)

        guard_file = tmp_path / CHEGI_DIR_NAME / GUARD_RULES_FILE_NAME
        custom_rules = {
            "patterns": ["*.custom"],
            "exclude_patterns": ["*.ok"],
        }
        with open(guard_file, "w") as f:
            json.dump(custom_rules, f)

        project = InitService.load_project(tmp_path)

        assert project is not None
        assert project.guard_rules is not None
        assert project.guard_rules.patterns == ["*.custom"]
        assert project.guard_rules.exclude_patterns == ["*.ok"]

    def test_loads_chegiignore(self, tmp_path: Path) -> None:
        """Test that load_project reads patterns from .chegiignore skipping comments and blanks."""
        InitService.create_project_directory(tmp_path)

        project = InitService.load_project(tmp_path)

        assert project is not None
        assert len(project.chegiignore) > 0
        # No entries should be comments or blank
        for entry in project.chegiignore:
            assert not entry.startswith("#")
            assert entry.strip() != ""


class TestInitServiceFindRoot:
    """Tests for InitService.find_project_root."""

    def test_finds_root_from_subdirectory(self, tmp_path: Path) -> None:
        """Test that find_project_root finds .chegi/ when searching from a subdirectory."""
        InitService.create_project_directory(tmp_path)

        sub_dir = tmp_path / "sub" / "deep"
        sub_dir.mkdir(parents=True)

        root = InitService.find_project_root(sub_dir)
        assert root == tmp_path

    def test_returns_none_when_no_root(self, tmp_path: Path) -> None:
        """Test that find_project_root returns None when no .chegi/ exists."""
        root = InitService.find_project_root(tmp_path)
        assert root is None

    def test_finds_root_from_current(self, tmp_path: Path) -> None:
        """Test that find_project_root finds .chegi/ when called directly on the root."""
        InitService.create_project_directory(tmp_path)

        root = InitService.find_project_root(tmp_path)
        assert root == tmp_path

    def test_stops_at_filesystem_root(self, tmp_path: Path) -> None:
        """Test that find_project_root does not loop indefinitely and returns None."""
        # Use a deep path that has no .chegi/ all the way up
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)

        root = InitService.find_project_root(deep)
        assert root is None
