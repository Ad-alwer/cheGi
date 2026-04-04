from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from chegi.services.scanner.scan_service import ScanService


@pytest.fixture
def base_scan_kwargs():
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
    kwargs = {**base_scan_kwargs, "max_depth": 5}
    service = ScanService(**kwargs)
    
    assert service.config.max_depth == 5
    mock_config_cls.return_value.load.assert_called_once()


@patch("chegi.services.scanner.scan_service.find_git_repos")
def test_get_repositories_success(mock_find, base_scan_kwargs):
    mock_find.return_value = [Path("/mock/repo1"), Path("/mock/repo2")]
    service = ScanService(**base_scan_kwargs)
    
    repos = service._get_repositories()
    assert repos == ["/mock/repo1", "/mock/repo2"]


@patch("chegi.services.scanner.scan_service.find_git_repos")
@patch("chegi.services.scanner.scan_service.TerminalUI")
def test_get_repositories_not_a_dir(mock_ui, mock_find, base_scan_kwargs):
    mock_find.side_effect = NotADirectoryError("Invalid path")
    service = ScanService(**base_scan_kwargs)
    
    with pytest.raises(typer.Exit) as exc_info:
        service._get_repositories()
    
    assert exc_info.value.exit_code == 1
    service.ui.print_error.assert_called_once_with("Invalid path")


def test_filter_results(base_scan_kwargs):
    dirty_repo = MagicMock(is_dirty=True, has_staged_files=False)
    staged_repo = MagicMock(is_dirty=True, has_staged_files=True)
    clean_repo = MagicMock(is_dirty=False, has_staged_files=False)
    
    statuses = [dirty_repo, staged_repo, clean_repo]
    
    # Test dirty filter
    kwargs_dirty = {**base_scan_kwargs, "dirty": True}
    service_dirty = ScanService(**kwargs_dirty)
    filtered = service_dirty._filter_results(statuses)
    assert len(filtered) == 2
    assert clean_repo not in filtered

    # Test staged filter
    kwargs_staged = {**base_scan_kwargs, "staged": True}
    service_staged = ScanService(**kwargs_staged)
    filtered = service_staged._filter_results(statuses)
    assert len(filtered) == 1
    assert staged_repo in filtered


@patch("chegi.services.scanner.scan_service.GitAnalyzer")
@patch("chegi.services.scanner.scan_service.Progress")
def test_analyze_repositories(mock_progress, mock_analyzer_cls, base_scan_kwargs):
    mock_analyzer = mock_analyzer_cls.return_value
    mock_analyzer.analyze_concurrently.return_value = ["status1", "status2"]
    
    service = ScanService(**base_scan_kwargs)
    statuses = service._analyze_repositories(["/path1", "/path2"])
    
    assert statuses == ["status1", "status2"]
    mock_analyzer.analyze_concurrently.assert_called_once_with(
        ["/path1", "/path2"], security_scanner=None
    )


@patch.object(ScanService, "_get_repositories")
@patch("chegi.services.scanner.scan_service.TerminalUI")
def test_execute_no_repos(mock_ui, mock_get_repos, base_scan_kwargs):
    mock_get_repos.return_value = []
    service = ScanService(**base_scan_kwargs)
    service.execute()
    
    service.ui.display_results_table.assert_called_once_with([])


@patch.object(ScanService, "_get_repositories")
@patch.object(ScanService, "_analyze_repositories")
@patch.object(ScanService, "_filter_results")
@patch("chegi.services.scanner.scan_service.TerminalUI")
def test_execute_full_flow(
    mock_ui, mock_filter, mock_analyze, mock_get_repos, base_scan_kwargs
):
    mock_get_repos.return_value = ["/path1"]
    mock_analyze.return_value = ["raw_status"]
    mock_filter.return_value = ["filtered_status"]
    
    service = ScanService(**base_scan_kwargs)
    service.execute()
    
    mock_get_repos.assert_called_once()
    mock_analyze.assert_called_once_with(["/path1"])
    mock_filter.assert_called_once_with(["raw_status"])
    service.ui.display_results_table.assert_called_once_with(["filtered_status"])


@patch.object(ScanService, "_get_repositories")
@patch.object(ScanService, "_analyze_repositories")
@patch.object(ScanService, "_filter_results")
@patch("chegi.services.scanner.scan_service.TerminalUI")
def test_execute_filtered_out_all(
    mock_ui, mock_filter, mock_analyze, mock_get_repos, base_scan_kwargs
):
    mock_get_repos.return_value = ["/path1"]
    mock_analyze.return_value = ["raw_status"]
    mock_filter.return_value = [] # Everything filtered out
    
    service = ScanService(**base_scan_kwargs)
    service.execute()
    
    service.ui.display_results_table.assert_not_called()
    service.ui.console.print.assert_any_call(
        "\n[bold yellow]No repositories matched your filters.[/bold yellow]"
    )
