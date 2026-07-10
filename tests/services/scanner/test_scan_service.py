from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from chegi.services.guard.models import GuardScanResult
from chegi.services.scanner.exceptions import InvalidDirectoryError
from chegi.services.scanner.models import ScanOptions
from chegi.services.scanner.scan_service import ScanService


@pytest.fixture
def base_scan_kwargs():
    """Provide base keyword arguments for ScanOptions."""
    return {
        "path": ".",
        "max_depth": None,
        "workers": 2,
        "security": False,
        "dirty": False,
        "staged": False,
    }


@patch("chegi.services.scanner.scan_service.ChegiConfig")
def test_init_config_override(mock_config_cls, base_scan_kwargs):
    """Test that config max_depth is overridden when provided in options."""
    kwargs = {**base_scan_kwargs, "max_depth": 5}
    service = ScanService(ScanOptions(**kwargs))

    assert service.config.max_depth == 5
    mock_config_cls.assert_called_once()
    mock_config_cls.return_value.load.assert_not_called()


# Finder Logic Tests


def test_find_git_repos_invalid_dir(base_scan_kwargs):
    """Test finding repos raises InvalidDirectoryError for non-existent path."""
    service = ScanService(ScanOptions(**base_scan_kwargs))
    with pytest.raises(InvalidDirectoryError, match="does not exist"):
        list(service._find_git_repos("/path/that/does/not/exist/12345"))


def test_find_git_repos_success(tmp_path: Path, base_scan_kwargs):
    """Test successfully finding valid Git repositories."""
    service = ScanService(ScanOptions(**base_scan_kwargs))
    service.config.max_depth = 3
    service.config.exclude_dirs.clear()
    service.config.exclude_dirs.update(["node_modules", "venv"])

    # Setup dummy directory structure
    repo1 = tmp_path / "project1"
    repo1.mkdir()
    (repo1 / ".git").mkdir()

    repo2 = tmp_path / "project2"
    repo2.mkdir()
    (repo2 / ".git").mkdir()

    not_repo = tmp_path / "project3"
    not_repo.mkdir()

    repos = list(service._find_git_repos(str(tmp_path)))

    assert len(repos) == 2
    assert repo1.resolve() in repos
    assert repo2.resolve() in repos


def test_find_git_repos_max_depth(tmp_path: Path, base_scan_kwargs):
    """Test that repository discovery respects the max_depth configuration."""
    service = ScanService(ScanOptions(**base_scan_kwargs))
    service.config.max_depth = 2
    service.config.exclude_dirs.clear()

    deep_repo = tmp_path / "level1" / "level2" / "repo"
    deep_repo.mkdir(parents=True)
    (deep_repo / ".git").mkdir()

    shallow_repo = tmp_path / "repo2"
    shallow_repo.mkdir()
    (shallow_repo / ".git").mkdir()

    repos = list(service._find_git_repos(str(tmp_path)))

    assert len(repos) == 1
    assert shallow_repo.resolve() in repos


def test_find_git_repos_ignore_dirs(tmp_path: Path, base_scan_kwargs):
    """Test that ignored directories are not scanned for repositories."""
    service = ScanService(ScanOptions(**base_scan_kwargs))
    service.config.exclude_dirs.clear()
    service.config.exclude_dirs.update(["node_modules", ".hidden_folder"])

    # Excluded directory
    excluded_dir = tmp_path / "node_modules" / "repo"
    excluded_dir.mkdir(parents=True)
    (excluded_dir / ".git").mkdir()

    # Hidden/Ignored directory
    hidden_dir = tmp_path / ".hidden_folder" / "repo"
    hidden_dir.mkdir(parents=True)
    (hidden_dir / ".git").mkdir()

    valid_repo = tmp_path / "valid_repo"
    valid_repo.mkdir()
    (valid_repo / ".git").mkdir()

    repos = list(service._find_git_repos(str(tmp_path)))

    assert len(repos) == 1
    assert valid_repo.resolve() in repos


