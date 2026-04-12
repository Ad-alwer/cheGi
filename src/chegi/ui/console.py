from rich.console import Console

from .models import MessageType

console = Console()


class TerminalUI:
    """Handles basic terminal message printing and output formatting."""

    @staticmethod
    def print_message(text: str, msg_type: MessageType = MessageType.NEUTRAL) -> None:
        """Prints a formatted message to the terminal using Rich.

        Args:
            text (str): The message string to print.
            msg_type (MessageType, optional): The type of message determining 
                color and style. Defaults to MessageType.NEUTRAL.
        """
        # Rich tags can be compound (e.g., 'bold red'). 
        # We extract the last word to properly close the tag (e.g., '[/red]').
        closing_tag = msg_type.value.split()[-1]
        console.print(f"[{msg_type.value}]{text}[/{closing_tag}]")

    @staticmethod
    def print_success(text: str) -> None:
        """Prints a success message with a checkmark.

        Args:
            text (str): The success message to print.
        """
        TerminalUI.print_message(f"✔ {text}", MessageType.SUCCESS)

    @staticmethod
    def print_error(text: str) -> None:
        """Prints an error message with a cross mark.

        Args:
            text (str): The error message to print.
        """
        TerminalUI.print_message(f"✖ {text}", MessageType.ERROR)

    @staticmethod
    def print_warning(text: str) -> None:
        """Prints a warning message with a warning sign.

        Args:
            text (str): The warning message to print.
        """
        TerminalUI.print_message(f"⚠ {text}", MessageType.WARNING)

    @staticmethod
    def print_info(text: str) -> None:
        """Prints an informational message with an info sign.

        Args:
            text (str): The info message to print.
        """
        TerminalUI.print_message(f"ℹ {text}", MessageType.INFO)
