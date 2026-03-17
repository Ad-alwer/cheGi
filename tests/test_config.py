import json
from pathlib import Path
from chegi.config import load_config, DEFAULT_EXCLUDES

def test_load_config_defaults(tmp_path: Path):
    """Test that load_config returns default excludes when no config file exists."""
    # tmp_path is an empty temporary directory provided by pytest
    excludes = load_config(str(tmp_path))
    assert excludes == DEFAULT_EXCLUDES

def test_load_config_with_custom_file(tmp_path: Path):
    """Test that custom excludes are merged with defaults."""
    config_file = tmp_path / ".chegi.json"
    config_data = {"exclude_dirs": ["my_custom_folder", "build_cache"]}
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    excludes = load_config(str(tmp_path))
    
    # Check if a default value is present
    assert "node_modules" in excludes
    # Check if custom values were successfully merged
    assert "my_custom_folder" in excludes
    assert "build_cache" in excludes
    # Ensure total length is correct
    assert len(excludes) == len(DEFAULT_EXCLUDES) + 2

def test_load_config_invalid_json(tmp_path: Path):
    """Test fallback to defaults if the JSON is malformed."""
    config_file = tmp_path / ".chegi.json"
    config_file.write_text("{this is not valid json}", encoding="utf-8")

    excludes = load_config(str(tmp_path))
    assert excludes == DEFAULT_EXCLUDES
