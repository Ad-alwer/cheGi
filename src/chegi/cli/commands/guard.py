"""CLI command for chegi guard — security scanning."""

import shlex
from pathlib import Path
from typing import List, Optional, Set

import typer
from typing_extensions import Annotated

from chegi.config import ChegiConfig
from chegi.services.git.client import GitClient
from chegi.services.guard import GuardHistoryService, HistoryScanResult, SecurityGuard
from chegi.ui import TerminalUI, console


def _get_extra_patterns(path: Optional[Path] = None) -> Optional[Set[str]]:
    """Reads custom sensitive patterns from project config.

    Args:
        path: Base path for config. Defaults to CWD.

    Returns:
        Set of custom patterns, or None if none configured.
    """
    try:
        cfg = ChegiConfig(str(path or Path.cwd()))
        if cfg.sensitive_patterns:
            return cfg.sensitive_patterns
    except Exception:
        pass
    return None


app = typer.Typer(
    help="Check staged files, directory trees, or Git history for sensitive data."
)


@app.callback(invoke_without_command=True)
def guard(
    ctx: typer.Context,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            "-f",
            help="Automatically unstage sensitive files without prompting",
        ),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            "-S",
            help="Scan both staged and unstaged files; auto-unstage sensitive staged files",
        ),
    ] = False,
    scan: Annotated[
        Optional[Path],
        typer.Option(
            "--scan",
            help="Recursively scan a directory for sensitive files (no Git repo required)",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
    ] = None,
) -> None:
    """Check staged files, directory trees, or Git history for sensitive data.

    Scans files against known sensitive patterns (e.g., .env, keys, .pem).
    Detected sensitive files can be automatically unstaged.

    Use [bold]chegi guard history[/bold] to scan Git history for secrets.
    """
    if ctx.invoked_subcommand is not None:
        return

    # --scan mode: directory scan, no Git repo needed
    if scan is not None:
        _handle_scan(scan)
        return

    # --strict mode: staged + unstaged
    if strict:
        _handle_strict(fix)
        return

    console.print("[dim]🔒 Running Security Guard...[/dim]")

    git_client = GitClient(Path.cwd())
    if not git_client.is_valid_repo():
        TerminalUI.print_error(
            "fatal: not a git repository (or any of the parent directories): .git"
        )
        raise typer.Exit(code=1)

    extra_patterns = _get_extra_patterns()
    staged_files = SecurityGuard.get_staged_files()
    if not staged_files:
        console.print("[bold blue]No staged files found. Nothing to check.[/bold blue]")
        raise typer.Exit()

    sensitive_files = SecurityGuard.find_sensitive_files(staged_files, extra_patterns)

    if sensitive_files:
        _handle_sensitive_staged(sensitive_files, fix)
    else:
        console.print(
            "[bold green]✅ Security check passed. No sensitive files found in staging.[/bold green]"
        )


def _handle_strict(fix: bool) -> None:
    """Handles --strict mode: scans staged + unstaged, auto-unstages staged sensitive files.

    Args:
        fix: If True, skip confirmation prompt for unstaging.
    """
    console.print("[dim]🔒 Running Security Guard (strict mode)...[/dim]")

    git_client = GitClient(Path.cwd())
    if not git_client.is_valid_repo():
        TerminalUI.print_error(
            "fatal: not a git repository (or any of the parent directories): .git"
        )
        raise typer.Exit(code=1)

    extra_patterns = _get_extra_patterns()
    staged_result, unstaged_result = SecurityGuard.scan_strict(
        extra_patterns=extra_patterns
    )

    has_sensitive_staged = not staged_result.is_safe
    has_sensitive_unstaged = not unstaged_result.is_safe

    if has_sensitive_staged:
        console.print(
            "\n[bold red]⚠️  Sensitive files detected in staging area![/bold red]"
        )
        for f in staged_result.sensitive_files:
            console.print(f"  [red]  staged: {f}[/red]")

        if fix or typer.confirm("Automatically unstage these files?"):
            success = SecurityGuard.unstage_files(staged_result.sensitive_files)
            if success:
                console.print(
                    "[bold green]✅ Files successfully unstaged.[/bold green]"
                )
            else:
                TerminalUI.print_error("Failed to unstage files.")

    if has_sensitive_unstaged:
        console.print(
            "\n[bold yellow]⚠️  Sensitive files detected in working directory (not staged):[/bold yellow]"
        )
        for f in unstaged_result.sensitive_files:
            console.print(f"  [yellow]  {f}[/yellow]")
        console.print(
            "\n[yellow]Run [bold]chegi guard --scan .[/bold] for a full directory scan.[/yellow]"
        )

    if not has_sensitive_staged and not has_sensitive_unstaged:
        console.print(
            "[bold green]✅ Strict security check passed. No sensitive files found.[/bold green]"
        )

    if has_sensitive_staged or has_sensitive_unstaged:
        raise typer.Exit(code=1)


def _handle_scan(path: Path) -> None:
    """Handles --scan mode: recursively scans a directory for sensitive files.

    Args:
        path: The directory path to scan.
    """
    console.print(f"[dim]🔒 Scanning directory: {path}[/dim]")

    extra_patterns = _get_extra_patterns(path)
    result = SecurityGuard.scan_directory(path, extra_patterns)

    if result.is_safe:
        console.print(
            "[bold green]✅ Directory scan complete. No sensitive files found.[/bold green]"
        )
        return

    console.print(
        f"\n[bold red]⚠️  Found {len(result.sensitive_files)} sensitive file(s):[/bold red]"
    )
    for f in result.sensitive_files:
        console.print(f"  [red]- {f}[/red]")

    raise typer.Exit(code=1)


