"""CLI commands for reading and modifying Git global config."""

from __future__ import annotations

from typing import List, Optional

import typer
from rich.table import Table

from chegi.services.git_config import (
    CATEGORY_ICONS,
    CATEGORY_LABELS,
    ConfigChange,
    GitConfigCategory,
    GitConfigService,
    categorize_key,
)
from chegi.ui import TerminalUI, console

app = typer.Typer(
    help="View and modify Git global configuration (user.name, init.defaultBranch, etc.)."
)

# ── Steps for the interactive set wizard ───────────────────┐

WIZARD_STEPS: List[dict] = [
    {
        "key": "user.name",
        "label": "User Name",
        "prompt": "Enter your name",
        "default": "",
    },
    {
        "key": "user.email",
        "label": "User Email",
        "prompt": "Enter your email",
        "default": "",
    },
    {
        "key": "init.defaultBranch",
        "label": "Default Branch",
        "prompt": "Default branch name",
        "default": "main",
    },
    {
        "key": "core.editor",
        "label": "Core Editor",
        "prompt": "Editor command",
        "default": "code --wait",
    },
    {
        "key": "pull.rebase",
        "label": "Pull Rebase",
        "prompt": "Enable pull.rebase?",
        "default": "true",
        "yesno": True,
    },
    {
        "key": "fetch.prune",
        "label": "Fetch Prune",
        "prompt": "Enable fetch.prune?",
        "default": "true",
        "yesno": True,
    },
]


# ── Interactive set wizard ─────────────────────────────────


def _run_set_wizard() -> None:
    """Runs the interactive git config set wizard."""
    changes: List[ConfigChange] = []

    console.print()
    console.print("[bold gold1]🐆 cheGi Git Config — Interactive Setup[/bold gold1]")
    console.print()

    total = len(WIZARD_STEPS)
    for idx, step in enumerate(WIZARD_STEPS, 1):
        key = step["key"]
        current = GitConfigService.get(key)
        pretty_key = step["label"]
        default = step.get("default", "")

        console.print(
            f"  [bold]Step [cyan]{idx}[/cyan]/[cyan]{total}[/cyan] — "
            f"{pretty_key}[/bold]"
        )
        if current:
            console.print(f"    Current: [green]{current}[/green]")
        else:
            console.print("    Current: [dim](not set)[/dim]")

        if step.get("yesno"):
            val = typer.confirm(
                f"  ? {step['prompt']}?", default=(current or default).lower() == "true"
            )
            new_value = "true" if val else ("false" if current is not None else None)
            if new_value is None:
                continue
        else:
            display_default = current or default
            prompt_text = f"  ? {step['prompt']}"
            if display_default:
                prompt_text += f" [[{display_default}]]: "
            else:
                prompt_text += ": "
            raw = input(prompt_text).strip()
            new_value = raw if raw else (current or default or None)
            if new_value is None:
                continue

        if new_value == current:
            console.print("    [dim](unchanged)[/dim]")
            console.print()
            continue

        GitConfigService.set(key, new_value)
        changes.append(ConfigChange(key=key, old_value=current, new_value=new_value))
        console.print(f"    [green]✔ Set to: {new_value}[/green]")
        console.print()

    if not changes:
        console.print("[yellow]No changes made.[/yellow]")
        return

    # ── Review + Revert ──
    _show_review_and_revert(changes)


def _show_review_and_revert(changes: List[ConfigChange]) -> None:
    """Shows the changes summary and offers revert + confirm."""
    while True:
        _print_changes_table(changes)

        # Revert selection
        console.print()
        console.print("[bold]Select changes to REVERT:[/bold]")
        console.print(
            "[dim](Space to toggle, Enter when done, leave empty to keep all)[/dim]"
        )

        choices = [(c.key, c.was_set) for c in changes]
        selected = _checkbox_select(choices)

        if selected:
            for s in selected:
                match = next((c for c in changes if c.key == s), None)
                if match:
                    if match.old_value is not None:
                        GitConfigService.set(match.key, match.old_value)
                    else:
                        GitConfigService.unset(match.key)
                    changes.remove(match)
                    console.print(
                        f"  [yellow]↩ Reverted:[/yellow] [bold]{match.key}[/bold]"
                    )
        else:
            console.print("  [dim]No changes reverted.[/dim]")

        console.print()
        action = _choose_action()
        if action == "confirm":
            _print_changes_table(changes)
            console.print()
            TerminalUI.print_success("Git configuration saved.")
            console.print()
            return
        elif action == "start_over":
            # Revert all
            for c in changes:
                if c.old_value is not None:
                    GitConfigService.set(c.key, c.old_value)
                else:
                    GitConfigService.unset(c.key)
            changes.clear()
            console.print()
            _run_set_wizard()
            return


def _print_changes_table(changes: List[ConfigChange]) -> None:
    """Prints a Rich table of applied changes."""
    table = Table(
        title="📋 Changes Applied",
        title_style="bold gold1",
        border_style="gold1",
        header_style="bold",
    )
    table.add_column("Key", style="cyan")
    table.add_column("Before", style="dim")
    table.add_column("After", style="green")
    table.add_column("Category", style="blue")

    for c in changes:
        cat = categorize_key(c.key)
        icon = CATEGORY_ICONS.get(cat, "📋")
        cat_label = CATEGORY_LABELS.get(cat, "")
        table.add_row(
            c.key,
            c.old_value or "[dim](not set)[/dim]",
            c.new_value or "[dim](unset)[/dim]",
            f"{icon} {cat_label}",
        )

    console.print(table)


