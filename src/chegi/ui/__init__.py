"""
UI Module for cheGi.
Handles all terminal presentation, styling, and complex component rendering (e.g., tables).
"""

from .console import console, TerminalUI
from .tables import display_results_table
from .models import MessageType, TableTheme
from .exceptions import UIError, TableRenderingError, ThemeConfigurationError

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
