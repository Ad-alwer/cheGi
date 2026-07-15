"""Console output and TerminalUI with theme support."""

from typing import Optional

from rich.console import Console

from .models import MessageType
from .themes import ChegiTheme, get_theme

console = Console()


class TerminalUI:
    """Handles basic terminal message printing and output formatting.

    Uses the active cheGi theme for message colors.
    """

    _current_theme: Optional[ChegiTheme] = None

    @classmethod
    def _load_theme(cls) -> ChegiTheme:
        """Loads the active theme from global config, caching it.

        Returns:
            The active ChegiTheme.
        """
        if cls._current_theme is None:
            from chegi.config import GlobalConfig

            name = GlobalConfig().theme
            cls._current_theme = get_theme(name)
        return cls._current_theme

    @classmethod
    def apply_theme(cls, theme: ChegiTheme) -> None:
        """Applies a theme for the current session.

        Args:
            theme: The ChegiTheme to use.
        """
        cls._current_theme = theme

    @classmethod
    def _get_style(cls, msg_type: MessageType) -> str:
        """Resolves the Rich style string for a message type from the active theme.

        Args:
            msg_type: The message type enum.

        Returns:
            Rich style string.
        """
        theme = cls._load_theme()
        attr = msg_type.name.lower()
        return str(getattr(theme, attr, theme.neutral))

    @classmethod
    def get_active_theme(cls) -> ChegiTheme:
        """Returns the currently active theme.

        Returns:
            The active ChegiTheme.
        """
        return cls._load_theme()

    @classmethod
    def print_message(
        cls, text: str, msg_type: MessageType = MessageType.NEUTRAL
    ) -> None:
        """Prints a formatted message to the terminal using Rich.

        Args:
            text: The message string to print.
            msg_type: The type of message determining color and style.
        """
        style = cls._get_style(msg_type)
        console.print(f"[{style}]{text}[/]")

    @classmethod
    def print_success(cls, text: str) -> None:
        """Prints a success message with a checkmark.

        Args:
            text: The success message to print.
        """
        cls.print_message(f"✔ {text}", MessageType.SUCCESS)

    @classmethod
    def print_error(cls, text: str) -> None:
        """Prints an error message with a cross mark.

        Args:
            text: The error message to print.
        """
        cls.print_message(f"✖ {text}", MessageType.ERROR)

    @classmethod
    def print_warning(cls, text: str) -> None:
        """Prints a warning message with a warning sign.

        Args:
            text: The warning message to print.
        """
        cls.print_message(f"⚠ {text}", MessageType.WARNING)

    @classmethod
    def print_info(cls, text: str) -> None:
        """Prints an informational message with an info sign.

        Args:
            text: The info message to print.
        """
        cls.print_message(f"ℹ {text}", MessageType.INFO)
