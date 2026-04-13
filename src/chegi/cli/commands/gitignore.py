from pathlib import Path
from typing import Optional

import typer
import questionary
from rich.prompt import Confirm

from chegi.services.environment import EnvManager
from chegi.services.git.client import GitClient
from chegi.ui.console import TerminalUI

app = typer.Typer(help="Generate a .gitignore file interactively.")


@app.command("gitignore", help="Generate a .gitignore file interactively.")
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
    ui = TerminalUI()
    env_manager = EnvManager()
    
    # Initialize GitClient with the target path
    target_path = Path(path).expanduser().resolve()
    git_client = GitClient(target_path)

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

    # Prevent accidental overwrites
    if env_manager.has_existing_gitignore(str(target_path)):
        if not Confirm.ask(
            f"⚠️  [yellow].gitignore already exists in '{target_path}'. Overwrite?[/yellow]",
            default=False,
        ):
            ui.console.print("[bold red]Aborted.[/bold red]")
            raise typer.Exit(1)

    try:
        created_path = env_manager.generate_gitignore(selected_langs, str(target_path))
        ui.console.print(f"\n[bold green]✅ Created:[/bold green] {created_path}")
    except Exception as e:
        ui.print_error(f"Error generating file: {e}")
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
                ui.console.print("[dim]Adding and committing .gitignore...[/dim]")
                commit_msg = "chore: add .gitignore [cheGi]"
                
                # Using the new generic commit_file method
                git_client.commit_file(".gitignore", commit_msg)
                
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
