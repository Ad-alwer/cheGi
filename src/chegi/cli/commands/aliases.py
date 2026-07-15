"""Git alias commands for cheGi — type less, do more."""

import subprocess

import typer


def _run_git(subcommand: str, ctx: typer.Context) -> None:
    """Runs a git subcommand with extra args from context.

    Args:
        subcommand: The git subcommand (e.g. checkout, branch).
        ctx: The Typer context containing extra arguments.
    """
    cmd = ["git", subcommand] + list(ctx.args)
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise typer.Exit(code=e.returncode)
    except FileNotFoundError:
        typer.echo("Error: Git is not installed.", err=True)
        raise typer.Exit(code=1)


# Each command uses ignore_unknown_options so that all
# remaining CLI args pass through to the underlying git command.


def co(ctx: typer.Context) -> None:
    """Switch branches. Alias for git checkout."""
    _run_git("checkout", ctx)


def br(ctx: typer.Context) -> None:
    """List or manage branches. Alias for git branch."""
    _run_git("branch", ctx)


def ci(ctx: typer.Context) -> None:
    """Commit changes. Alias for git commit."""
    _run_git("commit", ctx)


def st(ctx: typer.Context) -> None:
    """Show working tree status. Alias for git status."""
    _run_git("status", ctx)
