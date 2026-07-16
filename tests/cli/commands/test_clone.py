"""Tests for the chegi clone CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


def _mock_auth(token: str = "ghp_test123"):
    """Returns a mock credential with the given token."""
    cred = MagicMock()
    cred.token = token
    return cred


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_direct_url(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests cloning with a direct HTTPS URL."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path / "repo",
        repo_name="repo",
        default_branch="main",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    result = runner.invoke(app, ["clone", "https://github.com/user/repo.git"])
    assert result.exit_code == 0
    mock_service_cls.assert_called_once()
    config = mock_service_cls.call_args[0][0]
    assert config.url == "https://github.com/user/repo.git"
    assert config.repo_name == "repo"


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_shorthand(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests that user/repo shorthand expands to GitHub URL."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path / "chegi",
        repo_name="chegi",
        default_branch="main",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    result = runner.invoke(app, ["clone", "user/chegi"])
    assert result.exit_code == 0
    config = mock_service_cls.call_args[0][0]
    assert config.url == "https://github.com/user/chegi.git"
    assert config.repo_name == "chegi"


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_with_path(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests --path option."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path,
        repo_name="repo",
        default_branch="main",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    result = runner.invoke(app, ["clone", "user/repo", "--path", str(tmp_path)])
    assert result.exit_code == 0
    config = mock_service_cls.call_args[0][0]
    assert config.target_dir == tmp_path


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_here(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests --here flag clones into current directory."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path,
        repo_name="repo",
        default_branch="main",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    with patch.object(Path, "cwd", return_value=tmp_path):
        result = runner.invoke(app, ["clone", "user/repo", "--here"])
    assert result.exit_code == 0
    config = mock_service_cls.call_args[0][0]
    assert config.target_dir == tmp_path


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_with_branch(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests --branch option."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path / "repo",
        repo_name="repo",
        default_branch="develop",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    result = runner.invoke(app, ["clone", "user/repo", "--branch", "develop"])
    assert result.exit_code == 0
    config = mock_service_cls.call_args[0][0]
    assert config.branch == "develop"


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_with_depth(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests --depth option."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path / "repo",
        repo_name="repo",
        default_branch="main",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    result = runner.invoke(app, ["clone", "user/repo", "--depth", "1"])
    assert result.exit_code == 0
    config = mock_service_cls.call_args[0][0]
    assert config.depth == 1


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_no_submodules(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests --no-submodules flag."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path / "repo",
        repo_name="repo",
        default_branch="main",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    result = runner.invoke(app, ["clone", "user/repo", "--no-submodules"])
    assert result.exit_code == 0
    config = mock_service_cls.call_args[0][0]
    assert config.submodules is False


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_no_gitignore(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests --no-gitignore flag."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path / "repo",
        repo_name="repo",
        default_branch="main",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    result = runner.invoke(app, ["clone", "user/repo", "--no-gitignore"])
    assert result.exit_code == 0
    config = mock_service_cls.call_args[0][0]
    assert config.gitignore is False


@patch("chegi.cli.commands.clone.CloneService")
def test_clone_no_chegi(mock_service_cls: MagicMock, tmp_path: Path):
    """Tests --no-chegi flag."""
    mock_instance = MagicMock()
    mock_instance.execute.return_value = MagicMock(
        target_dir=tmp_path / "repo",
        repo_name="repo",
        default_branch="main",
        detected_techs=[],
    )
    mock_service_cls.return_value = mock_instance

    result = runner.invoke(app, ["clone", "user/repo", "--no-chegi"])
    assert result.exit_code == 0
    config = mock_service_cls.call_args[0][0]
    assert config.chegi is False


def test_clone_invalid_url():
    """Tests that an invalid URL shows an error."""
    result = runner.invoke(app, ["clone", "not a valid!!! url"])
    assert result.exit_code == 1


@patch("chegi.cli.commands.clone._execute_clone")
def test_clone_all_flags(mock_execute: MagicMock):
    """Tests that all flags can be combined."""
    result = runner.invoke(
        app,
        [
            "clone",
            "user/repo",
            "--path",
            "/tmp/test",
            "--branch",
            "dev",
            "--depth",
            "5",
            "--no-submodules",
            "--no-gitignore",
            "--no-chegi",
        ],
    )
    assert result.exit_code == 0