def test_find_git_repos_smart_pruning(tmp_path: Path, base_scan_kwargs):
    """Ensure that once a repo is found, it does not scan its subdirectories."""
    service = ScanService(ScanOptions(**base_scan_kwargs))
    service.config.exclude_dirs.clear()

    parent_repo = tmp_path / "parent_repo"
    parent_repo.mkdir()
    (parent_repo / ".git").mkdir()

    # Nested repo (should not be found because of pruning)
    child_repo = parent_repo / "sub_repo"
    child_repo.mkdir()
    (child_repo / ".git").mkdir()

    repos = list(service._find_git_repos(str(tmp_path)))

    assert len(repos) == 1
    assert parent_repo.resolve() in repos


# Scanner Flow Tests


@patch.object(ScanService, "_find_git_repos")
def test_get_repositories_success(mock_find, base_scan_kwargs):
    """Test successful retrieval of repositories using mocked finder."""
    mock_find.return_value = [Path("/mock/repo1"), Path("/mock/repo2")]
    service = ScanService(ScanOptions(**base_scan_kwargs))

    repos = service._get_repositories()
    assert repos == [Path("/mock/repo1"), Path("/mock/repo2")]


@patch.object(ScanService, "_find_git_repos")
@patch("chegi.services.scanner.scan_service.TerminalUI.print_error")
def test_get_repositories_not_a_dir(mock_print_error, mock_find, base_scan_kwargs):
    """Test get_repositories exits gracefully on InvalidDirectoryError."""
    mock_find.side_effect = InvalidDirectoryError("Invalid path")
    service = ScanService(ScanOptions(**base_scan_kwargs))

    with pytest.raises(typer.Exit) as exc_info:
        service._get_repositories()

    assert exc_info.value.exit_code == 1
    mock_print_error.assert_called_once_with("Invalid path")


def test_filter_results(base_scan_kwargs):
    """Test filtering repository statuses based on dirty and staged flags."""
    dirty_repo = MagicMock(is_dirty=True, has_staged_files=False)
    staged_repo = MagicMock(is_dirty=True, has_staged_files=True)
    clean_repo = MagicMock(is_dirty=False, has_staged_files=False)

    statuses = [dirty_repo, staged_repo, clean_repo]

    # Test dirty filter
    kwargs_dirty = {**base_scan_kwargs, "dirty": True}
    service_dirty = ScanService(ScanOptions(**kwargs_dirty))
    filtered = service_dirty._filter_results(statuses)
    assert len(filtered) == 2
    assert clean_repo not in filtered

    # Test staged filter
    kwargs_staged = {**base_scan_kwargs, "staged": True}
    service_staged = ScanService(ScanOptions(**kwargs_staged))
    filtered = service_staged._filter_results(statuses)
    assert len(filtered) == 1
    assert staged_repo in filtered


@patch.object(ScanService, "_analyze_single_repo")
def test_analyze_repositories(mock_analyze_single, base_scan_kwargs):
    """Test concurrent analysis of multiple repositories."""
    mock_analyze_single.side_effect = ["status1", "status2"]

    service = ScanService(ScanOptions(**base_scan_kwargs))
    statuses = service._analyze_repositories([Path("/path1"), Path("/path2")])

    assert set(statuses) == {"status1", "status2"}
    assert mock_analyze_single.call_count == 2


@patch.object(ScanService, "_get_repositories")
@patch("chegi.services.scanner.scan_service.display_results_table")
def test_execute_no_repos(mock_display, mock_get_repos, base_scan_kwargs):
    """Test execute method when no repositories are found."""
    mock_get_repos.return_value = []
    service = ScanService(ScanOptions(**base_scan_kwargs))
    service.execute()

    mock_display.assert_called_once_with([])


