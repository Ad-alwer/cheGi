from chegi.cli.core.checks import PreflightCheck
from chegi.cli.core.checks.git_check import GitRequirementCheck


class PreflightOrchestrator:
    """Orchestrates and executes all registered preflight checks.

    Attributes:
        checks (list[PreflightCheck]): A list of instantiated check objects
            that conform to the PreflightCheck interface.
    """

    def __init__(self) -> None:
        """Initializes the orchestrator and registers necessary checks."""
        self.checks: list[PreflightCheck] = [
            GitRequirementCheck(),
        ]

    def run_all(self) -> None:
        """Iterates through all registered checks and executes them sequentially."""
        for check in self.checks:
            check.execute()


def run_preflight_checks() -> None:
    """Entrypoint function to instantiate and run the PreflightOrchestrator."""
    orchestrator = PreflightOrchestrator()
    orchestrator.run_all()
