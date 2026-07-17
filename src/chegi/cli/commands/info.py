"""CLI command for chegi info — quick project status overview."""

import json
import time
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from typing_extensions import Annotated

from chegi.services.info.info_service import InfoService
from chegi.services.info.models import InfoReport
from chegi.ui import TerminalUI, console

app = typer.Typer(
    help="Quick project status overview — branch, changes, sync, security.",
)


@app.callback(invoke_without_command=True)
def info(
    short: Annotated[
        bool,
        typer.Option("--short", "-s", help="One-line summary"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="JSON output"),
    ] = False,
    watch: Annotated[
        bool,
        typer.Option("--watch", "-w", help="Live refresh every 2 seconds"),
    ] = False,
    path: Annotated[
        Optional[str],
        typer.Option("--path", "-p", help="Target project directory"),
    ] = None,
) -> None:
    """Display a quick status overview of your project."""
    target = Path(path).resolve() if path else Path.cwd()

    if not target.is_dir():
        TerminalUI.print_error(f"Directory does not exist: {target}")
        raise typer.Exit(code=1)

    if watch:
        _watch_loop(target)
        return

    report = InfoService(target).collect()

    if json_output:
        _print_json(report)
    elif short:
        _print_short(report)
    else:
        _render_dashboard(report)

        if report.errors:
            raise typer.Exit(code=1)


def _print_json(report: InfoReport) -> None:
    """Prints the report as JSON.

    Args:
        report: The info report.
    """
    service = InfoService(report.path)
    typer.echo(json.dumps(service.to_json(report), indent=2))


def _print_short(report: InfoReport) -> None:
    """Prints a one-line summary.

    Args:
        report: The info report.
    """
    service = InfoService(report.path)
    typer.echo(service.to_short(report))


def _render_dashboard(report: InfoReport) -> None:
    """Renders the full Rich dashboard.

    Args:
        report: The info report to display.
    """
    if not report.is_git_repo:
        TerminalUI.print_error(f"Not a git repository: {report.path}")
        raise typer.Exit(code=1)

    project_name = report.path.name

    info_table = Table.grid(padding=(0, 1))
    info_table.add_column()

    _add_branch_section(info_table, report, project_name)
    _add_changes_section(info_table, report)
    _add_commit_section(info_table, report)
    _add_security_section(info_table, report)

    dashboard = Panel(
        info_table,
        title=Text.assemble(
            ("\U0001f426 ", "bold gold1"),
            ("cheGi Info", "bold gold1"),
        ),
        subtitle=Text(project_name, style="dim white"),
        border_style="gold1",
        padding=(1, 2),
    )

    console.print()
    console.print(dashboard)
    console.print()


def _sync_style(ahead: int, behind: int) -> str:
    """Returns the Rich style string for sync status.

    Args:
        ahead: Commits ahead of remote.
        behind: Commits behind remote.

    Returns:
        A Rich style string.
    """
    if ahead > 0 and behind > 0:
        return "bold red"
    if behind > 0:
        return "bold yellow"
    if ahead > 0:
        return "bold yellow"
    return "bold green"


def _change_style(count: int) -> str:
    """Returns the Rich style string for change count.

    Args:
        count: Number of changes.

    Returns:
        A Rich style string.
    """
    if count > 0:
        return "bold yellow"
    return "bold green"


def _guard_style(is_safe: bool) -> str:
    """Returns the Rich style string for guard status.

    Args:
        is_safe: Whether no sensitive files were found.

    Returns:
        A Rich style string.
    """
    return "bold green" if is_safe else "bold red"


def _sync_label(ahead: int, behind: int) -> str:
    """Returns a human-readable sync label.

    Args:
        ahead: Commits ahead of remote.
        behind: Commits behind remote.

    Returns:
        A sync status string.
    """
    if ahead > 0 and behind > 0:
        return f"\u2191{ahead} \u2193{behind} diverged"
    if behind > 0:
        return f"\u2193{behind} behind"
    if ahead > 0:
        return f"\u2191{ahead} ahead"
    return "synced"


def _add_branch_section(table: Table, report: InfoReport, project_name: str) -> None:
    """Adds the branch and sync section.

    Args:
        table: The grid table.
        report: The info report.
        project_name: The project folder name.
    """
    branch = report.branch or "?"
    clean_count = report.staged + report.modified + report.untracked
    clean_label = f"{clean_count} changed" if clean_count > 0 else "clean"

    table.add_row(
        Text.assemble(
            ("\U0001f331 ", "bold cyan"),
            (branch, "bold cyan"),
            ("  ", ""),
        ),
        Text.assemble(
            ("  ", ""),
            ("\u25cf", _change_style(clean_count)),
            (f" {clean_label}", _change_style(clean_count)),
        ),
    )

    if report.remote_name:
        remote_display = report.remote_name
        if report.remote_url:
            url = report.remote_url
            if len(url) > 40:
                url = url[:37] + "..."
            remote_display += f"  ({url})"
        table.add_row(
            Text.assemble(
                ("\u2601 ", "bold blue"),
                (remote_display, "bold blue"),
            ),
            "",
        )
        table.add_row(
            Text.assemble(
                ("  ", ""),
                ("\U0001f4e1 ", _sync_style(report.ahead, report.behind)),
                (
                    _sync_label(report.ahead, report.behind),
                    _sync_style(report.ahead, report.behind),
                ),
            ),
            Text.assemble(
                ("  ", ""),
                ("\U0001f4e6 ", "bold"),
                (f"{report.stash_count} stashed", "bold"),
            ),
        )
    else:
        table.add_row(
            Text.assemble(("  ", ""), ("No remote configured", "dim")),
            "",
        )

    table.add_row("", "")


