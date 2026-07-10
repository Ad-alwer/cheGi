from pathlib import Path
from typing import Optional

import questionary
import typer
from rich.prompt import Confirm

from chegi.config import GITIGNORE_COMMIT_MESSAGE
from chegi.services.environment import EnvManager
from chegi.services.git.client import GitClient
from chegi.ui.console import TerminalUI, console

app = typer.Typer(help="Generate a .gitignore file interactively.")


@app.callback(invoke_without_command=True)
def gitignore(
    path: str = typer.Option(
        ".", "--path", "-p", help="Directory to save the .gitignore file."
    ),
    auto_commit: Optional[bool] = typer.Option(
        None, "--commit", "-c", help="Automatically commit the generated file."
    ),
) -> None:
    """Creates a .gitignore file interactively by combining environment templates.

    Prompts the user to select one or more environments, generates a deduplicated
    .gitignore file, and optionally commits it to the local git repository.

    Args:
        path (str): Directory to save the .gitignore file. Defaults to ".".
        auto_commit (Optional[bool]): Automatically commit the generated file.
            If None, the user will be prompted interactively.

    Raises:
        typer.Exit: If the operation is cancelled, aborted, or encounters an error.
    """
    env_manager = EnvManager()
    
    # Initialize GitClient with the target path
    target_path = Path(path).expanduser().resolve()
    git_client = GitClient(target_path)

    console.print("\n[bold blue] 🐆 Chegi .gitignore Generator[/bold blue]\n")

    envs_with_gitignore = env_manager.get_envs_with_gitignore()
    if not envs_with_gitignore:
        TerminalUI.print_error("No gitignore templates found in the environments database.")
        raise typer.Exit(1)

    choices = [env.capitalize() for env in sorted(envs_with_gitignore)]
    selected_langs_caps = questionary.checkbox(
        "Select technologies for the .gitignore file (Space to select, Enter to confirm):",
        choices=choices,
    ).ask()

    if not selected_langs_caps:
        TerminalUI.print_error("Operation cancelled or no technologies selected.")
        raise typer.Exit(1)

    selected_langs = [lang.lower() for lang in selected_langs_caps]

    # Prevent accidental overwrites
    if env_manager.has_existing_gitignore(str(target_path)):
        if not Confirm.ask(
            f"⚠️  [yellow].gitignore already exists in '{target_path}'. Overwrite?[/yellow]",
            default=False,
        ):
            TerminalUI.print_error("Aborted.")
            raise typer.Exit(1)

    try:
        created_path = env_manager.generate_gitignore(selected_langs, str(target_path))
        console.print(f"\n[bold green]✅ Created:[/bold green] {created_path}")
    except Exception as e:
        TerminalUI.print_error(f"Error generating file: {e}")
        raise typer.Exit(1)

    # Handle git integration using GitClient
    if git_client.is_valid_repo():
        should_commit = (
            auto_commit
            if auto_commit is not None
            else typer.confirm(
                "🚀 Do you want to commit this new .gitignore file?", default=True
            )
        )

        if should_commit:
            try:
                console.print("[dim]Adding and committing .gitignore...[/dim]")
                commit_msg = GITIGNORE_COMMIT_MESSAGE
                
                # Using the generic commit_file method
                git_client.commit_file(".gitignore", commit_msg)
                
                console.print(
                    f"[bold green]✨ Committed with message:[/bold green] [cyan]{commit_msg}[/cyan]"
                )

            except Exception as e:
                TerminalUI.print_error(f"Failed to execute git commit: {e}")
        else:
            console.print("[dim]Skipping commit.[/dim]")
    else:
        TerminalUI.print_warning("Skipped commit: Not a git repository.")