@patch.object(ScanService, "_get_repositories")
@patch.object(ScanService, "_analyze_repositories")
@patch.object(ScanService, "_filter_results")
@patch("chegi.services.scanner.scan_service.display_results_table")
def test_execute_full_flow(
    mock_display, mock_filter, mock_analyze, mock_get_repos, base_scan_kwargs
):
    """Test the complete execute flow with finding, analyzing, and filtering."""
    mock_get_repos.return_value = ["/path1"]
    mock_analyze.return_value = ["raw_status"]
    mock_filter.return_value = ["filtered_status"]

    service = ScanService(ScanOptions(**base_scan_kwargs))
    service.execute()

    mock_get_repos.assert_called_once()
    mock_analyze.assert_called_once_with(["/path1"])
    mock_filter.assert_called_once_with(["raw_status"])
    mock_display.assert_called_once_with(["filtered_status"])


@patch.object(ScanService, "_get_repositories")
@patch.object(ScanService, "_analyze_repositories")
@patch.object(ScanService, "_filter_results")
@patch("chegi.services.scanner.scan_service.display_results_table")
@patch("chegi.services.scanner.scan_service.console.print")
def test_execute_filtered_out_all(
    mock_print,
    mock_display,
    mock_filter,
    mock_analyze,
    mock_get_repos,
    base_scan_kwargs,
):
    """Test execute method when all found repositories are filtered out."""
    mock_get_repos.return_value = ["/path1"]
    mock_analyze.return_value = ["raw_status"]
    mock_filter.return_value = []

    service = ScanService(ScanOptions(**base_scan_kwargs))
    service.execute()

    mock_display.assert_not_called()
    mock_print.assert_any_call(
        "\n[bold yellow]No repositories matched your filters.[/bold yellow]"
    )


@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock_run:
        yield mock_run


def test_analyze_single_repo_synced(
    tmp_path: Path, base_scan_kwargs, mock_subprocess_run
):
    service = ScanService(ScanOptions(**base_scan_kwargs))

    def side_effect(cmd, **kwargs):
        res = MagicMock()
        res.returncode = 0
        if "branch" in cmd:
            res.stdout = "main\n"
        elif "status" in cmd:
            res.stdout = ""
        elif "remote" in cmd:
            res.stdout = "origin\n"
        elif "rev-parse" in cmd:
            res.stdout = "origin/main\n"
        elif "rev-list" in cmd:
            res.stdout = "0 0\n"
        return res

    mock_subprocess_run.side_effect = side_effect
    status = service._analyze_single_repo(tmp_path)
    assert status.status == "Clean | Synced"


def test_analyze_single_repo_ahead(
    tmp_path: Path, base_scan_kwargs, mock_subprocess_run
):
    service = ScanService(ScanOptions(**base_scan_kwargs))

    def side_effect(cmd, **kwargs):
        res = MagicMock()
        res.returncode = 0
        if "branch" in cmd:
            res.stdout = "main\n"
        elif "status" in cmd:
            res.stdout = ""
        elif "remote" in cmd:
            res.stdout = "origin\n"
        elif "rev-parse" in cmd:
            res.stdout = "origin/main\n"
        elif "rev-list" in cmd:
            res.stdout = "2 0\n"  # Ahead 2
        return res

    mock_subprocess_run.side_effect = side_effect
    status = service._analyze_single_repo(tmp_path)
    assert status.status == "Clean | Ahead (2)"


def test_analyze_single_repo_behind(
    tmp_path: Path, base_scan_kwargs, mock_subprocess_run
):
    service = ScanService(ScanOptions(**base_scan_kwargs))

    def side_effect(cmd, **kwargs):
        res = MagicMock()
        res.returncode = 0
        if "branch" in cmd:
            res.stdout = "main\n"
        elif "status" in cmd:
            res.stdout = ""
        elif "remote" in cmd:
            res.stdout = "origin\n"
        elif "rev-parse" in cmd:
            res.stdout = "origin/main\n"
        elif "rev-list" in cmd:
            res.stdout = "0 3\n"  # Behind 3
        return res

    mock_subprocess_run.side_effect = side_effect
    status = service._analyze_single_repo(tmp_path)
    assert status.status == "Clean | Behind (3)"


