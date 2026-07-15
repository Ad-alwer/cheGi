"""Theme presets for cheGi terminal output."""

from dataclasses import dataclass, field
from typing import Dict

from .models import TableTheme


@dataclass
class ChegiTheme:
    """A complete color theme for cheGi output.

    Attributes:
        name: Internal key name.
        label: Human-readable label for the picker.
        success: Rich style string for success messages.
        error: Rich style string for error messages.
        warning: Rich style string for warning messages.
        info: Rich style string for info messages.
        neutral: Rich style string for neutral messages.
        table: TableTheme for table rendering.
    """

    name: str
    label: str
    success: str = "bold green"
    error: str = "bold red"
    warning: str = "bold yellow"
    info: str = "bold blue"
    neutral: str = "white"
    table: TableTheme = field(default_factory=TableTheme)


THEMES: Dict[str, ChegiTheme] = {
    "default": ChegiTheme(
        name="default",
        label="Default",
        success="bold green",
        error="bold red",
        warning="bold yellow",
        info="bold blue",
        neutral="white",
        table=TableTheme(
            header_style="bold cyan",
            border_style="blue",
            show_lines=True,
        ),
    ),
    "dark": ChegiTheme(
        name="dark",
        label="Dark",
        success="green",
        error="red",
        warning="yellow",
        info="cyan",
        neutral="dim white",
        table=TableTheme(
            header_style="cyan",
            border_style="grey50",
            show_lines=True,
        ),
    ),
    "hacker": ChegiTheme(
        name="hacker",
        label="Hacker",
        success="bold green",
        error="bold red",
        warning="bold yellow",
        info="green",
        neutral="dark_green",
        table=TableTheme(
            header_style="bold green",
            border_style="green",
            show_lines=False,
        ),
    ),
    "solarized": ChegiTheme(
        name="solarized",
        label="Solarized",
        success="#859900",
        error="#dc322f",
        warning="#b58900",
        info="#268bd2",
        neutral="#93a1a1",
        table=TableTheme(
            header_style="bold #268bd2",
            border_style="#657b83",
            show_lines=True,
        ),
    ),
    "nord": ChegiTheme(
        name="nord",
        label="Nord",
        success="#a3be8c",
        error="#bf616a",
        warning="#ebcb8b",
        info="#81a1c1",
        neutral="#d8dee9",
        table=TableTheme(
            header_style="bold #88c0d0",
            border_style="#4c566a",
            show_lines=True,
        ),
    ),
}


def get_theme(name: str) -> ChegiTheme:
    """Returns a theme by name, or the default if not found.

    Args:
        name: Theme key name.

    Returns:
        The matching ChegiTheme, or default.
    """
    return THEMES.get(name, THEMES["default"])


def list_themes() -> Dict[str, str]:
    """Returns a dict of theme key -> label for the picker.

    Returns:
        Dict mapping internal names to display labels.
    """
    return {k: v.label for k, v in THEMES.items()}
