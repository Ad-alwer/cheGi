import json
from pathlib import Path

import pytest

from chegi.config import (
    DEFAULT_EXCLUDES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MCTS,
    DEFAULT_SENSITIVE_PATTERNS,
    ChegiConfig,
    InvalidMirrorFormatError,
    UnsupportedPackageManagerError,
)


def test_config_defaults(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    assert config.max_depth == DEFAULT_MAX_DEPTH
    assert config.mcts == DEFAULT_MCTS
    assert set(DEFAULT_EXCLUDES).issubset(config.exclude_dirs)
    assert not config.config_file.exists()


def test_config_save_and_load(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    # Modify settings
    config.max_depth = 5
    config.mcts = 20
    config.exclude_dirs.add("custom_folder")
    config.save()

    assert config.config_file.exists()

    # Create a new instance to load the saved file
    new_config = ChegiConfig(base_path=str(tmp_path))
    assert new_config.max_depth == 5
    assert new_config.mcts == 20
    assert "custom_folder" in new_config.exclude_dirs


def test_update_setting_valid(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    assert config.update_setting("max_depth", "7") is True
    assert config.max_depth == 7

    assert config.update_setting("mcts", "15") is True
    assert config.mcts == 15

    assert config.update_setting("exclude_dirs", "build, dist") is True
    assert "build" in config.exclude_dirs
    assert "dist" in config.exclude_dirs


def test_update_setting_invalid(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))
    assert config.update_setting("invalid_key", "value") is False


def test_add_and_remove_exclude(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    config.add_exclude("temp_cache")
    assert "temp_cache" in config.exclude_dirs

    with open(config.config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "temp_cache" in data["exclude_dirs"]

    assert config.remove_exclude("temp_cache") is True
    assert "temp_cache" not in config.exclude_dirs
    assert config.remove_exclude("does_not_exist") is False


def test_get_all(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))
    all_configs = config.get_all()

    assert all_configs["max_depth"] == DEFAULT_MAX_DEPTH
    assert all_configs["mcts"] == DEFAULT_MCTS
    assert isinstance(all_configs["exclude_dirs"], list)


def test_corrupted_json_fallback(tmp_path: Path) -> None:
    config_file = tmp_path / ".chegi.json"
    config_file.write_text("{invalid json format...]", encoding="utf-8")

    config = ChegiConfig(base_path=str(tmp_path))
    assert config.max_depth == DEFAULT_MAX_DEPTH
    assert config.mcts == DEFAULT_MCTS


def test_set_and_get_mirror(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    config.set_mirror("pip", "https://mirror1.local")
    assert "https://mirror1.local" in config.get_mirror("pip")

    config.set_mirror("pip", "https://mirror2.local")
    assert len(config.get_mirror("pip")) == 2

    # Ensure duplicate URLs are not appended
    config.set_mirror("pip", "https://mirror1.local")
    assert len(config.get_mirror("pip")) == 2

    with pytest.raises(UnsupportedPackageManagerError):
        config.set_mirror("invalid_pm", "https://url.local")


def test_remove_mirror_specific_url(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    config.set_mirror("npm", "https://npm.mirror1")
    config.set_mirror("npm", "https://npm.mirror2")

    assert config.remove_mirror("npm", "https://npm.mirror1") is True
    assert "https://npm.mirror1" not in config.get_mirror("npm")
    assert "https://npm.mirror2" in config.get_mirror("npm")

    assert config.remove_mirror("npm", "https://npm.mirror2") is True
    assert config.get_mirror("npm") == []
    assert "npm" not in config.mirrors

    assert config.remove_mirror("npm", "https://fake.url") is False


def test_remove_mirror_all(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    config.set_mirror("yarn", "https://yarn.mirror1")
    config.set_mirror("yarn", "https://yarn.mirror2")

    assert config.remove_mirror("yarn") is True
    assert config.get_mirror("yarn") == []
    assert "yarn" not in config.mirrors

    assert config.remove_mirror("yarn") is False


def test_add_mirrors_from_string(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    config.add_mirrors_from_string("pip=https://pypi.local, npm=https://npm.local")
    assert "https://pypi.local" in config.get_mirror("pip")
    assert "https://npm.local" in config.get_mirror("npm")

    with pytest.raises(InvalidMirrorFormatError):
        config.add_mirrors_from_string("invalid_format_string")


def test_update_setting_mirrors(tmp_path: Path) -> None:
    config = ChegiConfig(base_path=str(tmp_path))

    config.update_setting(
        "mirrors", {"pip": ["https://pip.local1", "https://pip.local2"]}
    )
    assert len(config.get_mirror("pip")) == 2
    assert "https://pip.local1" in config.get_mirror("pip")

    config.update_setting("mirrors", "cargo=https://cargo.local")
    assert "https://cargo.local" in config.get_mirror("cargo")


def test_load_legacy_mirror_format(tmp_path: Path) -> None:
    """Tests if load() correctly handles old JSON formats where a mirror URL is a string, not a list."""
    config_file = tmp_path / ".chegi.json"
    legacy_data = {"mirrors": {"pip": "https://legacy-pip.local"}}
    config_file.write_text(json.dumps(legacy_data), encoding="utf-8")

    config = ChegiConfig(base_path=str(tmp_path))
    assert "https://legacy-pip.local" in config.get_mirror("pip")
    assert isinstance(config.get_mirror("pip"), list)


def test_update_setting_with_list_types(tmp_path: Path) -> None:
    """Tests update_setting with actual list objects instead of strings."""
    config = ChegiConfig(base_path=str(tmp_path))

    # Test exclude_dirs with a list/set
    config.update_setting("exclude_dirs", ["node_modules", "venv"])
    assert "node_modules" in config.exclude_dirs
    assert "venv" in config.exclude_dirs

    # Test mirrors with a dictionary containing string values (not lists)
    config.update_setting("mirrors", {"npm": "https://npm.local.string"})
    assert "https://npm.local.string" in config.get_mirror("npm")


def test_add_mirrors_from_string_empty_and_spaces(tmp_path: Path) -> None:
    """Tests handling of empty strings and trailing commas in mirror strings."""
    config = ChegiConfig(base_path=str(tmp_path))

    # Should not raise any error, just return safely
    config.add_mirrors_from_string("")
    config.add_mirrors_from_string("   ")

    # String with empty parts (trailing comma)
    config.add_mirrors_from_string("pip=https://pypi.org,  ,  npm=https://npm.js  ")
    assert "https://pypi.org" in config.get_mirror("pip")
    assert "https://npm.js" in config.get_mirror("npm")


def test_load_project_config_overrides_dot_chegi_json(tmp_path: Path) -> None:
    """Tests that `.chegi/config.json` values override `.chegi.json` values."""
    # Write a .chegi.json with some values
    chegi_json = tmp_path / ".chegi.json"
    chegi_json.write_text(
        json.dumps({"max_depth": 1, "mcts": 5, "exclude_dirs": ["node_modules"]}),
        encoding="utf-8",
    )

    # Write .chegi/config.json with overrides
    chegi_dir = tmp_path / ".chegi"
    chegi_dir.mkdir()
    project_config = chegi_dir / "config.json"
    project_config.write_text(
        json.dumps({"max_depth": 10, "exclude_dirs": ["build"]}),
        encoding="utf-8",
    )

    config = ChegiConfig(base_path=str(tmp_path))
    # max_depth should come from .chegi/config.json (override)
    assert config.max_depth == 10
    # mcts should come from .chegi.json (not overridden)
    assert config.mcts == 5
    # exclude_dirs should come from .chegi/config.json (override)
    assert "build" in config.exclude_dirs
    assert "node_modules" not in config.exclude_dirs


def test_load_project_config_only(tmp_path: Path) -> None:
    """Tests that ChegiConfig loads from `.chegi/config.json` when no `.chegi.json` exists."""
    chegi_dir = tmp_path / ".chegi"
    chegi_dir.mkdir()
    project_config = chegi_dir / "config.json"
    project_config.write_text(
        json.dumps({"max_depth": 7, "mcts": 15}),
        encoding="utf-8",
    )

    config = ChegiConfig(base_path=str(tmp_path))
    assert config.max_depth == 7
    assert config.mcts == 15


def test_sensitive_patterns_default_empty(tmp_path: Path) -> None:
    """Test that sensitive_patterns is empty by default."""
    config = ChegiConfig(base_path=str(tmp_path))
    assert config.sensitive_patterns == set()


def test_add_and_remove_sensitive_pattern(tmp_path: Path) -> None:
    """Test adding and removing custom sensitive patterns."""
    config = ChegiConfig(base_path=str(tmp_path))

    config.add_sensitive_pattern("my_secrets.yaml")
    assert "my_secrets.yaml" in config.sensitive_patterns

    with open(config.config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "my_secrets.yaml" in data["sensitive_patterns"]

    assert config.remove_sensitive_pattern("my_secrets.yaml") is True
    assert "my_secrets.yaml" not in config.sensitive_patterns
    assert config.remove_sensitive_pattern("does_not_exist") is False


def test_sensitive_patterns_persist_across_load(tmp_path: Path) -> None:
    """Test that custom patterns survive a save/load cycle."""
    config = ChegiConfig(base_path=str(tmp_path))
    config.add_sensitive_pattern("secrets.*")
    config.add_sensitive_pattern("*.local")

    new_config = ChegiConfig(base_path=str(tmp_path))
    assert "secrets.*" in new_config.sensitive_patterns
    assert "*.local" in new_config.sensitive_patterns


def test_sensitive_patterns_in_get_all(tmp_path: Path) -> None:
    """Test that sensitive_patterns appears in get_all()."""
    config = ChegiConfig(base_path=str(tmp_path))
    config.add_sensitive_pattern("my_keys.txt")
    all_configs = config.get_all()
    assert "my_keys.txt" in all_configs["sensitive_patterns"]


def test_get_all_sensitive_patterns_merges_defaults(tmp_path: Path) -> None:
    """Test that get_all_sensitive_patterns() merges defaults with custom."""
    config = ChegiConfig(base_path=str(tmp_path))
    config.add_sensitive_pattern("my_app.key")
    all_patterns = config.get_all_sensitive_patterns()
    assert "my_app.key" in all_patterns
    assert ".env*" in all_patterns
    assert "*.pem" in all_patterns
    for default in DEFAULT_SENSITIVE_PATTERNS:
        assert default in all_patterns


def test_update_setting_sensitive_patterns(tmp_path: Path) -> None:
    """Test that update_setting handles sensitive_patterns."""
    config = ChegiConfig(base_path=str(tmp_path))
    assert config.update_setting("sensitive_patterns", "custom.key, *.secret") is True
    assert "custom.key" in config.sensitive_patterns
    assert "*.secret" in config.sensitive_patterns


def test_sensitive_patterns_load_from_project_config(tmp_path: Path) -> None:
    """Test that sensitive_patterns loads from .chegi/config.json."""
    chegi_dir = tmp_path / ".chegi"
    chegi_dir.mkdir()
    project_config = chegi_dir / "config.json"
    project_config.write_text(
        json.dumps({"sensitive_patterns": ["project.env", "deploy.key"]}),
        encoding="utf-8",
    )

    config = ChegiConfig(base_path=str(tmp_path))
    assert "project.env" in config.sensitive_patterns
    assert "deploy.key" in config.sensitive_patterns
