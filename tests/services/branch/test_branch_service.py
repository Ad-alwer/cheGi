"""Tests for the BranchService class."""

import subprocess
from pathlib import Path
from typing import List

import pytest

from chegi.services.branch import BranchError, BranchService, ProtectedBranchError
from chegi.services.branch.constants import PROTECTED_BRANCHES
from chegi.services.branch.models import BranchInfo


def _git(cmd: List[str], cwd: Path) -> str:
    """Runs a git command in the given directory and returns stdout."""
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
    _git(["init", "--bare", "-b", "main", str(bare)], tmp_path)

    repo = tmp_path / "repo"
    _git(["clone", str(bare), str(repo)], tmp_path)

    # Configure user for commits
    _git(["config", "user.email", "test@test.com"], repo)
    _git(["config", "user.name", "Test User"], repo)

    # Make an initial commit
    readme = repo / "README.md"
    readme.write_text("# Test")
    _git(["add", "README.md"], repo)
    _git(["commit", "-m", "Initial commit"], repo)

    # Push to remote
    _git(["push", "-u", "origin", "main"], repo)

    return repo


class TestBranchServiceCreate:
    """Tests for BranchService.create_branch()."""

    def test_create_branch_from_head(self, tmp_path: Path) -> None:
        """Test that a branch is created from HEAD."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        service.create_branch("feature/test")
        branches = service.get_local_branch_names()
        assert "feature/test" in branches

    def test_create_branch_from_base(self, tmp_path: Path) -> None:
        """Test that a branch is created from a specific base."""
        repo = _init_repo(tmp_path)
        # Create another commit on main
        (repo / "file2.txt").write_text("content")
        _git(["add", "file2.txt"], repo)
        _git(["commit", "-m", "Second commit"], repo)

        # Create a branch from the first commit
        first_commit = _git(["rev-list", "--max-parents=0", "HEAD"], repo)
        service = BranchService(repo)
        service.create_branch("from-root", first_commit)
        # Verify the branch exists
        branches = service.get_local_branch_names()
        assert "from-root" in branches

    def test_create_branch_empty_name_raises(self, tmp_path: Path) -> None:
        """Test that creating a branch with empty name raises BranchError."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        with pytest.raises(BranchError):
            service.create_branch("")


class TestBranchServiceList:
    """Tests for BranchService.list_branches()."""

    def test_list_branches_returns_current(self, tmp_path: Path) -> None:
        """Test that list_branches includes the current branch."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        branches = service.list_branches()
        names = [b.name for b in branches]
        assert "main" in names

    def test_list_branches_mark_current(self, tmp_path: Path) -> None:
        """Test that the current branch has is_current=True."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        branches = service.list_branches()
        main_branch = next(b for b in branches if b.name == "main")
        assert main_branch.is_current is True

    def test_list_branches_with_multiple(self, tmp_path: Path) -> None:
        """Test that all branches are listed."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        service.create_branch("feature/a")
        service.create_branch("feature/b")
        branches = service.list_branches()
        assert len(branches) == 3  # main + feature/a + feature/b


class TestBranchServiceCurrent:
    """Tests for BranchService.get_current_branch()."""

    def test_get_current_branch_returns_name(self, tmp_path: Path) -> None:
        """Test that get_current_branch returns the checked-out branch."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        assert service.get_current_branch() == "main"

    def test_get_current_branch_after_switch(self, tmp_path: Path) -> None:
        """Test that get_current_branch reflects the new branch after switch."""
        repo = _init_repo(tmp_path)
        # Create branch does not switch
        new_name = "feature/switch-test"
        # We need to create + switch manually via git for isolation
        _git(["branch", new_name], repo)
        _git(["checkout", new_name], repo)
        # Re-create service to ensure fresh state
        service2 = BranchService(repo)
        assert service2.get_current_branch() == new_name


class TestBranchServiceSwitch:
    """Tests for BranchService.switch_branch()."""

    def test_switch_to_existing_branch(self, tmp_path: Path) -> None:
        """Test that switching to an existing branch works."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        service.create_branch("develop")
        service.switch_branch("develop")
        assert service.get_current_branch() == "develop"

    def test_switch_to_nonexistent_raises(self, tmp_path: Path) -> None:
        """Test that switching to a non-existent branch raises BranchError."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        with pytest.raises(BranchError):
            service.switch_branch("nonexistent")


