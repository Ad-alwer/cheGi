from importlib.metadata import PackageNotFoundError, version

import typer

# Import command modules
from chegi.cli.commands import (
    aliases,
    auth,
    commit,
    config,
    doctor,
    gitignore,
    guard,
    hooks,
    init,
    repo,
    reword,
    scan,
    setup,
    sync,
)
from chegi.cli.commands.new import new_cmd

# Import the preflight orchestrator
from chegi.cli.core.preflight import run_preflight_checks

# Import the first-run wizard
from chegi.services.wizard import WizardService

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
app.add_typer(setup.app, name="setup")
app.add_typer(config.app, name="config")
app.add_typer(sync.app, name="sync")
app.add_typer(scan.app, name="scan")
app.add_typer(reword.app, name="reword")
app.add_typer(guard.app, name="guard")
app.add_typer(init.app, name="init")
app.add_typer(commit.app, name="commit")
app.add_typer(gitignore.app, name="gitignore")
app.command(name="new")(new_cmd)
app.add_typer(doctor.app, name="doctor")
app.add_typer(hooks.app, name="hooks")
app.add_typer(repo.app, name="repo")

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


if __name__ == "__main__":
    app()
