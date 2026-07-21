"""CLI command for chegi commit — secure Git commits."""

from pathlib import Path
from typing import Dict, Optional

import questionary
import typer
from rich.panel import Panel
from rich.text import Text
from typing_extensions import Annotated

from chegi.services.commit import (
    CommitContext,
    CommitService,
    CommitStyle,
    CommitStyleManager,
    NoStagedFilesError,
)
from chegi.services.git.client import GitClient
from chegi.ui.console import TerminalUI, console

app = typer.Typer(help="Record changes to the repository with security checks.")


@app.callback(invoke_without_command=True)
def commit(
    message: Annotated[
        Optional[str],
        typer.Option("--message", "-m", help="The commit message"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Commit even if sensitive files are detected in staging",
        ),
    ] = False,
    chegi_header: Annotated[
        bool,
        typer.Option(
            "--ch",
            "--chegi-header",
            help="Add the cheGi brand signature (🐆) to the subject line",
        ),
    ] = False,
) -> None:
    """Record changes to the repository with built-in security checks.

    Automatically scans staged files for sensitive data before committing.
    In interactive mode (no -m), guides you step-by-step through choosing
    a commit style, filling in fields, and previewing the result.
    """
    repo_path = Path.cwd()
    git_client = GitClient(repo_path)

    if not git_client.is_valid_repo():
        TerminalUI.print_error(
            "fatal: not a git repository (or any of the parent directories): .git"
        )
        raise typer.Exit(code=1)

    service = CommitService(repo_path)
    style_manager = CommitStyleManager(repo_path)

    try:
        context = service.prepare_context()
    except NoStagedFilesError:
        TerminalUI.print_error(
            "No staged files found. Use 'git add' to stage files first."
        )
        raise typer.Exit(code=1)

    if not context.is_safe and not force:
        _handle_sensitive_files(service, context)
        if not context.is_safe:
            raise typer.Exit(code=1)

    _show_styled_diff(context)

    if message:
        final_message = message
    else:
        final_message = _guided_commit_flow(service, style_manager, context)

    if not final_message or not final_message.strip():
        TerminalUI.print_error("Commit message cannot be empty.")
        raise typer.Exit(code=1)

    final_message = final_message.strip()

    if chegi_header:
        final_message = CommitService.apply_brand_suffix(final_message)

    try:
        output = service.execute_commit(final_message)
        console.print("[bold green]✔ Commit successful![/bold green]")
        for line in output.split("\n"):
            if line.strip():
                console.print(f"  [dim]{line.strip()}[/dim]")
    except Exception as exc:
        TerminalUI.print_error(f"Commit failed: {exc}")
        raise typer.Exit(code=1)


def _show_styled_diff(context: "CommitContext") -> None:
    """Displays the diff stat with styled file names.

    Shows file paths in the brand color (bold) without boxes.

    Args:
        context (CommitContext): The commit context with diff data.
    """
    console.print()
    console.print("[bold cyan]📊 Staged Changes:[/bold cyan]")
    if context.diff_stat:
        lines = context.diff_stat.strip().split("\n")
        for raw_line in lines:
            if not raw_line.strip():
                continue
            styled = Text()
            parts = raw_line.split("|", 1)
            if len(parts) == 2:
                file_part = parts[0].rstrip()
                rest = "|" + parts[1]
                styled.append(file_part, style="bold #d86c1f")
                styled.append(rest, style="")
            else:
                styled.append(raw_line)
            console.print(styled)


def _guided_commit_flow(
    service: CommitService,
    style_manager: CommitStyleManager,
    context: "CommitContext",
) -> Optional[str]:
    """Runs the interactive questionary commit flow.

    Guides the user through style selection, field input, preview,
    and confirmation.

    Args:
        service (CommitService): The commit service instance.
        style_manager (CommitStyleManager): The style manager instance.
        context (CommitContext): The current commit context.

    Returns:
        Optional[str]: The final commit message, or None if aborted.
    """
    styles = style_manager.get_styles()
    last_style_name = style_manager.get_last_style()

    style = _pick_style(styles, last_style_name)
    if style is None:
        TerminalUI.print_info("Commit aborted.")
        raise typer.Exit(code=1)

    style_manager.save_last_style(style.name)

    values = _fill_style_fields(style, context)
    if values is None:
        TerminalUI.print_info("Commit aborted.")
        raise typer.Exit(code=1)

    message = CommitService.build_message(style, values)

    console.print()
    preview_panel = Panel(
        message,
        title="[bold cyan]Commit Preview[/bold cyan]",
        border_style="#d86c1f",
        padding=(1, 2),
    )
    console.print(preview_panel)

    confirmed = questionary.confirm("Commit with this message?").ask()
    if not confirmed:
        TerminalUI.print_info("Commit aborted.")
        raise typer.Exit(code=1)

    is_single_line = "\n" not in message.strip()
    if is_single_line and style_manager.should_show_hint("commit_brand"):
        _show_brand_hint()
        style_manager.mark_hint_shown("commit_brand")

    return message


