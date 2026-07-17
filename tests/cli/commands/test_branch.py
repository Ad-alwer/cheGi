"""Tests for the chegi branch CLI command."""

import subprocess
from pathlib import Path
from typing import List

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


def _git(cmd: List[str], cwd: Path) -> str:
    """Runs a git command in the given directory."""
    result = subprocess.run(
        ["git"] + cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    """Initializes a bare git repo and clones it to create a working copy.

    Returns the working copy path.
    """
    bare = tmp_path / "bare.git"
    bare.mkdir()
    _git(["init", "--bare", str(bare)], tmp_path)

    repo = tmp_path / "repo"
    _git(["clone", str(bare), str(repo)], tmp_path)

    _git(["config", "user.email", "test@test.com"], repo)
    _git(["config", "user.name", "Test User"], repo)

    readme = repo / "README.md"
    readme.write_text("# Test")
    _git(["add", "README.md"], repo)
    _git(["commit", "-m", "Initial commit"], repo)
    _git(["push", "-u", "origin", "main"], repo)

    return repo


class TestBranchList:
    """Tests for 'chegi branch list'."""

    def test_list_branches(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch list' shows branches."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(app, ["branch", "list"])
        assert result.exit_code == 0
        assert "main" in result.stdout

    def test_list_remote(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch list --remote' shows remote branches."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(app, ["branch", "list", "--remote"])
        assert result.exit_code == 0
        assert "main" in result.stdout


class TestBranchCreate:
    """Tests for 'chegi branch create'."""

    def test_create_with_name(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch create test-branch' works."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(
            app,
            ["branch", "create", "test-branch"],
            input="n\nN\n",
        )
        assert result.exit_code == 0
        assert "Created" in result.stdout

    def test_create_interactive(self, tmp_path: Path, monkeypatch) -> None:
        """Test that interactive create asks for name and creates branch."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))

        # Mock questionary prompts for the interactive flow
        import questionary

        monkeypatch.setattr(
            questionary,
            "text",
            lambda *a, **kw: type(
                "Q", (), {"ask": lambda self: "interactive-branch"}
            )(),
        )
        monkeypatch.setattr(
            questionary,
            "select",
            lambda *a, **kw: type("Q", (), {"ask": lambda self: None})(),
        )
        monkeypatch.setattr(
            questionary,
            "confirm",
            lambda *a, **kw: type("Q", (), {"ask": lambda self: False})(),
        )

        result = runner.invoke(app, ["branch", "create"])
        assert result.exit_code == 0
        assert "interactive-branch" in result.stdout or "Created" in result.stdout


class TestBranchSwitch:
    """Tests for 'chegi branch switch'."""

    def test_switch_to_branch(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch switch main' works."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(app, ["branch", "switch", "main"])
        assert result.exit_code == 0

    def test_switch_nonexistent(self, tmp_path: Path, monkeypatch) -> None:
        """Test that switching to a non-existent branch fails."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(app, ["branch", "switch", "nonexistent"])
        assert result.exit_code == 1


class TestBranchMerge:
    """Tests for 'chegi branch merge'."""

    def test_merge_preview_then_abort(self, tmp_path: Path, monkeypatch) -> None:
        """Test that merge preview shows and can be cancelled."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))

        # Create feature branch with a commit
        _git(["branch", "feature-x"], repo)
        _git(["checkout", "feature-x"], repo)
        (repo / "f.txt").write_text("x")
        _git(["add", "f.txt"], repo)
        _git(["commit", "-m", "Feature X"], repo)
        _git(["checkout", "main"], repo)

        result = runner.invoke(
            app,
            ["branch", "merge", "feature-x"],
            input="n\n",  # Don't proceed with merge
        )
        assert result.exit_code == 0
        assert "Preview" in result.stdout or "feature-x" in result.stdout


class TestBranchDelete:
    """Tests for 'chegi branch delete'."""

    def test_delete_branch(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch delete delete-me' works."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        _git(["branch", "delete-me"], repo)
        result = runner.invoke(app, ["branch", "delete", "delete-me"])
        assert result.exit_code == 0
        assert "Deleted" in result.stdout

    def test_delete_protected_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Test that deleting 'main' fails."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(app, ["branch", "delete", "main"])
        assert result.exit_code == 1
        assert "protected" in result.stdout.lower()

    def test_delete_nonexistent_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Test that deleting non-existent branch fails."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(app, ["branch", "delete", "no-such-branch"])
        assert result.exit_code == 1


class TestBranchRename:
    """Tests for 'chegi branch rename'."""

    def test_rename_branch(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch rename old new' works."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        _git(["branch", "old-name"], repo)
        result = runner.invoke(app, ["branch", "rename", "old-name", "new-name"])
        assert result.exit_code == 0
        assert "Renamed" in result.stdout


class TestBranchPushDelete:
    """Tests for 'chegi branch push-delete'."""

    def test_push_delete(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch push-delete pushdel' works."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        _git(["branch", "pushdel"], repo)
        result = runner.invoke(app, ["branch", "push-delete", "pushdel"])
        assert result.exit_code == 0
        assert "Pushed" in result.stdout


class TestBranchSync:
    """Tests for 'chegi branch sync'."""

    def test_sync_branches(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch sync origin' works."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(app, ["branch", "sync", "origin"])
        assert result.exit_code == 0
        assert "prune" in result.stdout.lower() or "No stale" in result.stdout


class TestBranchInfo:
    """Tests for 'chegi branch info'."""

    def test_branch_info_current(self, tmp_path: Path, monkeypatch) -> None:
        """Test that 'chegi branch info' shows current branch info."""
        repo = _init_repo(tmp_path)
        monkeypatch.chdir(str(repo))
        result = runner.invoke(app, ["branch", "info"])
        assert result.exit_code == 0
        assert "main" in result.stdout
        assert "Initial commit" in result.stdout
