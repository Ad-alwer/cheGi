"""
UI Module for cheGi.
Handles all terminal presentation, styling, and complex component rendering (e.g., tables).
"""

from .console import TerminalUI, console
from .exceptions import TableRenderingError, ThemeConfigurationError, UIError
from .models import MessageType, TableTheme
from .tables import display_results_table
from .themes import THEMES, ChegiTheme, get_theme, list_themes

__all__ = [
    "console",
    "TerminalUI",
    "display_results_table",
    "MessageType",
    "TableTheme",
    "ChegiTheme",
    "THEMES",
    "get_theme",
    "list_themes",
    "UIError",
    "TableRenderingError",
    "ThemeConfigurationError",
]
