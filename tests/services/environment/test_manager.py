import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.environment.exceptions import NoEnvironmentsProvidedError
from chegi.services.environment.manager import EnvManager
from chegi.services.environment.models import EnvironmentPreset, ToolConfig


@pytest.fixture
def dummy_json_data():
    return {
        "name": "Python",
        "description": "Python dev environment",
        "gitignore": ["*.pyc", "__pycache__/"],
        "tools": {
            "pip": {
                "command": "python",
                "args": ["-m", "ensurepip"],
                "description": "Python package installer"
            }
        },
    }


@patch("chegi.services.environment.manager.pkg_resources.files")
def test_load_environments_success(mock_files, dummy_json_data):
    """Tests successful loading and parsing of JSON presets into Dataclasses."""
    mock_file = MagicMock()
    mock_file.is_file.return_value = True
    mock_file.name = "python.json"
    mock_file.read_text.return_value = json.dumps(dummy_json_data)

    mock_dir = MagicMock()
    mock_dir.iterdir.return_value = [mock_file]
    mock_files.return_value = mock_dir

    manager = EnvManager()
    preset = manager.db.get("python")

    assert "python" in manager.db
    assert isinstance(preset, EnvironmentPreset)
    assert preset.name == "Python"
    assert isinstance(preset.tools["pip"], ToolConfig)
    assert preset.tools["pip"].command == "python"
    assert preset.tools["pip"].args == ["-m", "ensurepip"]


@patch("chegi.services.environment.manager.pkg_resources.files")
def test_load_environments_preserves_levels_and_raw_tools(mock_files):
    """Tests that levels, levels_info, and raw_tools are preserved from JSON."""
    data = {
        "name": "Go",
        "description": "Go dev environment",
        "levels": {"1": ["go", "gofmt"], "2": ["golangci-lint"]},
        "levels_info": {"1": "Essential", "2": "Recommended"},
        "tools": {
            "go": {"command": "go", "args": ["version"], "description": "Go compiler"},
            "gofmt": {"command": "gofmt", "args": [], "description": "Go formatter"},
            "golangci-lint": {"command": "golangci-lint", "args": ["run"], "description": "Go linter"},
        },
        "gitignore": ["*.exe"],
    }
    mock_file = MagicMock()
    mock_file.is_file.return_value = True
    mock_file.name = "go.json"
    mock_file.read_text.return_value = json.dumps(data)
    mock_dir = MagicMock()
    mock_dir.iterdir.return_value = [mock_file]
    mock_files.return_value = mock_dir

    manager = EnvManager()
    preset = manager.db.get("go")

    assert preset is not None
    assert preset.levels == {"1": ["go", "gofmt"], "2": ["golangci-lint"]}
    assert preset.levels_info == {"1": "Essential", "2": "Recommended"}
    assert "go" in preset.raw_tools
    assert preset.raw_tools["go"]["command"] == "go"
    assert isinstance(preset.tools["go"], ToolConfig)


@patch("chegi.services.environment.manager.pkg_resources.files")
def test_load_environments_exception_handling(mock_files):
    """Tests that a missing presets directory results in an empty database."""
    mock_files.side_effect = FileNotFoundError("Presets directory not found")
    manager = EnvManager()
    assert manager.db == {}


@patch("chegi.services.environment.manager.pkg_resources.files")
def test_load_environments_bad_json_skipped(mock_files, tmp_path):
    """Tests that a corrupted JSON file is skipped without breaking the whole load."""
    preset_dir = tmp_path / "presets"
    preset_dir.mkdir()
    (preset_dir / "good.json").write_text('{"name": "Python", "tools": {}}')
    (preset_dir / "bad.json").write_text("this is not json")

    mock_files.return_value = preset_dir
    manager = EnvManager()
    assert "python" in manager.db
    assert len(manager.db) == 1


@patch("chegi.services.environment.manager.pkg_resources.files")
def test_load_environments_unexpected_error_propagates(mock_files):
    """Tests that an unexpected error during loading propagates instead of being swallowed."""
    mock_files.side_effect = RuntimeError("Something unexpected broke")
    with pytest.raises(RuntimeError, match="Something unexpected broke"):
        EnvManager()


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_get_language(mock_load, dummy_json_data):
    """Tests retrieving a specific language by name (case-insensitive)."""
    manager = EnvManager()
    preset = EnvironmentPreset(
        name=dummy_json_data["name"],
        description=dummy_json_data["description"],
        gitignore=dummy_json_data["gitignore"],
        tools={"pip": ToolConfig(**dummy_json_data["tools"]["pip"])}
    )
    manager.db = {"python": preset}

    result = manager.get_language("Python")
    
    assert isinstance(result, EnvironmentPreset)
    assert result.name == "Python"
    assert manager.get_language("PYTHON").name == "Python"
    assert manager.get_language("ruby") is None


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_get_tool(mock_load, dummy_json_data):
    """Tests searching for a tool across all environments."""
    manager = EnvManager()
    preset = EnvironmentPreset(
        name=dummy_json_data["name"],
        description=dummy_json_data["description"],
        gitignore=[],
        tools={"pip": ToolConfig(**dummy_json_data["tools"]["pip"])}
    )
    manager.db = {"python": preset}

    tool = manager.get_tool("pip")
    
    assert isinstance(tool, ToolConfig)
    assert tool.command == "python"
    assert manager.get_tool("gem") is None


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_get_available_envs(mock_load):
    """Tests retrieving the sorted list of available environment names."""
    manager = EnvManager()
    manager.db = {"python": MagicMock(), "ruby": MagicMock(), "node": MagicMock()}
    
    assert sorted(manager.get_available_envs()) == ["node", "python", "ruby"]


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_get_envs_with_gitignore(mock_load):
    """Tests filtering environments that actually define a gitignore array."""
    manager = EnvManager()
    manager.db = {
        "python": EnvironmentPreset(name="Python", description="", tools={}, gitignore=["*.pyc"]),
        "ruby": EnvironmentPreset(name="Ruby", description="", tools={}, gitignore=[]),
        "node": EnvironmentPreset(name="Node", description="", tools={}, gitignore=["node_modules/"]),
    }

    assert sorted(manager.get_envs_with_gitignore()) == ["node", "python"]


