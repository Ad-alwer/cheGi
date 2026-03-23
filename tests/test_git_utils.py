import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from chegi.git_utils import GitAnalyzer, GitStatus, check_git_environment

def test_run_git_command_success():
    """Test successful execution of a git command."""
    analyzer = GitAnalyzer()
    dummy_path = Path("/dummy/path")
    mock_result = MagicMock()
    mock_result.stdout = "  main \n"
    
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        output = analyzer._run_git_command(dummy_path, "branch", "--show-current")
        
        mock_run.assert_called_once_with(
            ["git", "branch", "--show-current"],
            cwd=dummy_path,
            capture_output=True,
            text=True,
            check=True
        )
        assert output == "main"

def test_run_git_command_failure():
    """Test handling of a failed git command."""
    analyzer = GitAnalyzer()
    dummy_path = Path("/dummy/path")
    error = subprocess.CalledProcessError(returncode=1, cmd=["git"], stderr="fatal: not a git repo")
    
    with patch("subprocess.run", side_effect=error):
        with pytest.raises(RuntimeError) as exc_info:
            analyzer._run_git_command(dummy_path, "status")
            
        assert "fatal: not a git repo" in str(exc_info.value)

def test_analyze_single_repo_clean():
    """Test analyzing a clean repository with a configured remote."""
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/my_clean_repo")
    
    def mock_git_command(cwd, *args):
        if args == ("branch", "--show-current"):
            return "main"
        elif args == ("status", "--porcelain"):
            return ""
        elif args == ("remote",):
            return "origin"
        elif args == ("diff", "--cached", "--name-only"):
            return ""
        return ""
        
    with patch.object(analyzer, "_run_git_command", side_effect=mock_git_command):
        status = analyzer.analyze_single_repo(repo_path)
        
        assert isinstance(status, GitStatus)
        assert status.repo_name == "my_clean_repo"
        assert status.branch == "main"
        assert status.is_dirty is False
        assert status.has_staged_files is False
        assert status.has_remote is True
        assert status.error == ""

def test_analyze_single_repo_dirty_no_remote():
    """Test analyzing a dirty repository without a configured remote."""
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/dirty_repo")
    
    def mock_git_command(cwd, *args):
        if args == ("branch", "--show-current"):
            return "feature-branch"
        elif args == ("status", "--porcelain"):
            # ' M' (space then M) means NOT staged. 'M ' (M then space) means staged.
            return " M file.py\n?? new_file.txt" 
        elif args == ("remote",):
            return ""
        elif args == ("diff", "--cached", "--name-only"):
            return ""
        return ""
        
    with patch.object(analyzer, "_run_git_command", side_effect=mock_git_command):
        status = analyzer.analyze_single_repo(repo_path)
        
        assert status.branch == "feature-branch"
        assert status.is_dirty is True
        assert status.has_staged_files is False
        assert status.has_remote is False

def test_analyze_single_repo_with_staged_files():
    """Test analyzing a repository that has files in the staging area."""
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/staged_repo")
    
    def mock_git_command(cwd, *args):
        if args == ("branch", "--show-current"):
            return "main"
        elif args == ("status", "--porcelain"):
            return "M  file.py"
        elif args == ("remote",):
            return "origin"
        elif args == ("diff", "--cached", "--name-only"):
            return "file.py"
        return ""
        
    with patch.object(analyzer, "_run_git_command", side_effect=mock_git_command):
        status = analyzer.analyze_single_repo(repo_path)
        
        assert status.is_dirty is True
        assert status.has_staged_files is True

def test_analyze_single_repo_exception_fallback():
    """Test fallback behavior when repository analysis fails."""
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/corrupted_repo")
    
    with patch.object(analyzer, "_run_git_command", side_effect=RuntimeError("Permission Denied")):
        status = analyzer.analyze_single_repo(repo_path)
        
        assert status.repo_name == "corrupted_repo"
        assert status.branch == "Unknown"
        assert status.is_dirty is False
        assert status.has_staged_files is False
        assert status.has_remote is False
        assert "Permission Denied" in status.error

def test_analyze_single_repo_with_security_scanner():
    """Test scan with security scanner integration."""
    analyzer = GitAnalyzer()
    repo_path = Path("/projects/secure_repo")
    
    def mock_git_command(cwd, *args):
        if args == ("branch", "--show-current"):
            return "main"
        elif args == ("status", "--porcelain"):
            return ""
        elif args == ("remote",):
            return "origin"
        elif args == ("diff", "--cached", "--name-only"):
            return ""
        return ""
        
    mock_scanner = MagicMock(return_value="[green]Safe[/green]")
        
    with patch.object(analyzer, "_run_git_command", side_effect=mock_git_command):
        status = analyzer.analyze_single_repo(repo_path, security_scanner=mock_scanner)
        
        assert isinstance(status, GitStatus)
        assert status.security_status == "[green]Safe[/green]"
        mock_scanner.assert_called_once_with(repo_path)

def test_analyze_concurrently():
    """Test concurrent analysis of multiple repositories."""
    analyzer = GitAnalyzer(max_workers=2)
    paths = [Path("/repo1"), Path("/repo2"), Path("/repo3")]
    mock_scanner = MagicMock()
    
    def mock_analyze(repo_path, security_scanner=None):
        return GitStatus(
            path=repo_path,
            repo_name=repo_path.name,
            branch="main",
            is_dirty=False,
            has_staged_files=False,
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
    """Tests successful Git environment validation."""
    mock_result = MagicMock()
    mock_result.stdout = "git version 2.34.1\n"
    
    with patch("subprocess.run", return_value=mock_result):
        is_ok, msg = check_git_environment()
        
    assert is_ok is True
    assert "2.34.1" in msg

def test_check_git_environment_old_version():
    """Tests validation when Git version is too old."""
    mock_result = MagicMock()
    mock_result.stdout = "git version 2.20.0\n"
    
    with patch("subprocess.run", return_value=mock_result):
        is_ok, msg = check_git_environment()
        
    assert is_ok is False
    assert "too old" in msg

def test_check_git_environment_not_installed():
    """Tests validation when Git is not installed."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        is_ok, msg = check_git_environment()
        
    assert is_ok is False
    assert "not installed" in msg

def test_check_git_environment_unexpected_error():
    """Tests handling of unexpected exceptions during environment check."""
    with patch("subprocess.run", side_effect=Exception("Unknown Error")):
        is_ok, msg = check_git_environment()
        
    assert is_ok is False
    assert "unexpected error" in msg
