import typer

# Import command modules
from chegi.cli.commands import config, sync, scan, security, setup

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
# (Currently commented out. We will uncomment them one by one as we migrate the code)

app.add_typer(setup.app, name="setup")
app.add_typer(config.app, name="config")
app.add_typer(sync.app, name="sync")
app.add_typer(scan.app , name="scan")
# app.add_typer(security.app)

if __name__ == "__main__":
    app()