def _checkbox_select(choices: List[str]) -> List[str]:
    """Simple checkbox-style selection. Returns selected keys."""
    selected: List[str] = []
    print()
    for i, (label, default_checked) in enumerate(choices):
        marker = "✓" if default_checked else "◻"
        print(f"  {marker} {label}")

    console.print()
    console.print("[dim]Enter keys to revert (comma-separated), or leave empty:[/dim]")
    raw = input("  > ").strip()
    if raw:
        selected = [s.strip() for s in raw.split(",") if s.strip()]
    return selected


def _choose_action() -> str:
    """Asks user to confirm or start over."""
    console.print("[bold]What now?[/bold]")
    console.print("  [green]1.[/green] Confirm & Save (done!)")
    console.print("  [yellow]2.[/yellow] Start Over")
    choice = input("  Choose [1/2]: ").strip()
    if choice == "2":
        return "start_over"
    return "confirm"


# ── set command ────────────────────────────────────────────


@app.command()
def set(
    key: Optional[str] = typer.Argument(
        None, help="Config key (e.g. user.name). Omit for interactive wizard."
    ),
    value: Optional[str] = typer.Argument(
        None, help="Value to set. Omit for interactive prompt."
    ),
) -> None:
    """Set Git global configuration values interactively or directly.

    Examples:\n
      chegi config git set              # Interactive 6-step wizard

      chegi config git set user.name Ali  # Direct
    """
    if key is None:
        _run_set_wizard()
        return

    if value is None:
        current = GitConfigService.get(key)
        prompt_text = f"  ? Enter value for [cyan]{key}[/cyan]"
        if current:
            prompt_text += f" [[{current}]]: "
        else:
            prompt_text += ": "
        raw = input(prompt_text).strip()
        value = raw if raw else current
        if value is None:
            TerminalUI.print_error("No value provided.")
            raise typer.Exit(code=1)

    old = GitConfigService.get(key)
    GitConfigService.set(key, value)
    TerminalUI.print_success(f"{key} set to '{value}'")
    if old and old != value:
        console.print(f"  [dim]Previous: {old}[/dim]")


# ── get command ────────────────────────────────────────────


@app.command()
def get(
    keys: List[str] = typer.Argument(
        None,
        help="One or more keys to display (e.g. user.name). Omit for interactive picker.",
    ),
) -> None:
    """Display Git global configuration values.

    Examples:\n
      chegi config git get                # Interactive — pick keys with checkbox

      chegi config git get user.name      # Single key

      chegi config git get user.name user.email  # Multiple keys
    """
    all_entries = GitConfigService.get_all()
    by_key = {e.key: e.value for e in all_entries}

    if keys:
        # Direct key lookup
        found = False
        for key in keys:
            val = by_key.get(key)
            if val is not None:
                console.print(f"[cyan]{key}[/cyan] = [green]{val}[/green]")
            else:
                console.print(f"[cyan]{key}[/cyan] = [dim](not set)[/dim]")
            found = True
        if not found:
            TerminalUI.print_error("No matching keys found.")
            raise typer.Exit(code=1)
        return

    # Interactive picker
    if not all_entries:
        console.print("[yellow]No global git config entries found.[/yellow]")
        return

    console.print()
    console.print("[bold gold1]🐆 Select Git Config to display[/bold gold1]")
    console.print("[dim](Space to toggle, Enter when done)[/dim]")
    console.print()

    # Group by category
    grouped: dict[GitConfigCategory, list] = {}
    for e in all_entries:
        grouped.setdefault(e.category, []).append(e)

    selected_keys: List[str] = []
    for cat in sorted(grouped.keys(), key=lambda c: c.value):
        entries = grouped[cat]
        icon = CATEGORY_ICONS.get(cat, "📋")
        label = CATEGORY_LABELS.get(cat, "")
        console.print(f"  [bold]{icon} {label}[/bold]")
        for e in entries:
            checked = "✓" if False else "◻"
            console.print(
                f"    {checked} [cyan]{e.key}[/cyan] = [green]{e.value}[/green]"
            )
            selected_keys.append(e.key)

    console.print()
    console.print(
        "[dim]Enter keys to display (comma-separated), or leave empty for all:[/dim]"
    )
    raw = input("  > ").strip()
    if raw:
        selected_keys = [s.strip() for s in raw.split(",") if s.strip()]
    else:
        selected_keys = [e.key for e in all_entries]

    if not selected_keys:
        console.print("[yellow]No keys selected.[/yellow]")
        return

    # Display selected
    table = Table(
        title="Git Global Config",
        title_style="bold gold1",
        border_style="gold1",
        header_style="bold",
    )
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Category", style="blue")

    for key in selected_keys:
        val = by_key.get(key, "")
        cat = categorize_key(key)
        icon = CATEGORY_ICONS.get(cat, "📋")
        cat_label = CATEGORY_LABELS.get(cat, "")
        table.add_row(
            key,
            val or "[dim](not set)[/dim]",
            f"{icon} {cat_label}",
        )

    console.print(table)
