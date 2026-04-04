import subprocess
from typing import Annotated, Optional

import questionary
import typer
from rich.prompt import Confirm

from chegi.env_manager import EnvManager
from chegi.git_utils import (
    check_git_environment,
    is_workspace_clean,
    perform_automated_rebase,
    pop_stash,
    pull_rebase,
    push_changes,
    stash_changes,
)
from chegi.installer import SystemInstaller
from chegi.security import SecurityGuard
from chegi.ui import TerminalUI

app = typer.Typer(
    help=(
        "cheGi - The ultimate Git companion. Type less, do more.\n\n"
        "A fast, concurrent Git toolkit to guard sensitive data, "
        "safely sync changes, generate .gitignore files, and setup dev environments "
        "with automated system installers and custom mirror support."
    )
)


@app.callback()
def global_setup() -> None:
    """Global setup executed before any command.

    Validates the Git environment. If Git is missing or outdated, it prompts
    the user to automatically install or update it using the SystemInstaller.

    Raises:
        typer.Exit: If the user aborts the installation, if the installation
            fails, or upon successful installation requiring a terminal restart.
    """
    is_valid, message = check_git_environment()

    if not is_valid:
        ui = TerminalUI()
        ui.print_error(f"Environment Check Failed: {message}")

        install_now = typer.confirm(
            "Git is missing or outdated. Do you want cheGi to automatically install/update Git for you?"
        )

        if not install_now:
            ui.print_error(
                "Installation aborted. cheGi requires Git to function properly."
            )
            raise typer.Exit(code=1)

        ui.console.print("\n[bold cyan]Starting installation process...[/bold cyan]")
        success = SystemInstaller.install_package("git")

        if success:
            ui.console.print(
                "\n[bold green]Success! Git has been installed/updated.[/bold green]"
            )
            ui.console.print(
                "[bold magenta]IMPORTANT: Please restart your terminal (close and open it again) "
                "so the system can recognize the 'git' command.[/bold magenta]"
            )
            raise typer.Exit(code=0)
        else:
            ui.print_error(
                "Failed to install Git automatically. Please install it manually from https://git-scm.com/"
            )
            raise typer.Exit(code=1)


@app.command("guard")
def guard(
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            "-f",
            help="Automatically unstage sensitive files without prompting",
        ),
    ] = False,
) -> None:
    """Checks staged files for sensitive data to prevent accidental commits."""
    ui = TerminalUI()
    ui.console.print("[dim]🔒 Running Security Guard...[/dim]")

    staged_files = SecurityGuard.get_staged_files()
    if not staged_files:
        ui.console.print(
            "[bold blue]No staged files found. Nothing to check.[/bold blue]"
        )
        raise typer.Exit()

    sensitive_files = SecurityGuard.find_sensitive_files(staged_files)

    if sensitive_files:
        ui.console.print(
            "\n[bold red]⚠️  WARNING: Sensitive files detected in staging area![/bold red]"
        )
        for f in sensitive_files:
            ui.console.print(f"  [red]- {f}[/red]")

        files_str = " ".join(sensitive_files)
        exact_command = f"git rm --cached {files_str}"
        ui.console.print(
            f"\n[bold yellow]To fix this manually, run:[/bold yellow] [cyan]{exact_command}[/cyan]\n"
        )

        if fix:
            success = SecurityGuard.unstage_files(sensitive_files)
            if success:
                ui.console.print(
                    "\n[bold green]✅ Files successfully unstaged automatically (via --fix). You can now commit safely.[/bold green]"
                )
            else:
                ui.print_error(
                    "\nFailed to unstage files automatically. Please run the command manually."
                )
        else:
            should_unstage = typer.confirm(
                "Do you want cheGi to automatically unstage these files for you?"
            )

            if should_unstage:
                success = SecurityGuard.unstage_files(sensitive_files)
                if success:
                    ui.console.print(
                        "\n[bold green]✅ Files successfully unstaged. You can now commit safely.[/bold green]"
                    )
                else:
                    ui.print_error(
                        "\nFailed to unstage files automatically. Please run the command manually."
                    )

        raise typer.Exit(code=1)
    else:
        ui.console.print(
            "[bold green]✅ Security check passed. No sensitive files found in staging.[/bold green]"
        )


