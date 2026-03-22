import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from chegi.git_utils import GitAnalyzer, GitStatus, check_git_environment

def test_run_git_command_success():
    """
    Test successful execution of a git command.

    Mocks `subprocess.run` to simulate a successful git command execution
    and verifies that the output is correctly stripped and returned.
    """
    analyzer = GitAnalyzer()
    dummy_path = Path("/dummy/path")
    
    # Create a mock CompletedProcess object
    mock_result = MagicMock()
    mock_result.stdout = "  main \n"
    
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        output = analyzer._run_git_command(dummy_path, "branch", "--show-current")
        
        # Verify the subprocess.run was called with correct arguments
        mock_run.assert_called_once_with(
            ["git", "branch", "--show-current"],
            cwd=dummy_path,
            capture_output=True,
            text=True,
            check=True
        )
        # Verify output is stripped
        assert output == "main"

def test_run_git_command_failure():
    """
    Test handling of a failed git command.

    Mocks `subprocess.run` to raise a `CalledProcessError` and verifies
    that `GitAnalyzer` correctly catches it and raises a `RuntimeError`.
    """
    analyzer = GitAnalyzer()
    dummy_path = Path("/dummy/path")
    
    # Simulate a git command failure
    error = subprocess.CalledProcessError(returncode=1, cmd=["git"], stderr="fatal: not a git repo")
    
    with patch("subprocess.run", side_effect=error):
        with pytest.raises(RuntimeError) as exc_info:
            analyzer._run_git_command(dummy_path, "status")
            
        assert "fatal: not a git repo" in str(exc_info.value)

def test_analyze_single_repo_clean():
    """
    Test analyzing a clean repository with a configured remote.

    Mocks `_run_git_command` to return specific outputs simulating a
    clean 'main' branch with an 'origin' remote.
    """
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/my_clean_repo")
    
    # Define what _run_git_command should return for different calls
    def mock_git_command(cwd, *args):
        if args == ("branch", "--show-current"):
            return "main"
        elif args == ("status", "--porcelain"):
            return ""  # Empty string means no uncommitted changes
        elif args == ("remote",):
            return "origin"
        return ""
        
    with patch.object(analyzer, "_run_git_command", side_effect=mock_git_command):
        status = analyzer.analyze_single_repo(repo_path)
        
        assert isinstance(status, GitStatus)
        assert status.repo_name == "my_clean_repo"
        assert status.branch == "main"
        assert status.is_dirty is False
        assert status.has_remote is True
        assert status.error == ""

def test_analyze_single_repo_dirty_no_remote():
    """
    Test analyzing a dirty repository without a configured remote.

    Mocks `_run_git_command` to simulate uncommitted changes and no remotes.
    """
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/dirty_repo")
    
    def mock_git_command(cwd, *args):
        if args == ("branch", "--show-current"):
            return "feature-branch"
        elif args == ("status", "--porcelain"):
            return "M  file.py\n?? new_file.txt"  # Has changes
        elif args == ("remote",):
            return ""  # No remote
        return ""
        
    with patch.object(analyzer, "_run_git_command", side_effect=mock_git_command):
        status = analyzer.analyze_single_repo(repo_path)
        
        assert status.branch == "feature-branch"
        assert status.is_dirty is True
        assert status.has_remote is False

def test_analyze_single_repo_exception_fallback():
    """
    Test the fallback behavior when repository analysis fails.

    If an exception occurs during analysis (e.g., permission denied),
    it should return a GitStatus object with default values and the error message.
    """
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/corrupted_repo")
    
    # Force _run_git_command to raise an error
    with patch.object(analyzer, "_run_git_command", side_effect=RuntimeError("Permission Denied")):
        status = analyzer.analyze_single_repo(repo_path)
        
        assert status.repo_name == "corrupted_repo"
        assert status.branch == "Unknown"
        assert status.is_dirty is False
        assert status.has_remote is False
        assert "Permission Denied" in status.error

def test_analyze_single_repo_with_security_scanner():
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/secure_repo")
    
    def mock_git_command(cwd, *args):
        if args == ("branch", "--show-current"):
            return "main"
        elif args == ("status", "--porcelain"):
            return ""
        elif args == ("remote",):
            return "origin"
        return ""
        
    mock_scanner = MagicMock(return_value="[green]Safe[/green]")
        
    with patch.object(analyzer, "_run_git_command", side_effect=mock_git_command):
        status = analyzer.analyze_single_repo(repo_path, security_scanner=mock_scanner)
        
        assert isinstance(status, GitStatus)
        assert status.security_status == "[green]Safe[/green]"
        mock_scanner.assert_called_once_with(repo_path)


def test_analyze_concurrently():
    analyzer = GitAnalyzer(max_workers=2)
    paths = [Path("/repo1"), Path("/repo2"), Path("/repo3")]
    
    mock_scanner = MagicMock()
    
    def mock_analyze(repo_path, security_scanner=None):
        return GitStatus(
            path=repo_path,
            repo_name=repo_path.name,
            branch="main",
            is_dirty=False,
            has_remote=True,
            security_status="Scanned" if security_scanner else None
        )
        
    with patch.object(analyzer, "analyze_single_repo", side_effect=mock_analyze):
        results = list(analyzer.analyze_concurrently(paths, security_scanner=mock_scanner))
        
        assert len(results) == 3
        
        for res in results:
            assert res.security_status == "Scanned"
            
        result_names = [res.repo_name for res in results]
        assert set(result_names) == {"repo1", "repo2", "repo3"}

def test_check_git_environment_success():
    """Tests successful Git environment validation with a supported version."""
    mock_result = MagicMock()
    mock_result.stdout = "git version 2.34.1\n"
    
    with patch("subprocess.run", return_value=mock_result):
        is_ok, msg = check_git_environment()
        
    assert is_ok is True
    assert "2.34.1" in msg

def test_check_git_environment_old_version():
    """Tests Git environment validation when the installed version is too old."""
    mock_result = MagicMock()
    mock_result.stdout = "git version 2.20.0\n"
    
    with patch("subprocess.run", return_value=mock_result):
        is_ok, msg = check_git_environment()
        
    assert is_ok is False
    assert "too old" in msg

def test_check_git_environment_not_installed():
    """Tests Git environment validation when Git is not installed."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        is_ok, msg = check_git_environment()
        
    assert is_ok is False
    assert "not installed" in msg

def test_check_git_environment_unexpected_error():
    """Tests Git environment validation handling of unexpected exceptions."""
    with patch("subprocess.run", side_effect=Exception("Unknown Error")):
        is_ok, msg = check_git_environment()
        
    assert is_ok is False
    assert "unexpected error" in msg
