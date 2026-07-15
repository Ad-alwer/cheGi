"""Tests for Git alias commands (co, br, ci, st)."""

from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


def _ok_mock():
    m = MagicMock()
    m.stdout = "2.43.0\n"
    return m


# ── co (checkout) ────────────────────────────────────────────


@patch("chegi.cli.commands.aliases.subprocess.run")
def test_co_passes_args_to_git_checkout(mock_run: MagicMock):
    """Tests that chegi co passes args to git checkout."""
    mock_run.side_effect = [_ok_mock(), _ok_mock()]

    result = runner.invoke(app, ["co", "main"])

    assert result.exit_code == 0
    mock_run.assert_any_call(["git", "checkout", "main"], check=True)


@patch("chegi.cli.commands.aliases.subprocess.run")
def test_co_with_flag(mock_run: MagicMock):
    """Tests that chegi co -b passes through."""
    mock_run.side_effect = [_ok_mock(), _ok_mock()]

    result = runner.invoke(app, ["co", "-b", "feature"])

    assert result.exit_code == 0
    mock_run.assert_any_call(["git", "checkout", "-b", "feature"], check=True)


# ── br (branch) ──────────────────────────────────────────────


@patch("chegi.cli.commands.aliases.subprocess.run")
def test_br_lists_branches(mock_run: MagicMock):
    """Tests that chegi br lists branches."""
    mock_run.side_effect = [_ok_mock(), _ok_mock()]

    result = runner.invoke(app, ["br"])

    assert result.exit_code == 0
    mock_run.assert_any_call(["git", "branch"], check=True)


@patch("chegi.cli.commands.aliases.subprocess.run")
def test_br_with_args(mock_run: MagicMock):
    """Tests that chegi br -a passes through."""
    mock_run.side_effect = [_ok_mock(), _ok_mock()]

    result = runner.invoke(app, ["br", "-a"])

    assert result.exit_code == 0
    mock_run.assert_any_call(["git", "branch", "-a"], check=True)


# ── ci (commit) ──────────────────────────────────────────────


@patch("chegi.cli.commands.aliases.subprocess.run")
def test_ci_with_message(mock_run: MagicMock):
    """Tests that chegi ci -m passes through."""
    mock_run.side_effect = [_ok_mock(), _ok_mock()]

    result = runner.invoke(app, ["ci", "-m", "feat: add stuff"])

    assert result.exit_code == 0
    mock_run.assert_any_call(["git", "commit", "-m", "feat: add stuff"], check=True)


# ── st (status) ──────────────────────────────────────────────


@patch("chegi.cli.commands.aliases.subprocess.run")
def test_st_shows_status(mock_run: MagicMock):
    """Tests that chegi st shows git status."""
    mock_run.side_effect = [_ok_mock(), _ok_mock()]

    result = runner.invoke(app, ["st"])

    assert result.exit_code == 0
    mock_run.assert_any_call(["git", "status"], check=True)


# ── Error handling ───────────────────────────────────────────


@patch("chegi.cli.commands.aliases.subprocess.run")
def test_alias_handles_git_not_found(mock_run: MagicMock):
    """Tests graceful handling when git is not installed."""
    mock_run.side_effect = [_ok_mock(), FileNotFoundError()]

    result = runner.invoke(app, ["co"])

    assert result.exit_code == 1


@patch("chegi.cli.commands.aliases.subprocess.run")
def test_alias_handles_git_error(mock_run: MagicMock):
    """Tests graceful handling when git command fails."""
    mock_run.side_effect = [_ok_mock(), CalledProcessError(128, "git")]

    result = runner.invoke(app, ["co", "nonexistent"])

    assert result.exit_code == 128
