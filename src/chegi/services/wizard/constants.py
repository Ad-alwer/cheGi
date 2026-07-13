"""Constants for the first-run wizard."""

from pathlib import Path

WIZARD_MARKER_DIR = Path.home() / ".config" / "chegi"
WIZARD_MARKER_FILE = WIZARD_MARKER_DIR / "wizard_done"

BANNER = """\
[bold yellow]     ___  ___ ___ ___ ___ [/bold yellow]
[bold yellow]    / __|/ __|_ _| __|_ _|[/bold yellow]  [cyan]🐆 cheGi[/cyan] — [italic]The ultimate Git companion[/italic]
[bold yellow]   | (__| (__ | || _| | | [/bold yellow]  [dim]Type less, do more.[/dim]
[bold yellow]    \___|\___|___|_| |___|[/bold yellow]
"""

WELCOME_MESSAGE = (
    "[bold cyan]Welcome to cheGi![/bold cyan] "
    "Let's get you set up in a few quick steps."
)