@app.command("gitignore")
def gitignore(
    path: str = typer.Option(
        ".", "--path", "-p", help="Directory to save the .gitignore file."
    ),
    auto_commit: bool = typer.Option(
        None, "--commit", "-c", help="Automatically commit the generated file."
    ),
) -> None:
    """Creates a .gitignore file interactively by combining environment templates.

    Prompts the user to select one or more environments, generates a deduplicated
    .gitignore file, and optionally commits it to the local git repository.
    """
    ui = TerminalUI()
    env_manager = EnvManager()

    ui.console.print("\n[bold blue] 🐆 Chegi .gitignore Generator[/bold blue]\n")

    envs_with_gitignore = env_manager.get_envs_with_gitignore()
    if not envs_with_gitignore:
        ui.print_error("No gitignore templates found in the environments database.")
        raise typer.Exit(1)

    choices = [env.capitalize() for env in sorted(envs_with_gitignore)]
    selected_langs_caps = questionary.checkbox(
        "Select technologies for the .gitignore file (Space to select, Enter to confirm):",
        choices=choices,
    ).ask()

    if not selected_langs_caps:
        ui.console.print(
            "[bold red]Operation cancelled or no technologies selected.[/bold red]"
        )
        raise typer.Exit(1)

    selected_langs = [lang.lower() for lang in selected_langs_caps]

    if env_manager.has_existing_gitignore(path):
        if not Confirm.ask(
            f"⚠️  [yellow].gitignore already exists in '{path}'. Overwrite?[/yellow]",
            default=False,
        ):
            ui.console.print("[bold red]Aborted.[/bold red]")
            raise typer.Exit()

    try:
        created_path = env_manager.generate_gitignore(selected_langs, path)
        ui.console.print(f"\n[bold green]✅ Created:[/bold green] {created_path}")
    except Exception as e:
        ui.print_error(f"Error generating file: {e}")
        raise typer.Exit(1)

    if env_manager.is_git_repo(path):
        should_commit = (
            auto_commit
            if auto_commit is not None
            else typer.confirm(
                "🚀 Do you want to commit this new .gitignore file?", default=True
            )
        )

        if should_commit:
            try:
                ui.console.print("[dim]Adding and committing .gitignore...[/dim]")
                commit_msg = env_manager.commit_gitignore(path)
                ui.console.print(
                    f"[bold green]✨ Committed with message:[/bold green] [cyan]{commit_msg}[/cyan]"
                )

            except Exception as e:
                ui.print_error(f"Failed to execute git commit: {e}")
        else:
            ui.console.print("[dim]Skipping commit.[/dim]")
    else:
        ui.console.print(
            "[bold yellow]⚠️  Skipped commit: Not a git repository.[/bold yellow]"
        )


