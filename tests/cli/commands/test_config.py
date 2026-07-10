"""
Tests for the config CLI command.
"""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


def test_config_list(tmp_path: Path):
    """Tests listing configuration settings."""
    result = runner.invoke(app, ["config", "list", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Max Depth" in result.stdout


def test_config_set(tmp_path: Path):
    """Tests updating a configuration value."""
    result = runner.invoke(
        app, ["config", "set", "max_depth", "5", "--path", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "Successfully updated 'max_depth' to 5" in result.stdout


def test_config_exclude_add_remove(tmp_path: Path):
    """Tests adding and then removing an item from the exclude list."""
    runner.invoke(app, ["config", "exclude-add", "junk", "--path", str(tmp_path)])
    res_remove = runner.invoke(
        app, ["config", "exclude-remove", "junk", "--path", str(tmp_path)]
    )
    assert res_remove.exit_code == 0
    assert "Removed 'junk'" in res_remove.stdout


# ==========================================
# Configuration Mirror Command Tests
# ==========================================


def test_config_mirror_add(tmp_path: Path):
    """Tests adding a mirror to a specific package manager."""
    result = runner.invoke(
        app,
        [
            "config",
            "mirror-add",
            "npm",
            "https://registry.npmmirror.com",
            "--path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Successfully added/updated mirror" in result.stdout


# NOTE: We patch the ChegiConfig where it is used in the new architecture
@patch("chegi.cli.commands.config.ChegiConfig")
def test_config_mirror_remove_specific(mock_config_cls, tmp_path: Path):
    """Tests removing a specific mirror from configuration."""
    mock_config = mock_config_cls.return_value

    # Mock the 'mirrors' property so the CLI doesn't exit with "No mirror configuration found"
    mock_config.mirrors = {"pip": ["https://mirror1"]}
    mock_config.remove_mirror.return_value = True

    result = runner.invoke(
        app,
        ["config", "mirror-remove", "pip", "https://mirror1", "--path", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Command failed. CLI Output:\n{result.output}"


@patch("chegi.cli.commands.config.ChegiConfig")
def test_config_mirror_remove_all(mock_config_cls, tmp_path: Path):
    """Tests removing all mirrors for a specific package manager."""
    mock_config = mock_config_cls.return_value
    mock_config.mirrors = {"pip": ["https://mirror1"]}
    mock_config.remove_mirror.return_value = True

    # Using catch_exceptions=False to expose the real error if the command fails.
    result = runner.invoke(
        app,
        ["config", "mirror-remove", "pip", "--path", str(tmp_path)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Command failed. CLI Output:\n{result.output}"


def test_config_mirror_clear(tmp_path: Path):
    """Tests clearing all mirror configurations."""
    runner.invoke(
        app, ["config", "mirror-add", "pip", "https://mirror1", "--path", str(tmp_path)]
    )
    result = runner.invoke(app, ["config", "mirror-clear", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "All mirrors have been completely cleared" in result.stdout
