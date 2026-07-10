import typer

# Import command modules
from chegi.cli.commands import config, gitignore, guard, reword, scan, setup, sync

# Import the preflight orchestrator
from chegi.cli.core.preflight import run_preflight_checks

app = typer.Typer(
    help=(
        "cheGi - The ultimate Git companion. Type less, do more.\n\n"
        "cheGi simplifies your workflow by automating repository setup, managing "
        "multiple git configurations, enforcing security measures, and keeping "
        "your branches synchronized without the usual boilerplate."
    ),
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Register subcommands
app.add_typer(setup.app, name="setup")
app.add_typer(config.app, name="config")
app.add_typer(sync.app, name="sync")
app.add_typer(scan.app, name="scan")
app.add_typer(reword.app, name="reword")
app.add_typer(guard.app, name="guard")
app.add_typer(gitignore.app, name="gitignore")


@app.callback()
def global_setup() -> None:
    """Global setup executed before any command is routed.

    Runs essential preflight system checks (e.g., Git installation)
    to ensure the environment is ready for cheGi operations.
    """
    run_preflight_checks()


if __name__ == "__main__":
    app()