@app.command("reword")
def reword(
    message: Optional[str] = typer.Argument(None, help="The new commit message"),
    last: Optional[int] = typer.Option(
        None, "--last", "-l", help="Number of recent commits to choose from", min=1
    ),
    start: Optional[int] = typer.Option(
        None, "--start", "-s", help="Start index for commit list (e.g., 15)", min=0
    ),
    end: Optional[int] = typer.Option(
        None, "--end", "-e", help="End index for commit list (e.g., 25)", min=1
    ),
) -> None:
    """Changes a commit message interactively or directly."""
    ui = TerminalUI()

    if last is not None and last > 20:
        ui.print_error("❌ Maximum limit for --last is 20.")
        ui.print_error(
            "💡 Please use --start/-s and --end/-e flags to navigate older commits."
        )
        raise typer.Exit(1)

    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        ui.print_error("❌ Not a git repository.")
        raise typer.Exit(1)

    target_hash = "HEAD"
    is_head = True

    show_menu = last is not None or start is not None or end is not None

    if show_menu:
        if start is not None and end is not None:
            if start >= end:
                ui.print_error("❌ Error: --start must be less than --end.")
                raise typer.Exit(1)
            skip = start
            limit = end - start
        elif start is not None:
            skip = start
            limit = 10
        elif end is not None:
            skip = max(0, end - 10)
            limit = end - skip
        else:
            skip = 0
            limit = last if last else 10

        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--max-count={limit}",
                    f"--skip={skip}",
                    "--format=%h %s",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            commits = [line for line in result.stdout.strip().split("\n") if line]

            if not commits:
                ui.print_error("❌ No commits found in the specified range.")
                raise typer.Exit(1)

            choice = questionary.select(
                "Select the commit to reword:", choices=commits
            ).ask()

            if not choice:
                raise typer.Exit(0)

            target_hash = choice.split(" ")[0]

            head_hash = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
            ).stdout.strip()

            is_head = target_hash == head_hash

        except subprocess.CalledProcessError:
            ui.print_error("❌ Failed to fetch git history.")
            raise typer.Exit(1)

    try:
        old_msg_result = subprocess.run(
            ["git", "log", "--format=%B", "-n", "1", target_hash],
            check=True,
            capture_output=True,
            text=True,
        )
        old_message = old_msg_result.stdout.strip()
    except subprocess.CalledProcessError:
        ui.print_error("❌ Failed to fetch the commit message.")
        raise typer.Exit(1)

    if not message:
        message = questionary.text(
            "Enter new commit message:", default=old_message
        ).ask()

        if not message:
            ui.print_error("❌ Commit message cannot be empty.")
            raise typer.Exit(1)

    if message == old_message:
        ui.print_success("✅ Message is unchanged. Exiting without modifying history.")
        return

    if is_head:
        try:
            subprocess.run(["git", "commit", "--amend", "-m", message], check=True)
            ui.print_success("✅ Last commit message updated successfully!")
        except subprocess.CalledProcessError:
            ui.print_error("❌ Failed to amend the commit.")
            raise typer.Exit(1)
    else:
        try:
            perform_automated_rebase(target_hash, message)
            ui.print_success(f"✅ Commit {target_hash} updated successfully!")
        except Exception as e:
            ui.print_error(f"❌ Failed to rebase: {e}")
            raise typer.Exit(1)


@app.command()
def sync():
    """Synchronizes the local repository with the remote safely."""
    ui = TerminalUI()
    ui.print_info("Starting synchronization process...")

    needs_stash = False

    if not is_workspace_clean():
        ui.print_warning("You have uncommitted changes in your workspace.")

        confirm_stash = typer.confirm(
            "Do you want to automatically stash changes, sync, and restore them?",
            default=False,
        )
        if not confirm_stash:
            ui.print_error(
                "Sync aborted. Please commit or stash your changes manually."
            )
            raise typer.Exit(1)

        ui.print_warning(
            "Restoring changes (stash pop) after sync might result in merge conflicts."
        )
        confirm_again = typer.confirm(
            "Are you absolutely sure you want to proceed?", default=False
        )
        if not confirm_again:
            ui.print_error(
                "Sync aborted. Please commit or stash your changes manually."
            )
            raise typer.Exit(1)

        needs_stash = True

    if needs_stash:
        ui.print_info("Stashing uncommitted changes...")
        try:
            stash_changes()
        except RuntimeError as e:
            ui.print_error(str(e))
            raise typer.Exit(1)

    ui.print_info("Pulling latest changes from remote (rebase)...")
    try:
        pull_rebase()
    except RuntimeError as e:
        ui.print_error("❌ Conflict or error during pull --rebase.")
        ui.print_error(str(e))
        ui.print_warning(
            "💡 Please resolve conflicts manually, then run 'git rebase --continue'."
        )
        if needs_stash:
            ui.print_info("ℹ️ Your uncommitted changes are safely stored in git stash.")
        raise typer.Exit(1)

    ui.print_info("Pushing local commits to remote...")
    try:
        push_changes()
    except RuntimeError as e:
        ui.print_error("❌ Error during push.")
        ui.print_error(str(e))
        if needs_stash:
            ui.print_info("ℹ️ Your uncommitted changes are safely stored in git stash.")
        raise typer.Exit(1)

    if needs_stash:
        ui.print_info("Restoring stashed changes...")
        try:
            pop_stash()
        except RuntimeError as e:
            ui.print_warning(
                "⚠️ Conflict or error occurred while restoring stashed changes."
            )
            ui.print_error(str(e))
            ui.print_warning(
                "💡 Please resolve the conflicts manually in your code editor."
            )

    ui.print_success("Synchronization completed successfully! 🚀")


def main() -> None:
    """Main entry point for the cheGi Typer CLI application."""
    app()
