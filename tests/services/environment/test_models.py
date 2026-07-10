from chegi.services.environment.models import EnvironmentPreset, ToolConfig


def test_tool_config_creation_with_all_fields():
    """Test ToolConfig initialization with all provided fields."""
    tool = ToolConfig(
        command="python", args=["-m", "venv"], description="Creates virtual env"
    )
    assert tool.command == "python"
    assert tool.args == ["-m", "venv"]
    assert tool.description == "Creates virtual env"


def test_tool_config_creation_without_optional_fields():
    """Test ToolConfig initialization without the optional description field."""
    tool = ToolConfig(command="npm", args=["install"])
    assert tool.command == "npm"
    assert tool.args == ["install"]
    assert tool.description is None


def test_environment_preset_with_list_gitignore():
    """Test EnvironmentPreset initialization with a list for gitignore."""
    tool = ToolConfig(command="pip", args=["install"])
    preset = EnvironmentPreset(
        name="python",
        description="Python development environment",
        tools={"pip": tool},
        gitignore=["*.pyc", "__pycache__/"],
    )
    assert preset.name == "python"
    assert preset.description == "Python development environment"
    assert "pip" in preset.tools
    assert preset.tools["pip"].command == "pip"
    assert isinstance(preset.gitignore, list)
    assert preset.gitignore == ["*.pyc", "__pycache__/"]


def test_environment_preset_with_string_gitignore():
    """Test EnvironmentPreset initialization with a string for gitignore."""
    preset = EnvironmentPreset(
        name="node",
        description="Node.js environment",
        tools={},
        gitignore="node_modules/\n.env",
    )
    assert preset.name == "node"
    assert isinstance(preset.gitignore, str)
    assert preset.gitignore == "node_modules/\n.env"
