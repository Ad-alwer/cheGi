from abc import ABC, abstractmethod


class PreflightCheck(ABC):
    """Abstract base class for all preflight system checks.

    This class enforces a standard interface for any check that needs to be
    executed before the main CLI application runs. All subclasses must
    implement the `execute` method.
    """

    @abstractmethod
    def execute(self) -> None:
        """Executes the specific preflight check logic.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        pass