def _add_changes_section(table: Table, report: InfoReport) -> None:
    """Adds the changes section.

    Args:
        table: The grid table.
        report: The info report.
    """
    parts = []
    if report.staged > 0:
        parts.append(
            Text.assemble(
                (f"{report.staged} staged", "bold green"),
            )
        )
    if report.modified > 0:
        parts.append(
            Text.assemble(
                (f"{report.modified} modified", "bold yellow"),
            )
        )
    if report.untracked > 0:
        parts.append(
            Text.assemble(
                (f"{report.untracked} untracked", "bold blue"),
            )
        )

    left = Text.assemble(
        ("\U0001f4dd ", "bold"),
    )
    if parts:
        for i, part in enumerate(parts):
            if i > 0:
                left.append("  \u00b7  ")
            left.append(part)
    else:
        left.append(Text("No changes", style="dim"))

    right = Text.assemble(
        ("\U0001f4e6 ", "bold"),
        (f"{report.stash_count} stashed", "bold"),
    )

    table.add_row(left, right)
    table.add_row("", "")


def _add_commit_section(table: Table, report: InfoReport) -> None:
    """Adds the last commit and contributors section.

    Args:
        table: The grid table.
        report: The info report.
    """
    if report.last_commit:
        commit_line = Text.assemble(
            ("\U0001f48e ", "bold magenta"),
            (report.last_commit.hash, "bold magenta"),
            ("  ", ""),
            (report.last_commit.message[:60], "white"),
        )
        table.add_row(commit_line, "")

        author_line = Text.assemble(
            ("  ", ""),
            ("\U0001f464 ", "bold"),
            (report.last_commit.author, "bold"),
            ("  \u00b7  ", "dim"),
            ("\U0001f550 ", "bold"),
            (report.last_commit.date, ""),
        )
        table.add_row(author_line, "")

    contributors = Text.assemble(
        ("\U0001f465 ", "bold"),
        (f"{report.contributor_count} contributors", ""),
    )
    if report.latest_tag:
        tag_text = Text.assemble(
            ("\U0001f3f7 ", "bold"),
            (report.latest_tag, "bold cyan"),
            ("  ", ""),
            (f"{report.commits_since_tag} commits since", "dim"),
        )
        table.add_row(contributors, tag_text)
    else:
        table.add_row(contributors, "")

    table.add_row("", "")


def _add_security_section(table: Table, report: InfoReport) -> None:
    """Adds the security and config section.

    Args:
        table: The grid table.
        report: The info report.
    """
    check_mark = "\u2713"
    cross_mark = "\u2716"

    guard_icon = check_mark if not report.has_sensitive_files else cross_mark
    guard_text = (
        "No sensitive files"
        if not report.has_sensitive_files
        else f"{report.sensitive_file_count} sensitive files found"
    )
    table.add_row(
        Text.assemble(
            ("\U0001f6e1 ", _guard_style(not report.has_sensitive_files)),
            ("Guard: ", ""),
            (
                f"{guard_icon}  {guard_text}",
                _guard_style(not report.has_sensitive_files),
            ),
        ),
        Text.assemble(
            ("\U0001f517 ", "bold green" if report.has_hooks else "dim"),
            ("Hooks: ", ""),
            (
                "\u2713  Installed" if report.has_hooks else "Not installed",
                "bold green" if report.has_hooks else "dim",
            ),
        ),
    )

    identity_icon = check_mark if report.git_identity_set else cross_mark
    chegi_icon = check_mark if report.has_chegi_dir else cross_mark
    table.add_row(
        Text.assemble(
            ("\U0001f464 ", "bold green" if report.git_identity_set else "bold red"),
            (f"Identity: {identity_icon}  ", ""),
            (
                "Set" if report.git_identity_set else "Not set",
                "bold green" if report.git_identity_set else "bold red",
            ),
        ),
        Text.assemble(
            ("\u2699 ", "bold green" if report.has_chegi_dir else "dim"),
            ("\U0001f914.chegi/: ", ""),
            (
                f"{chegi_icon}  Configured"
                if report.has_chegi_dir
                else "Not configured",
                "bold green" if report.has_chegi_dir else "dim",
            ),
        ),
    )


def _watch_loop(target: Path) -> None:
    """Re-renders the dashboard every 2 seconds.

    Args:
        target: The project directory.
    """
    try:
        while True:
            console.clear()
            report = InfoService(target).collect()
            _render_dashboard(report)
            time.sleep(2)
    except KeyboardInterrupt:
        pass
