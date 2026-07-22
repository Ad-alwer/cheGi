"""Root Typer application that registers all cheGi CLI commands."""

from importlib.metadata import PackageNotFoundError, version

import typer

# Import command modules
from chegi.cli.commands import (
    aliases,
    auth,
    branch,
    commit,
    completions,
    config,
    doctor,
    gitignore,
    guard,
    hooks,
    info,
    init,
    repo,
    reword,
    scan,
    setup,
    sync,
    upgrade,
)
from chegi.cli.commands.clone import clone_cmd
from chegi.cli.commands.new import new_cmd

# Import the preflight orchestrator
from chegi.cli.core.preflight import run_preflight_checks
from chegi.services.upgrade import UpgradeService

# Import the first-run wizard
from chegi.services.wizard import WizardService
from chegi.ui import TerminalUI

try:
    __version__ = version("chegi")
except PackageNotFoundError:
    __version__ = "0.0.0"

app = typer.Typer(
    help=(
        "cheGi - The ultimate Git companion. Type less, do more.\n\n"
        "cheGi simplifies your workflow by automating repository setup, managing "
        "multiple git configurations, enforcing security measures, and keeping "
        "your branches synchronized without the usual boilerplate."
    ),
    rich_markup_mode="rich",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands
app.add_typer(auth.app, name="auth")
app.add_typer(branch.app, name="branch")
app.add_typer(setup.app, name="setup")
app.add_typer(config.app, name="config")
app.add_typer(sync.app, name="sync")
app.add_typer(scan.app, name="scan")
app.command(name="clone")(clone_cmd)
app.add_typer(reword.app, name="reword")
app.add_typer(guard.app, name="guard")
app.add_typer(init.app, name="init")
app.add_typer(commit.app, name="commit")
app.add_typer(gitignore.app, name="gitignore")
app.command(name="new")(new_cmd)
app.add_typer(doctor.app, name="doctor")
app.add_typer(hooks.app, name="hooks")
app.add_typer(repo.app, name="repo")
app.add_typer(completions.app, name="completions")
app.add_typer(info.app, name="info")
app.add_typer(upgrade.app, name="upgrade")

# Register Git alias commands (pass-through to git)
alias_settings = {"allow_extra_args": True, "ignore_unknown_options": True}
app.command(name="co", context_settings=alias_settings)(aliases.co)
app.command(name="br", context_settings=alias_settings)(aliases.br)
app.command(name="ci", context_settings=alias_settings)(aliases.ci)
app.command(name="st", context_settings=alias_settings)(aliases.st)


@app.callback()
def global_setup(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show the version and exit.", is_eager=True
    ),
) -> None:
    """Global setup executed before any command is routed.

    Runs essential preflight system checks (e.g., Git installation)
    and the first-run wizard for new users.
    """
    if version:
        from rich.console import Console

        console = Console()
        console.print(f"[bold gold1]cheGi[/bold gold1] [white]v{__version__}[/white]")
        console.print("[dim]The ultimate Git companion. Type less, do more.[/dim]")
        raise typer.Exit()

    run_preflight_checks()
    WizardService().execute()
    _auto_upgrade_check()


def _auto_upgrade_check() -> None:
    """Checks for a newer version and prompts to upgrade, respecting cooldown."""
    from rich.text import Text

    from chegi.ui import console

    service = UpgradeService()

    if not service.should_check():
        return

    info = service.check_version()
    service.mark_checked()

    if info.error or not info.is_outdated:
        return

    console.print()
    msg = Text.assemble(
        ("\U0001f426 ", "bold gold1"),
        (f"A new version [bold]{info.latest_version}[/] is available!", ""),
    )
    console.print(msg)

    try:
        import questionary

        upgrade_now = questionary.confirm(
            "Upgrade now?",
            default=True,
        ).ask()
    except Exception:
        upgrade_now = False

    if upgrade_now:
        try:
            service.upgrade(yes=True)
            TerminalUI.print_success(
                f"Successfully upgraded to v{info.latest_version}!"
            )
        except Exception:
            TerminalUI.print_error(
                "Failed to upgrade. Run 'chegi upgrade' to try again."
            )
    else:
        console.print(
            "[dim]Run [bold]chegi upgrade[/] anytime to upgrade "
            "to the latest version.[/dim]"
        )


if __name__ == "__main__":
    app()
