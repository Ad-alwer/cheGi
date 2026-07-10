from pathlib import Path

from chegi.services.git.models import GitStatus


def test_git_status_creation_with_required_fields():
    """Test GitStatus initialization with only required fields to check defaults."""
    status = GitStatus(
        path=Path("/fake/path/myrepo"),
        repo_name="myrepo",
        branch="main",
        is_dirty=False,
        has_remote=True
    )
    
    assert status.path == Path("/fake/path/myrepo")
    assert status.repo_name == "myrepo"
    assert status.branch == "main"
    assert status.is_dirty is False
    assert status.has_remote is True
    

    assert status.error == ""
    assert status.has_staged_files is False
    assert status.security_status is None


def test_git_status_creation_with_all_fields():
    """Test GitStatus initialization with all fields provided explicitly."""
    status = GitStatus(
        path=Path("/another/path/project"),
        repo_name="project",
        branch="feature/test",
        is_dirty=True,
        has_remote=False,
        error="Detached HEAD",
        has_staged_files=True,
        security_status="Pass"
    )
    
    assert status.path == Path("/another/path/project")
    assert status.repo_name == "project"
    assert status.branch == "feature/test"
    assert status.is_dirty is True
    assert status.has_remote is False
    assert status.error == "Detached HEAD"
    assert status.has_staged_files is True
    assert status.security_status == "Pass"
