import json
import pytest
from pathlib import Path
from chegi.config import ChegiConfig, DEFAULT_EXCLUDES, DEFAULT_MAX_DEPTH, DEFAULT_MCTS


def test_config_defaults(tmp_path: Path) -> None:
    """Tests if ChegiConfig loads default values when no file exists.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    assert config.max_depth == DEFAULT_MAX_DEPTH
    assert config.mcts == DEFAULT_MCTS
    assert set(DEFAULT_EXCLUDES).issubset(config.exclude_dirs)
    assert not config.config_file.exists()


def test_config_save_and_load(tmp_path: Path) -> None:
    """Tests saving configuration to a file and loading it back into a new instance.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    # Modify settings
    config.max_depth = 5
    config.mcts = 20
    config.exclude_dirs.add("custom_folder")
    
    # Save to file
    config.save()
    assert config.config_file.exists()
    
    # Create a new instance to load the saved file
    new_config = ChegiConfig(base_path=str(tmp_path))
    assert new_config.max_depth == 5
    assert new_config.mcts == 20
    assert "custom_folder" in new_config.exclude_dirs


def test_update_setting_valid(tmp_path: Path) -> None:
    """Tests updating settings via the update_setting method with valid keys.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    # Test integer updates (passed as string from CLI)
    assert config.update_setting("max_depth", "7") is True
    assert config.max_depth == 7
    
    assert config.update_setting("mcts", "15") is True
    assert config.mcts == 15
    
    # Test list update via comma-separated string
    assert config.update_setting("exclude_dirs", "build, dist") is True
    assert "build" in config.exclude_dirs
    assert "dist" in config.exclude_dirs


def test_update_setting_invalid(tmp_path: Path) -> None:
    """Tests updating an invalid setting key.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    assert config.update_setting("invalid_key", "value") is False


def test_add_and_remove_exclude(tmp_path: Path) -> None:
    """Tests adding and removing single folders from the exclude_dirs list.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    # Add a folder
    config.add_exclude("temp_cache")
    assert "temp_cache" in config.exclude_dirs
    
    # Verify it was saved to the JSON file
    with open(config.config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "temp_cache" in data["exclude_dirs"]
    
    # Remove the folder
    assert config.remove_exclude("temp_cache") is True
    assert "temp_cache" not in config.exclude_dirs
    
    # Try removing a non-existent folder
    assert config.remove_exclude("does_not_exist") is False


def test_get_all(tmp_path: Path) -> None:
    """Tests retrieving all configurations as a dictionary.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    all_configs = config.get_all()
    
    assert all_configs["max_depth"] == DEFAULT_MAX_DEPTH
    assert all_configs["mcts"] == DEFAULT_MCTS
    assert isinstance(all_configs["exclude_dirs"], list)


def test_corrupted_json_fallback(tmp_path: Path) -> None:
    """Tests fallback to default settings if the JSON file is corrupted.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config_file = tmp_path / ".chegi.json"
    config_file.write_text("{invalid json format...]", encoding="utf-8")
    
    # Should not raise an exception, but silently load defaults
    config = ChegiConfig(base_path=str(tmp_path))
    assert config.max_depth == DEFAULT_MAX_DEPTH
    assert config.mcts == DEFAULT_MCTS


def test_set_and_get_mirror(tmp_path: Path) -> None:
    """Tests adding and retrieving mirrors for supported package managers.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    config.set_mirror("pip", "https://mirror1.local")
    assert "https://mirror1.local" in config.get_mirror("pip")
    
    config.set_mirror("pip", "https://mirror2.local")
    assert len(config.get_mirror("pip")) == 2
    
    # Ensure duplicate URLs are not appended
    config.set_mirror("pip", "https://mirror1.local")
    assert len(config.get_mirror("pip")) == 2
    
    with pytest.raises(ValueError, match="Unsupported package manager"):
        config.set_mirror("invalid_pm", "https://url.local")


def test_remove_mirror_specific_url(tmp_path: Path) -> None:
    """Tests removing a specific URL from a package manager's mirror list.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    config.set_mirror("npm", "https://npm.mirror1")
    config.set_mirror("npm", "https://npm.mirror2")
    
    assert config.remove_mirror("npm", "https://npm.mirror1") is True
    assert "https://npm.mirror1" not in config.get_mirror("npm")
    assert "https://npm.mirror2" in config.get_mirror("npm")
    
    # Removing the last URL should delete the package manager key entirely
    assert config.remove_mirror("npm", "https://npm.mirror2") is True
    assert config.get_mirror("npm") == []
    assert "npm" not in config.mirrors
    
    # Attempting to remove a non-existent URL
    assert config.remove_mirror("npm", "https://fake.url") is False


def test_remove_mirror_all(tmp_path: Path) -> None:
    """Tests removing all mirrors for a specific package manager.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    config.set_mirror("yarn", "https://yarn.mirror1")
    config.set_mirror("yarn", "https://yarn.mirror2")
    
    # Omitting the url parameter should remove the entire PM entry
    assert config.remove_mirror("yarn") is True
    assert config.get_mirror("yarn") == []
    assert "yarn" not in config.mirrors
    
    # Attempting to remove a non-existent package manager
    assert config.remove_mirror("yarn") is False


def test_add_mirrors_from_string(tmp_path: Path) -> None:
    """Tests parsing a comma-separated string to add multiple mirrors.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    config.add_mirrors_from_string("pip=https://pypi.local, npm=https://npm.local")
    assert "https://pypi.local" in config.get_mirror("pip")
    assert "https://npm.local" in config.get_mirror("npm")
    
    with pytest.raises(ValueError, match="Invalid format"):
        config.add_mirrors_from_string("invalid_format_string")


def test_update_setting_mirrors(tmp_path: Path) -> None:
    """Tests updating mirrors via the update_setting method.

    Args:
        tmp_path (Path): A temporary directory provided by pytest.
    """
    config = ChegiConfig(base_path=str(tmp_path))
    
    # Update via dictionary containing a list of URLs
    config.update_setting("mirrors", {"pip": ["https://pip.local1", "https://pip.local2"]})
    assert len(config.get_mirror("pip")) == 2
    assert "https://pip.local1" in config.get_mirror("pip")
    
    # Update via string (CLI format)
    config.update_setting("mirrors", "cargo=https://cargo.local")
    assert "https://cargo.local" in config.get_mirror("cargo")
