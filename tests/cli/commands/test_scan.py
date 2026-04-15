from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()




@patch("chegi.cli.commands.scan.ScanService")
def test_scan_invalid_path(mock_scan_service_class: MagicMock):
    """Tests the CLI behavior when an invalid directory path is provided."""
    mock_instance = mock_scan_service_class.return_value
    mock_instance.execute.side_effect = ValueError("Directory does not exist")

    result = runner.invoke(app, ["scan", "/non/existent/mock/path/12345"])
    
    assert result.exit_code == 1
    # Check if the error message was outputted or caught correctly
    assert "does not exist" in result.stdout.lower() or isinstance(result.exception, ValueError)


@patch("chegi.cli.commands.scan.ScanService")
def test_scan_with_repos(mock_scan_service_class: MagicMock, tmp_path: Path):
    """Tests successful scan execution and service call."""
    result = runner.invoke(app, ["scan", str(tmp_path)])

    assert result.exit_code == 0
    mock_scan_service_class.assert_called_once()
    mock_instance = mock_scan_service_class.return_value
    mock_instance.execute.assert_called_once()


@patch("chegi.cli.commands.scan.ScanService")
def test_scan_filter_dirty(mock_scan_service_class: MagicMock, tmp_path: Path):
    """Tests the --dirty flag to ensure dirty argument is passed to the service."""
    result = runner.invoke(app, ["scan", "--dirty", str(tmp_path)])

    assert result.exit_code == 0
    mock_scan_service_class.assert_called_once()
    _, kwargs = mock_scan_service_class.call_args
    assert kwargs.get("dirty") is True


@patch("chegi.cli.commands.scan.ScanService")
def test_scan_filter_staged(mock_scan_service_class: MagicMock, tmp_path: Path):
    """Tests the --staged flag to ensure staged argument is passed to the service."""
    result = runner.invoke(app, ["scan", "--staged", str(tmp_path)])

    assert result.exit_code == 0
    mock_scan_service_class.assert_called_once()
    _, kwargs = mock_scan_service_class.call_args
    assert kwargs.get("staged") is True


@patch("chegi.cli.commands.scan.ScanService")
def test_scan_with_security_flag(mock_scan_service_class: MagicMock, tmp_path: Path):
    """Tests if --security flag correctly passes the security argument to the service."""
    result = runner.invoke(app, ["scan", "--security", str(tmp_path)])

    assert result.exit_code == 0
    mock_scan_service_class.assert_called_once()
    _, kwargs = mock_scan_service_class.call_args
    assert kwargs.get("security") is True
