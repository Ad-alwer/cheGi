from unittest.mock import MagicMock, patch

from chegi.cli.core.preflight import PreflightOrchestrator, run_preflight_checks
from chegi.cli.core.checks import PreflightCheck


class DummyCheck(PreflightCheck):
    """A concrete mock implementation of PreflightCheck for testing the orchestrator."""
    def __init__(self):
        self.executed = False

    def execute(self):
        self.executed = True


def test_orchestrator_add_and_execute_checks():
    """Tests that the orchestrator can register multiple checks and execute them all."""
    orchestrator = PreflightOrchestrator()
    dummy_check_1 = DummyCheck()
    dummy_check_2 = DummyCheck()

    orchestrator.add_check(dummy_check_1)
    orchestrator.add_check(dummy_check_2)

    assert len(orchestrator._checks) == 2

    orchestrator.execute_all()

    assert dummy_check_1.executed is True
    assert dummy_check_2.executed is True


@patch("chegi.cli.core.preflight.PreflightOrchestrator")
def test_run_preflight_checks(mock_orchestrator_class: MagicMock):
    """Tests the entry point function to ensure it creates an orchestrator and runs checks."""
    mock_orchestrator = mock_orchestrator_class.return_value

    run_preflight_checks()

    mock_orchestrator.add_check.assert_called()
    mock_orchestrator.execute_all.assert_called_once()
