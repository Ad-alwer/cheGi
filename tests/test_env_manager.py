import json
import pytest
from unittest.mock import patch, MagicMock
from chegi.env_manager import EnvManager


@pytest.fixture
def dummy_json_data():
    return {
        "name": "Python",
        "levels": {"1": ["pip"]},
        "tools": {
            "pip": {"check_cmd": "pip --version"}
        }
    }


@patch("chegi.env_manager.pkg_resources.files")
def test_load_environments_success(mock_files, dummy_json_data):
    """Tests successful loading of JSON environment files."""
    mock_file = MagicMock()
    mock_file.is_file.return_value = True
    mock_file.name = "python.json"
    mock_file.read_text.return_value = json.dumps(dummy_json_data)
    
    mock_dir = MagicMock()
    mock_dir.iterdir.return_value = [mock_file]
    mock_files.return_value = mock_dir

    manager = EnvManager()

    assert "python" in manager.db
    assert manager.db["python"]["name"] == "Python"


@patch("chegi.env_manager.pkg_resources.files")
def test_load_environments_exception(mock_files):
    """Tests that exceptions during loading are silently handled."""
    mock_files.side_effect = Exception("Simulated error")
    
    manager = EnvManager()
    
    assert manager.db == {}


@patch("chegi.env_manager.EnvManager.load_environments")
def test_get_language(mock_load, dummy_json_data):
    """Tests retrieving a specific language by name."""
    manager = EnvManager()
    manager.db = {"python": dummy_json_data}
    
    assert manager.get_language("Python") == dummy_json_data
    assert manager.get_language("PYTHON") == dummy_json_data
    assert manager.get_language("ruby") is None


@patch("chegi.env_manager.EnvManager.load_environments")
def test_get_tool(mock_load, dummy_json_data):
    """Tests searching for a tool across all environments."""
    manager = EnvManager()
    manager.db = {"python": dummy_json_data}
    
    assert manager.get_tool("pip") == {"check_cmd": "pip --version"}
    assert manager.get_tool("PIP") == {"check_cmd": "pip --version"}
    assert manager.get_tool("gem") is None


@patch("chegi.env_manager.EnvManager.load_environments")
def test_get_available_envs(mock_load):
    """Tests retrieving the list of available environment names."""
    manager = EnvManager()
    manager.db = {"python": {}, "ruby": {}, "node": {}}
    
    envs = manager.get_available_envs()
    
    assert sorted(envs) == ["node", "python", "ruby"]


@patch("chegi.env_manager.EnvManager.load_environments")
def test_get_env(mock_load, dummy_json_data):
    """Tests that get_env alias correctly calls get_language."""
    manager = EnvManager()
    manager.db = {"python": dummy_json_data}
    
    assert manager.get_env("python") == dummy_json_data
    assert manager.get_env("unknown") is None