def _pick_style(styles, last_style_name: Optional[str]) -> Optional["CommitStyle"]:
    """Prompts the user to pick a commit style.

    Args:
        styles: List of available CommitStyle objects.
        last_style_name: The user's previously used style name.

    Returns:
        Optional[CommitStyle]: The selected style, or None if aborted.
    """
    choices = []
    default_index = 0
    for i, style in enumerate(styles):
        label = f"{style.label} — {style.description}"
        choices.append(questionary.Choice(title=label, value=style))
        if style.name == last_style_name:
            default_index = i

    chosen = questionary.select(
        "Select commit style:",
        choices=choices,
        default=choices[default_index] if choices else None,
    ).ask()

    return chosen


def _fill_style_fields(
    style: "CommitStyle", context: "CommitContext"
) -> Optional[Dict[str, str]]:
    """Prompts the user to fill in fields for the chosen style.

    Args:
        style (CommitStyle): The selected commit style.
        context (CommitContext): The commit context for suggestions.

    Returns:
        Optional[Dict[str, str]]: Field values, or None if aborted.
    """
    values: Dict[str, str] = {}

    if "scope" in style.fields and context.suggested_messages:
        suggested_scope = ""
        first = context.suggested_messages[0]
        if "(" in first and ")" in first:
            suggested_scope = first.split("(")[1].split(")")[0]

        scope_val = questionary.text("Scope:", default=suggested_scope).ask()
        if scope_val is None:
            return None
        values["scope"] = scope_val.strip()

    if "emoji" in style.fields and style.emojis:
        type_val = _pick_type(style.types)
        if type_val is None:
            return None
        values["type"] = type_val

        emoji = style.emojis.get(type_val, "")
        console.print(f"  Selected: [bold]{emoji} {type_val}[/bold]")
        values["emoji"] = emoji
    elif "type" in style.fields:
        if style.types:
            type_val = _pick_type(style.types)
            if type_val is None:
                return None
            values["type"] = type_val
        else:
            type_val = questionary.text("Type:").ask()
            if type_val is None:
                return None
            values["type"] = type_val.strip()

    if "description" in style.fields:
        suggested_desc = ""
        if context.suggested_messages:
            msg = context.suggested_messages[0]
            if ":" in msg:
                suggested_desc = msg.split(":", 1)[1].strip()

        desc_val = questionary.text("Description:", default=suggested_desc).ask()
        if desc_val is None:
            return None
        values["description"] = desc_val.strip()

    if "body" in style.fields:
        body_lines: list = []
        console.print("[dim]Enter body lines (empty line to finish):[/dim]")
        while True:
            line = questionary.text("  •").ask()
            if line is None:
                return None
            line = line.strip()
            if not line:
                break
            if not line.startswith("- "):
                line = "- " + line
            body_lines.append(line)

        if body_lines:
            values["body"] = "\n".join(body_lines)
        else:
            values["body"] = ""

    return values


def _pick_type(types) -> Optional[str]:
    """Prompts the user to pick a commit type.

    Args:
        types: List of available type strings.

    Returns:
        Optional[str]: The selected type, or None if aborted.
    """
    type_choices = [questionary.Choice(title=f"{t}", value=t) for t in types]
    chosen = questionary.select("Select type:", choices=type_choices).ask()
    return chosen


def _handle_sensitive_files(service: CommitService, context: "CommitContext") -> None:
    """Handles the case where sensitive files are detected in staging.

    Presents interactive options to the user: unstage, force, or abort.

    Args:
        service (CommitService): The commit service instance.
        context (CommitContext): The current commit context.
    """
    console.print()
    TerminalUI.print_warning("Sensitive files detected in staging area!")
    for f in context.sensitive_files:
        console.print(f"  [bold yellow]• {f}[/bold yellow]")

    console.print()
    choice = questionary.select(
        "What would you like to do?",
        choices=[
            questionary.Choice(
                "Unstage sensitive files and continue",
                value="unstage",
            ),
            questionary.Choice(
                "Force commit anyway (not recommended)",
                value="force",
            ),
            questionary.Choice("Abort commit", value="abort"),
        ],
    ).ask()

    if choice == "abort" or choice is None:
        TerminalUI.print_info("Commit aborted.")
        raise typer.Exit(code=1)

    if choice == "force":
        console.print(
            "[bold yellow]⚠ Forcing commit with sensitive files.[/bold yellow]"
        )
        context.is_safe = True
        return

    if choice == "unstage":
        success = service.unstage_files(context.sensitive_files)
        if success:
            console.print(
                "[bold green]✔ Sensitive files unstaged successfully.[/bold green]"
            )
            context.staged_files = [
                f for f in context.staged_files if f not in context.sensitive_files
            ]
            context.sensitive_files = []
            context.is_safe = True
            if not context.staged_files:
                TerminalUI.print_error(
                    "No files remaining to commit after unstaging sensitive files."
                )
                raise typer.Exit(code=1)
        else:
            TerminalUI.print_error("Failed to unstage sensitive files.")
            raise typer.Exit(code=1)


def _show_brand_hint() -> None:
    """Shows a one-time hint about the --ch brand flag."""
    console.print()
    hint_panel = Panel(
        "[bold #d86c1f]🐆 Tip:[/bold #d86c1f] Want the cheetah to stamp "
        "your commits?\n"
        "Use [bold]chegi commit --ch[/bold] to add the cheGi brand "
        "signature.\n"
        "It makes your commits recognizable and helps cheGi grow!",
        border_style="#d86c1f",
        padding=(1, 2),
    )
    console.print(hint_panel)
