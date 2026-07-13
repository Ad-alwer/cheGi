"""CLI command for scaffolding new Git projects."""

from pathlib import Path
from typing import Optional

import questionary
import typer
from typing_extensions import Annotated

from chegi.services.environment import EnvManager
from chegi.services.new_project import NewProjectConfig, NewProjectService
from chegi.services.new_project.constants import (
    AVAILABLE_LICENSES,
    INITIAL_COMMIT_MESSAGE,
    TEMPLATE_TECH_MAP,
)
from chegi.services.new_project.exceptions import (
    NewProjectError,
    ProjectAlreadyExistsError,
)
from chegi.ui import TerminalUI, console


def new_cmd(
    project_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of the project (creates a new directory with this name)",
        ),
    ] = None,
    path: Annotated[
        str,
        typer.Option(
            "--path",
            "-p",
            help="Parent directory to create the project in",
        ),
    ] = ".",
    template: Annotated[
        Optional[str],
        typer.Option(
            "--template",
            "-t",
            help="Predefined project template (python, node, go, rust, ...)",
        ),
    ] = None,
    license: Annotated[
        Optional[str],
        typer.Option(
            "--license",
            "-l",
            help="License type (mit, apache, gpl3)",
        ),
    ] = None,
    no_readme: Annotated[
        bool,
        typer.Option(
            "--no-readme",
            help="Skip README.md generation",
        ),
    ] = False,
    no_gitignore: Annotated[
        bool,
        typer.Option(
            "--no-gitignore",
            help="Skip .gitignore generation",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Non-interactive mode — use defaults for all prompts",
        ),
    ] = False,
) -> None:
    """Create a new Git project from scratch.

    Scaffolds a complete project with Git initialization, .gitignore,
    .chegi/ directory, README.md, optional LICENSE, and an initial commit.

    Use [bold]chegi new <project-name>[/bold] to get started interactively.
    """
    target_path = Path(path).resolve()
    yes_mode = yes or template is not None

    # Interactive mode: prompt for project name if not given
    if project_name is None:
        project_name = questionary.text(
            "What is your project name?",
            validate=lambda val: (
                len(val.strip()) > 0 or "Project name cannot be empty."
            ),
        ).ask()

        if project_name is None:
            TerminalUI.print_error("Operation cancelled.")
            raise typer.Exit(1)

    config = NewProjectConfig(
        name=project_name,
        path=target_path,
        template=template,
        license_type=license,
        skip_readme=no_readme,
        skip_gitignore=no_gitignore,
        yes=yes_mode,
    )

    if not yes_mode:
        _run_interactive(config)
    else:
        _run_non_interactive(config)


def _run_interactive(config: NewProjectConfig) -> None:
    """Runs the interactive guided flow for project creation.

    Args:
        config: The base configuration to fill in interactively.
    """
    console.print("\n[bold gold1]🐆 Create a new cheGi project[/bold gold1]\n")
    console.print(
        f"[dim]Scaffolding: [bold]{config.name}[/bold] "
        f"at {config.path / config.name}[/dim]\n"
    )

    # Language selection for .gitignore
    env_manager = EnvManager()
    available_envs = env_manager.get_envs_with_gitignore()
    if available_envs and not config.skip_gitignore:
        choices = [env.capitalize() for env in sorted(available_envs)]
        selected_caps = questionary.checkbox(
            "Select technologies for .gitignore (Space to select, Enter to confirm):",
            choices=choices,
        ).ask()

        if selected_caps is None:
            TerminalUI.print_error("Operation cancelled.")
            raise typer.Exit(1)

        config.technologies = [lang.lower() for lang in selected_caps]

    # License selection
    if not config.license_type:
        license_choices = list(AVAILABLE_LICENSES.values())
        license_choice = questionary.select(
            "Select a license (or skip with Esc):",
            choices=["None (skip)"] + license_choices,
        ).ask()

        if license_choice is None or license_choice == "None (skip)":
            config.license_type = None
        else:
            reverse_map = {v: k for k, v in AVAILABLE_LICENSES.items()}
            config.license_type = reverse_map.get(license_choice)

    # Summary and confirmation
    tech_str = ", ".join(config.technologies) if config.technologies else "None"
    lic_str = (
        AVAILABLE_LICENSES.get(config.license_type, "None")
        if config.license_type
        else "None"
    )

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  [gold1]•[/gold1] Project:  [bold]{config.name}[/bold]")
    console.print(
        f"  [gold1]•[/gold1] Location: [dim]{config.path / config.name}[/dim]"
    )
    console.print(f"  [gold1]•[/gold1] .gitignore: [cyan]{tech_str}[/cyan]")
    console.print(f"  [gold1]•[/gold1] License:   [cyan]{lic_str}[/cyan]")

    if not typer.confirm("\nCreate this project?", default=True):
        TerminalUI.print_error("Aborted.")
        raise typer.Exit(1)

    _create_project(config)


def _run_non_interactive(config: NewProjectConfig) -> None:
    """Runs project creation in non-interactive mode.

    Args:
        config: The project configuration (uses defaults for unset values).
    """
    if config.template and config.template.lower() in TEMPLATE_TECH_MAP:
        config.technologies = TEMPLATE_TECH_MAP[config.template.lower()]

    _create_project(config)


def _create_project(config: NewProjectConfig) -> None:
    """Creates the project with the given configuration.

    Args:
        config: The final project configuration.
    """
    service = NewProjectService(config)

    try:
        result = service.create()
    except ProjectAlreadyExistsError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1) from e
    except NewProjectError as e:
        TerminalUI.print_error(f"Failed to create project: {e}")
        raise typer.Exit(code=1) from e

    console.print()
    TerminalUI.print_success(
        f"Project [bold cyan]{config.name}[/bold cyan] created at "
        f"[bold]{result.project_path}[/bold]"
    )
    console.print()

    for f in result.files_created:
        console.print(f"  [gold1]✓[/gold1] [bold]{f}[/bold]")

    if result.commit_hash:
        console.print(
            f"\n  [dim]Initial commit:[/dim] [cyan]{result.commit_hash}[/cyan]"
        )
        console.print(f"  [dim]Message:[/dim] {INITIAL_COMMIT_MESSAGE}")

    console.print(
        "\n[dim]Run [bold]cd {}/[/bold] to get started.[/dim]".format(config.name)
    )
