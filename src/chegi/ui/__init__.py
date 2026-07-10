"""
UI Module for cheGi.
Handles all terminal presentation, styling, and complex component rendering (e.g., tables).
"""

from .console import TerminalUI, console
from .exceptions import TableRenderingError, ThemeConfigurationError, UIError
from .models import MessageType, TableTheme
from .tables import display_results_table

__all__ = [
    "console",
    "TerminalUI",
    "display_results_table",
    "MessageType",
    "TableTheme",
    "UIError",
    "TableRenderingError",
    "ThemeConfigurationError",
]
