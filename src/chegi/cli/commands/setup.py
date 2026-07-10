"""Setup command module for the cheGi CLI.

Handles the installation and configuration of development environments.
Note: The core logic has been delegated to `SetupService` for cleaner architecture.
"""

import typer

from chegi.services.installer.setup_service import SetupService

app = typer.Typer()


@app.callback(invoke_without_command=True)
def setup_environment(
    environment: str = typer.Argument(
        ...,
        help="The programming language or toolset to setup (e.g., python, ruby, postman).",
    ),
    auto_yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Automatically answer yes to all installation prompts.",
    ),
) -> None:
    """Sets up the development environment or installs a standalone tool.
    
    This command acts as the CLI entry point and delegates the core logic 
    to the `SetupService`.
    
    Args:
        environment (str): The programming language or toolset to setup 
            (e.g., 'python', 'ruby', 'postman').
        auto_yes (bool, optional): Automatically answer yes to all installation 
            prompts. Defaults to False.
            
    Returns:
        None
    """
    
    service = SetupService(environment=environment, auto_yes=auto_yes)
    service.execute()
