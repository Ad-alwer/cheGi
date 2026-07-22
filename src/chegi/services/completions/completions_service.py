"""Service for generating shell completion scripts."""

from pathlib import Path

from typer._completion_classes import (
    BashComplete,
    FishComplete,
    PowerShellComplete,
    ZshComplete,
)
from typer.main import get_command

from chegi.services.completions.constants import INSTALL_PATHS
from chegi.services.completions.exceptions import (
    InstallationError,
    UnsupportedShellError,
)


class CompletionsService:
    """Generates and installs shell completion scripts for cheGi CLI."""

    _CLASSES = {
        "bash": BashComplete,
        "zsh": ZshComplete,
        "fish": FishComplete,
        "powershell": PowerShellComplete,
        "pwsh": PowerShellComplete,
    }

    @staticmethod
    def detect_shell() -> str | None:
        """Detects the current shell using shellingham, falling back to $SHELL.

        Returns:
            The shell name (e.g. 'bash', 'zsh', 'fish') or None if undetectable.
        """
        try:
            from shellingham import detect_shell

            name, _cmd = detect_shell()
            return name
        except (ImportError, OSError, AttributeError):
            pass

        import os

        shell_path = os.environ.get("SHELL", "")
        if shell_path:
            return Path(shell_path).stem
        return None

    def generate(self, shell: str) -> str:
        """Generates the shell completion script for the given shell.

        Args:
            shell: The shell name (bash, zsh, fish, powershell, pwsh).

        Returns:
            The completion script as a string.

        Raises:
            UnsupportedShellError: If the shell is not supported.
        """
        cls = self._CLASSES.get(shell)
        if cls is None:
            supported = ", ".join(sorted(self._CLASSES))
            raise UnsupportedShellError(
                f"Unsupported shell '{shell}'. Supported shells: {supported}"
            )

        from chegi.cli.main import app

        click_cmd = get_command(app)
        complete_var = "_CHEGI_COMPLETE"
        comp = cls(click_cmd, {}, "chegi", complete_var)
        return comp.source()

    def install(self, shell: str) -> Path:
        """Generates and writes the completion script to the standard path.

        Args:
            shell: The shell name (bash, zsh, fish).

        Returns:
            The path where the script was written.

        Raises:
            UnsupportedShellError: If the shell does not support auto-install.
            InstallationError: If the file cannot be written.
        """
        if shell not in INSTALL_PATHS:
            raise UnsupportedShellError(
                f"Auto-install is not supported for '{shell}'. "
                f"Use 'chegi completions {shell} > file' to save manually."
            )

        path = INSTALL_PATHS[shell]
        script = self.generate(shell)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(script)
        except OSError as e:
            raise InstallationError(f"Could not write completion script to {path}: {e}")

        return path