@patch("chegi.services.environment.manager.EnvManager.load_environments")
@patch("pathlib.Path.exists")
def test_has_existing_gitignore(mock_exists, mock_load):
    """Tests checking for existing .gitignore files using pathlib."""
    manager = EnvManager()
    
    mock_exists.return_value = True
    assert manager.has_existing_gitignore(Path("/fake/dir")) is True

    mock_exists.return_value = False
    assert manager.has_existing_gitignore(Path("/fake/dir")) is False


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_generate_gitignore_empty_list(mock_load):
    """Tests that generating a gitignore without environments raises custom error."""
    manager = EnvManager()
    with pytest.raises(NoEnvironmentsProvidedError):
        manager.generate_gitignore([], Path("/fake/dir"))


@patch("chegi.services.environment.manager.EnvManager.load_environments")
@patch("pathlib.Path.write_text")
def test_generate_gitignore_success(mock_write_text, mock_load):
    """Tests generating, deduplicating, and writing gitignore content."""
    manager = EnvManager()
    manager.db = {
        "python": EnvironmentPreset(name="Python", description="", tools={}, gitignore=["*.pyc", ".env"]),
        "node": EnvironmentPreset(name="Node", description="", tools={}, gitignore=["node_modules/", ".env"]),
    }

    manager.generate_gitignore(["python", "node"], Path("/fake/dir"))
    written_content = mock_write_text.call_args[0][0]

    assert "# .gitignore generated by Chegi for: Python, Node" in written_content
    assert "*.pyc" in written_content
    assert "node_modules/" in written_content
    assert ".DS_Store" in written_content
    assert written_content.count("\nnode_modules/\n") == 1


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_get_required_package_managers(mock_load):
    """Tests extracting unique tools across requested environments."""
    manager = EnvManager()
    manager.db = {
        "python": EnvironmentPreset(name="Py", description="", gitignore=[], tools={
            "pip": ToolConfig(command="pip", args=[]), 
            "poetry": ToolConfig(command="poetry", args=[])
        }),
        "node": EnvironmentPreset(name="Node", description="", gitignore=[], tools={
            "npm": ToolConfig(command="npm", args=[]), 
            "yarn": ToolConfig(command="yarn", args=[])
        }),
    }

    pms = manager.get_required_package_managers(["python", "node"])
    assert pms == {"pip", "poetry", "npm", "yarn"}


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_find_setup_target_as_environment(mock_load):
    """Tests finding a target that is a full environment."""
    manager = EnvManager()
    python_env = EnvironmentPreset(
        name="Python", description="", gitignore=[], 
        tools={"pip": ToolConfig(command="pip", args=[])}
    )
    manager.db = {"python": python_env}

    result = manager.find_setup_target("python")
    
    assert result is python_env
    assert isinstance(result, EnvironmentPreset)


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_find_setup_target_as_standalone_tool(mock_load):
    """Tests finding a tool and dynamically wrapping it in an EnvironmentPreset."""
    manager = EnvManager()
    postman_tool = ToolConfig(command="snap", args=["install", "postman"], description="Postman API")
    manager.db = {"apps": EnvironmentPreset(
        name="Apps", description="", gitignore=[], 
        tools={"postman": postman_tool}
    )}

    result = manager.find_setup_target("postman")

    assert isinstance(result, EnvironmentPreset)
    assert result.name == "Postman API"
    assert "Standalone tool" in result.description
    assert result.tools["postman"] is postman_tool


@patch("chegi.services.environment.manager.EnvManager.load_environments")
def test_find_setup_target_not_found(mock_load):
    """Tests returning None for unknown targets."""
    manager = EnvManager()
    manager.db = {"python": EnvironmentPreset(
        name="Python", description="", gitignore=[], 
        tools={"pip": ToolConfig(command="pip", args=[])}
    )}

    assert manager.find_setup_target("unknown_target") is None
