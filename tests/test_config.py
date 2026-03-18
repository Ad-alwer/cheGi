import json
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
