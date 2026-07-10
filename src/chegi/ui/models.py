from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    """
    Enumeration of message types with their corresponding Rich text styles.
    """

    SUCCESS = "bold green"
    ERROR = "bold red"
    WARNING = "bold yellow"
    INFO = "bold blue"
    NEUTRAL = "white"


@dataclass
class TableTheme:
    """
    Configuration model for table styling in the terminal UI.

    Attributes:
        header_style (str): The Rich style string for the table header.
        border_style (str): The Rich style string for the table borders.
        show_lines (bool): Whether to draw lines between rows.
    """

    header_style: str = "bold cyan"
    border_style: str = "blue"
    show_lines: bool = True