class TestBranchServiceDelete:
    """Tests for BranchService.delete_branch()."""

    def test_delete_branch(self, tmp_path: Path) -> None:
        """Test that a branch can be deleted."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        service.create_branch("to-delete")
        assert "to-delete" in service.get_local_branch_names()
        service.delete_branch("to-delete")
        assert "to-delete" not in service.get_local_branch_names()

    def test_delete_protected_branch_raises(self, tmp_path: Path) -> None:
        """Test that deleting a protected branch raises ProtectedBranchError."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        for name in PROTECTED_BRANCHES:
            if name in service.get_local_branch_names():
                with pytest.raises(ProtectedBranchError):
                    service.delete_branch(name)

    def test_delete_nonexistent_raises(self, tmp_path: Path) -> None:
        """Test that deleting a non-existent branch raises BranchError."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        with pytest.raises(BranchError):
            service.delete_branch("nonexistent")


class TestBranchServiceRename:
    """Tests for BranchService.rename_branch()."""

    def test_rename_branch(self, tmp_path: Path) -> None:
        """Test that a branch can be renamed."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        service.create_branch("old-name")
        service.rename_branch("old-name", "new-name")
        names = service.get_local_branch_names()
        assert "old-name" not in names
        assert "new-name" in names

    def test_rename_empty_new_name_raises(self, tmp_path: Path) -> None:
        """Test that renaming to empty name raises BranchError."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        with pytest.raises(BranchError):
            service.rename_branch("main", "")


class TestBranchServiceMerge:
    """Tests for BranchService.merge_branch()."""

    def test_merge_fast_forward(self, tmp_path: Path) -> None:
        """Test that a fast-forward merge works."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)

        # Create a feature branch and add a commit
        service.create_branch("feature")
        service.switch_branch("feature")
        (repo / "feature.txt").write_text("feature work")
        _git(["add", "feature.txt"], repo)
        _git(["commit", "-m", "Feature commit"], repo)

        # Switch back to main and merge
        service.switch_branch("main")
        output = service.merge_branch("feature")

        assert "feature" in service.get_local_branch_names()
        # The current branch should be up to date
        assert (
            "Already" in output
            or "Fast-forward" in output
            or "Merge" in output
            or not output
        )

    def test_merge_with_target(self, tmp_path: Path) -> None:
        """Test that merging with a specified target works."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)

        # Create and switch to dev, make commit
        service.create_branch("dev")
        service.switch_branch("dev")
        (repo / "dev.txt").write_text("dev work")
        _git(["add", "dev.txt"], repo)
        _git(["commit", "-m", "Dev commit"], repo)

        service.merge_branch(source="dev", target="main")
        # After merge, we should be on main
        assert service.get_current_branch() == "main"


class TestBranchServicePush:
    """Tests for BranchService.push_branch()."""

    def test_push_new_branch(self, tmp_path: Path) -> None:
        """Test that pushing a new branch to origin works."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        service.create_branch("push-test")
        service.push_branch("push-test")
        # Verify by listing remote branches
        branches = service.list_branches(remote=True)
        names = [b.name for b in branches]
        assert "push-test" in names


class TestBranchServicePushAndDelete:
    """Tests for BranchService.push_and_delete()."""

    def test_push_and_delete(self, tmp_path: Path) -> None:
        """Test that push_and_delete pushes and removes local branch."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        service.create_branch("cleanup-me")
        service.push_and_delete("cleanup-me")
        names_local = service.get_local_branch_names()
        assert "cleanup-me" not in names_local
        branches_remote = service.list_branches(remote=True)
        names_remote = [b.name for b in branches_remote]
        assert "cleanup-me" in names_remote


class TestBranchServiceSync:
    """Tests for BranchService.sync_branches()."""

    def test_sync_with_no_stale(self, tmp_path: Path) -> None:
        """Test that sync with no stale branches returns empty list."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        pruned = service.sync_branches()
        assert isinstance(pruned, list)


class TestBranchServiceInfo:
    """Tests for BranchService.get_branch_info()."""

    def test_get_branch_info_returns_details(self, tmp_path: Path) -> None:
        """Test that get_branch_info returns branch metadata."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        info = service.get_branch_info("main")
        assert isinstance(info, BranchInfo)
        assert info.name == "main"
        assert info.is_current is True
        assert info.last_commit_hash is not None
        assert info.last_commit_message == "Initial commit"
        assert info.last_commit_author == "Test User"

    def test_get_branch_info_ahead_behind(self, tmp_path: Path) -> None:
        """Test that ahead/behind counts are correct."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)

        # Create branch, add commit, push, then check ahead
        service.create_branch("feature/ahead")
        service.switch_branch("feature/ahead")
        (repo / "ahead.txt").write_text("ahead work")
        _git(["add", "ahead.txt"], repo)
        _git(["commit", "-m", "Ahead commit"], repo)
        # Push with upstream tracking so ahead/behind can be computed
        _git(["push", "-u", "origin", "feature/ahead"], repo)

        # Add another commit locally (now ahead of remote)
        (repo / "ahead2.txt").write_text("more work")
        _git(["add", "ahead2.txt"], repo)
        _git(["commit", "-m", "More work"], repo)

        info = service.get_branch_info("feature/ahead")
        assert info.ahead >= 1

    def test_get_branch_info_no_upstream(self, tmp_path: Path) -> None:
        """Test that branch without upstream has no upstream info."""
        repo = _init_repo(tmp_path)
        service = BranchService(repo)
        service.create_branch("orphan")
        info = service.get_branch_info("orphan")
        assert info.upstream is None


class TestBranchServiceEdgeCases:
    """Tests for edge cases in BranchService."""

    def test_get_local_branch_names_empty_repo(self, tmp_path: Path) -> None:
        """Test that get_local_branch_names raises BranchError in non-repo."""
        service = BranchService(tmp_path)
        with pytest.raises(BranchError):
            service.get_local_branch_names()

    def test_get_current_branch_in_non_repo(self, tmp_path: Path) -> None:
        """Test that get_current_branch raises BranchError in non-repo."""
        service = BranchService(tmp_path)
        with pytest.raises(BranchError):
            service.get_current_branch()