def _handle_sensitive_staged(sensitive_files: List[str], fix: bool) -> None:
    """Handles the case where sensitive files are found in staging.

    Args:
        sensitive_files: List of sensitive file paths.
        fix: If True, auto-unstage without prompting.
    """
    console.print(
        "\n[bold red]⚠️  WARNING: Sensitive files detected in staging area![/bold red]"
    )
    for f in sensitive_files:
        console.print(f"  [red]- {f}[/red]")

    files_str = " ".join(shlex.quote(f) for f in sensitive_files)
    exact_command = f"git rm --cached {files_str}"
    console.print(
        f"\n[bold yellow]To fix this manually, run:[/bold yellow] [cyan]{exact_command}[/cyan]\n"
    )

    if fix:
        success = SecurityGuard.unstage_files(sensitive_files)
        if success:
            console.print(
                "\n[bold green]✅ Files successfully unstaged automatically (via --fix)."
                " You can now commit safely.[/bold green]"
            )
        else:
            TerminalUI.print_error(
                "\nFailed to unstage files automatically. Please run the command manually."
            )
    else:
        should_unstage = typer.confirm(
            "Do you want cheGi to automatically unstage these files for you?"
        )

        if should_unstage:
            success = SecurityGuard.unstage_files(sensitive_files)
            if success:
                console.print(
                    "\n[bold green]✅ Files successfully unstaged."
                    " You can now commit safely.[/bold green]"
                )
            else:
                TerminalUI.print_error(
                    "\nFailed to unstage files automatically. Please run the command manually."
                )

    raise typer.Exit(code=1)


@app.command()
def history(
    report: Annotated[
        bool,
        typer.Option(
            "--report",
            "-r",
            help="Generate an HTML report of findings",
        ),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            "-f",
            help="Remove detected files from Git history with confirmation",
        ),
    ] = False,
) -> None:
    """Scan Git history for sensitive files across all branches.

    Searches all commits in the repository for files matching sensitive patterns
    (e.g., .env, keys, secrets). Results are displayed per commit with
    file paths and matched patterns.
    """
    git_client = GitClient(Path.cwd())
    if not git_client.is_valid_repo():
        TerminalUI.print_error(
            "fatal: not a git repository (or any of the parent directories): .git"
        )
        raise typer.Exit(code=1)

    scanner = GuardHistoryService()
    result = scanner.scan()

    GuardHistoryService.print_findings(result)

    if report and result.findings:
        report_path = GuardHistoryService.generate_report(result, Path.cwd())
        TerminalUI.print_success(f"HTML report saved to {report_path}")

    if fix and result.findings:
        _handle_history_removal(scanner, result)

    if not result.findings:
        raise typer.Exit()
    if not fix and not report:
        raise typer.Exit(code=1)


def _handle_history_removal(scanner: GuardHistoryService, result: HistoryScanResult) -> None:
    """Handles removal of sensitive files from Git history.

    Shows strong warnings, lists affected files, and requires explicit
    user confirmation before executing git filter-branch.

    Args:
        scanner: The GuardHistoryService instance.
        result: The HistoryScanResult with findings.
    """
    console.print(
        "\n[bold red]⚠️  DESTRUCTIVE ACTION: Removing files from Git history![/bold red]"
    )
    console.print(
        "[bold red]This will rewrite Git history for ALL branches."
        " This is IRREVERSIBLE.[/bold red]"
    )
    console.print(
        "[bold red]All collaborators will need to force-pull"
        " and rebase their work.[/bold red]\n"
    )

    seen_files: set[str] = set()
    for finding in result.findings:
        if finding.file_path not in seen_files:
            seen_files.add(finding.file_path)
            console.print(f"  [red]● {finding.file_path}[/red]")

    console.print(
        "\n[bold yellow]The following commands will be executed for each file:[/bold yellow]\n"
    )
    for file_path in seen_files:
        console.print(
            f"  [dim]git filter-branch --force --index-filter"
            f" 'git rm --cached --ignore-unmatch {shlex.quote(file_path)}'"
            f" --prune-empty --tag-name-filter cat -- --all[/dim]\n"
        )

    console.print(
        "[yellow]⚠️  After completion, force push with:"
        " git push origin --force --all[/yellow]\n"
    )

    if not typer.confirm(
        "[bold red]Are you ABSOLUTELY SURE you want to proceed?[/bold red]",
        default=False,
    ):
        console.print("[bold blue]Removal cancelled by user.[/bold blue]")
        raise typer.Exit()

    failed: list[str] = []
    for file_path in seen_files:
        console.print(f"[yellow]Removing {file_path} from history...[/yellow]")
        success = scanner.remove_file_from_history(file_path)
        if success:
            console.print(
                f"  [bold green]✅ {file_path} removed successfully.[/bold green]"
            )
        else:
            console.print(f"  [bold red]❌ Failed to remove {file_path}[/bold red]")
            failed.append(file_path)

    if not failed:
        console.print(
            "\n[bold green]✅ All files removed from Git history.[/bold green]"
        )
        console.print(
            "[yellow]⚠️  Don't forget to force push:"
            " git push origin --force --all[/yellow]"
        )
    else:
        TerminalUI.print_error(
            f"\nFailed to remove {len(failed)} file(s). Check the error messages above."
        )

    raise typer.Exit(code=1 if failed else 0)
