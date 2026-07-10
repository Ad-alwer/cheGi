from unittest.mock import MagicMock, patch

from chegi.cli.core.checks import PreflightCheck
from chegi.cli.core.preflight import PreflightOrchestrator, run_preflight_checks


class DummyCheck(PreflightCheck):
    """A concrete mock implementation of PreflightCheck for testing the orchestrator."""

    def __init__(self):
        self.executed = False

    def execute(self):
        self.executed = True


def test_orchestrator_execute_checks():
    """Tests that the orchestrator can execute all registered checks."""
    orchestrator = PreflightOrchestrator()
    dummy_check_1 = DummyCheck()
    dummy_check_2 = DummyCheck()

    # Override the default checks with our dummy checks for isolated testing
    orchestrator.checks = [dummy_check_1, dummy_check_2]

    assert len(orchestrator.checks) == 2

    orchestrator.run_all()

    assert dummy_check_1.executed is True
    assert dummy_check_2.executed is True


@patch("chegi.cli.core.preflight.PreflightOrchestrator")
def test_run_preflight_checks(mock_orchestrator_class: MagicMock):
    """Tests the entry point function to ensure it creates an orchestrator and runs checks."""
    mock_orchestrator = mock_orchestrator_class.return_value

    run_preflight_checks()

    mock_orchestrator.run_all.assert_called_once()