def test_analyze_single_repo_no_origin(
    tmp_path: Path, base_scan_kwargs, mock_subprocess_run
):
    service = ScanService(ScanOptions(**base_scan_kwargs))

    def side_effect(cmd, **kwargs):
        res = MagicMock()
        res.returncode = 0
        if "branch" in cmd:
            res.stdout = "main\n"
        elif "status" in cmd:
            res.stdout = ""
        elif "remote" in cmd:
            res.stdout = ""  # No remote
        return res

    mock_subprocess_run.side_effect = side_effect
    status = service._analyze_single_repo(tmp_path)
    assert status.status == "Clean | No Remote"


def test_analyze_single_repo_with_security_scanner_safe(
    tmp_path: Path, base_scan_kwargs, mock_subprocess_run
):
    """Test _analyze_single_repo with a security scanner that returns safe."""
    service = ScanService(ScanOptions(**base_scan_kwargs))

    def side_effect(cmd, **kwargs):
        res = MagicMock()
        res.returncode = 0
        if "branch" in cmd:
            res.stdout = "main\n"
        elif "status" in cmd:
            res.stdout = ""
        elif "remote" in cmd:
            res.stdout = "origin\n"
        elif "rev-parse" in cmd:
            res.stdout = "origin/main\n"
        elif "rev-list" in cmd:
            res.stdout = "0 0\n"
        return res

    mock_subprocess_run.side_effect = side_effect

    def fake_scanner(path):
        return GuardScanResult(is_safe=True, sensitive_files=[])

    status = service._analyze_single_repo(tmp_path, security_scanner=fake_scanner)
    assert status.security_status == "Safe"


def test_analyze_single_repo_with_security_scanner_unsafe(
    tmp_path: Path, base_scan_kwargs, mock_subprocess_run
):
    """Test _analyze_single_repo with a security scanner that detects threats."""
    service = ScanService(ScanOptions(**base_scan_kwargs))

    def side_effect(cmd, **kwargs):
        res = MagicMock()
        res.returncode = 0
        if "branch" in cmd:
            res.stdout = "main\n"
        elif "status" in cmd:
            res.stdout = ""
        elif "remote" in cmd:
            res.stdout = "origin\n"
        elif "rev-parse" in cmd:
            res.stdout = "origin/main\n"
        elif "rev-list" in cmd:
            res.stdout = "0 0\n"
        return res

    mock_subprocess_run.side_effect = side_effect

    def fake_scanner(path):
        return GuardScanResult(is_safe=False, sensitive_files=[".env", "key.pem"])

    status = service._analyze_single_repo(tmp_path, security_scanner=fake_scanner)
    assert status.security_status == "Sensitive: .env, key.pem"


def test_analyze_single_repo_with_security_scanner_error(
    tmp_path: Path, base_scan_kwargs, mock_subprocess_run
):
    """Test _analyze_single_repo handles a failing security scanner gracefully."""
    service = ScanService(ScanOptions(**base_scan_kwargs))

    def side_effect(cmd, **kwargs):
        res = MagicMock()
        res.returncode = 0
        if "branch" in cmd:
            res.stdout = "main\n"
        elif "status" in cmd:
            res.stdout = ""
        elif "remote" in cmd:
            res.stdout = "origin\n"
        elif "rev-parse" in cmd:
            res.stdout = "origin/main\n"
        elif "rev-list" in cmd:
            res.stdout = "0 0\n"
        return res

    mock_subprocess_run.side_effect = side_effect

    def fake_scanner(path):
        raise RuntimeError("oops")

    status = service._analyze_single_repo(tmp_path, security_scanner=fake_scanner)
    assert status.security_status == "Scan Failed"
