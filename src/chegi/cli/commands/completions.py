"""CLI command for chegi completions — shell completion scripts."""

from typing import Optional

import questionary
import typer
from rich.text import Text
from typing_extensions import Annotated

from chegi.services.completions.completions_service import CompletionsService
from chegi.services.completions.constants import INSTALL_PATHS
from chegi.services.completions.exceptions import (
    InstallationError,
    UnsupportedShellError,
)
from chegi.ui import TerminalUI, console

app = typer.Typer(
    help="Generate shell completion scripts for bash, zsh, fish, and powershell.",
)


@app.callback(invoke_without_command=True)
def completions(
    shell: Annotated[
        Optional[str],
        typer.Argument(
            help="Target shell: bash, zsh, fish, powershell, or pwsh",
        ),
    ] = None,
    install: Annotated[
        bool,
        typer.Option(
            "--install",
            "-i",
            help="Auto-detect and install completion script (no prompts)",
        ),
    ] = False,
) -> None:
    """Print a shell completion script to stdout, or run interactive install."""
    service = CompletionsService()

    if shell and install:
        _do_install(service, shell)
    elif install:
        _auto_install(service)
    elif shell:
        _print_script(service, shell)
    else:
        _interactive_install(service)


def _auto_install(service: CompletionsService) -> None:
    """Detects shell and installs without interactive prompts.

    Args:
        service: The completions service.
    """
    detected = service.detect_shell()
    if not detected:
        TerminalUI.print_error(
            "Could not detect your shell. "
            "Use 'chegi completions --install bash' to specify one."
        )
        raise typer.Exit(code=1)

    _do_install(service, detected)


def _print_script(service: CompletionsService, shell: str) -> None:
    """Prints a completion script to stdout.

    Args:
        service: The completions service.
        shell: The target shell name.
    """
    try:
        script = service.generate(shell)
    except UnsupportedShellError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    typer.echo(script, nl=False)


def _interactive_install(service: CompletionsService) -> None:
    """Runs the interactive Q&A flow for detecting and installing completions.

    Args:
        service: The completions service.
    """
    detected = service.detect_shell()

    if detected and detected in INSTALL_PATHS:
        msg = Text.assemble(
            ("\U0001f426 ", "bold gold1"),
            ("I see you're using ", ""),
            (detected, "bold cyan"),
            (". Want me to set up tab completion?", ""),
        )
        console.print(msg)
    elif detected:
        console.print(
            f"\U0001f426 [bold gold1]I see you're using [bold cyan]{detected}[/]. "
            f"Auto-install isn't available for [bold]{detected}[/], "
            f"but I can print the script for you."
        )
    else:
        console.print(
            "\U0001f426 [bold gold1]Couldn't detect your shell. "
            "I can still print a script — just tell me which one."
        )

    choices = []
    if detected and detected in INSTALL_PATHS:
        choices.append(
            questionary.Choice(
                title=f"Install for {detected}",
                value="install",
                description=f"Write completion script to {INSTALL_PATHS[detected]}",
            )
        )
    choices.append(
        questionary.Choice(
            title="Show completion script",
            value="show",
            description="Print to stdout (pipe it yourself)",
        )
    )
    choices.append(
        questionary.Choice(
            title="Cancel",
            value="cancel",
        )
    )

    action = questionary.select(
        "What would you like to do?",
        choices=choices,
    ).ask()

    if action is None or action == "cancel":
        console.print("[dim]OK, maybe next time![/dim]")
        raise typer.Exit()

    if action == "install":
        _do_install(service, detected)
    else:
        _pick_and_print(service, detected)


def _do_install(service: CompletionsService, shell: str) -> None:
    """Installs the completion script for the detected shell.

    Args:
        service: The completions service.
        shell: The shell name.
    """
    try:
        path = service.install(shell)
    except (UnsupportedShellError, InstallationError) as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    console.print(
        f"\n[bold green]\u2713[/] Completion script installed to [bold]{path}[/]"
    )

    source_hint = {
        "bash": "source ~/.bashrc",
        "zsh": "source ~/.zshrc",
        "fish": "exec fish",
    }.get(shell, f"source {path}")

    console.print(f"[dim]Restart your terminal or run: [bold]{source_hint}[/][/dim]")


def _pick_and_print(service: CompletionsService, detected: Optional[str]) -> None:
    """Lets the user pick a shell and prints the completion script.

    Args:
        service: The completions service.
        detected: The detected shell name, if any.
    """
    shell_choices = [
        questionary.Choice(title="Bash", value="bash"),
        questionary.Choice(title="Zsh", value="zsh"),
        questionary.Choice(title="Fish", value="fish"),
        questionary.Choice(title="PowerShell", value="powershell"),
        questionary.Choice(title="PowerShell Core (pwsh)", value="pwsh"),
    ]

    chosen = questionary.select(
        "Which shell?",
        choices=shell_choices,
        default=detected if detected else None,
    ).ask()

    if chosen is None:
        raise typer.Exit()

    _print_script(service, chosen)
