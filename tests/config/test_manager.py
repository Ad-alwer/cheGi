import json
from pathlib import Path

import pytest

from chegi.config import (
    DEFAULT_EXCLUDES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MCTS,
    ChegiConfig,
    UnsupportedPackageManagerError,
    InvalidMirrorFormatError,
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
