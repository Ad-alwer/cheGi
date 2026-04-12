import json
from typing import Optional

import typer

from chegi.config import ChegiConfig
from chegi.ui import TerminalUI, console

app = typer.Typer(
    help=(
        "Manage cheGi's global configuration.\n\n"
        "Configure scan depths, add/remove ignored directories, and setup custom "
        "registry mirrors (e.g., pip, npm) to speed up environment setups."
    )
)


@app.command("list")
def config_list(
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Lists the current configuration settings, including saved mirrors.

    Args:
        path (str): Base directory for the configuration file.
    """
    config = ChegiConfig(base_path=path)
    config.load()

    console.print("[bold]Current Configuration:[/bold]")
    console.print(f"  Max Depth: {config.max_depth}")
    console.print(f"  MCTS: {getattr(config, 'mcts', 10)}")
    console.print(f"  Exclude Dirs: {', '.join(config.exclude_dirs)}")

    # Display configured mirrors if any exist
    if hasattr(config, "mirrors") and config.mirrors:
        console.print("  [bold]Saved Mirrors:[/bold]")
        for pm, urls in config.mirrors.items():
            if not urls:
                continue

            # Format the output depending on whether there's a single URL or multiple
            if len(urls) == 1:
                console.print(f"    - {pm}: [cyan]{urls[0]}[/cyan]")
            else:
                console.print(f"    - {pm}:")
                for url in urls:
                    console.print(f"      • [cyan]{url}[/cyan]")
    else:
        console.print("  [bold]Saved Mirrors:[/bold] None")


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (e.g., max_depth, mcts)"),
    value: int = typer.Argument(..., help="New integer value"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Updates a specific configuration setting.

    Args:
        key (str): The configuration key to update.
        value (int): The new integer value to assign.
        path (str): Base directory for the configuration file.

    Raises:
        typer.Exit: If the provided value is invalid.
    """
    config = ChegiConfig(base_path=path)
    config.load()

    try:
        config.update_setting(key, value)
        config.save()
        console.print(f"[green]Successfully updated '{key}' to {value}.[/green]")
    except ValueError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)


@app.command("exclude-add")
def config_exclude_add(
    folder: str = typer.Argument(..., help="Folder name to ignore"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Adds a directory name to the scanning exclusion list.

    Args:
        folder (str): The name of the directory to exclude from scans.
        path (str): Base directory for the configuration file.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    config.add_exclude(folder)
    config.save()

    console.print(f"[green]Added '{folder}' to the exclude list.[/green]")


@app.command("exclude-remove")
def config_exclude_remove(
    folder: str = typer.Argument(..., help="Folder name to stop ignoring"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Removes a directory name from the scanning exclusion list.

    Args:
        folder (str): The name of the directory to remove from the exclusion list.
        path (str): Base directory for the configuration file.

    Raises:
        typer.Exit: If the folder does not exist in the exclusion list.
    """
    config = ChegiConfig(base_path=path)
    config.load()

    try:
        config.remove_exclude(folder)
        config.save()
        console.print(f"[green]Removed '{folder}' from the exclude list.[/green]")
    except ValueError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)


@app.command("mirror-add")
def config_mirror_add(
    pm_name: str = typer.Argument(..., help="Package manager name (e.g., pip, npm)"),
    url: str = typer.Argument(..., help="The mirror URL to use"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Adds or updates a single mirror URL for a package manager.

    Args:
        pm_name (str): The target package manager.
        url (str): The custom registry or mirror URL.
        path (str): Base directory for the configuration file.

    Raises:
        typer.Exit: If the package manager is not supported or URL is invalid.
    """
    config = ChegiConfig(base_path=path)
    config.load()

    try:
        config.set_mirror(pm_name, url)
        config.save()
        console.print(
            f"[green]✔ Successfully added/updated mirror for '{pm_name.lower()}' -> '{url}'.[/green]"
        )
    except ValueError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)


@app.command(name="mirror-remove")
def config_mirror_remove(
    pm_name: str = typer.Argument(
        ..., help="The package manager name (e.g., pip, npm)."
    ),
    url: Optional[str] = typer.Argument(
        None,
        help="The specific mirror URL to remove. If omitted, all mirrors for this PM are removed.",
    ),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Removes a mirror configuration.

    Args:
        pm_name (str): The target package manager.
        url (Optional[str]): Specific URL to remove. Defaults to None (removes all).
        path (str): Base directory for the configuration file.

    Raises:
        typer.Exit: If the mirror or package manager is not found.
    """
    config = ChegiConfig(base_path=path)
    config.load()

    pm_name = pm_name.lower()

    if not hasattr(config, "mirrors") or pm_name not in config.mirrors:
        TerminalUI.print_error(f"No mirror configuration found for '{pm_name}'.")
        raise typer.Exit(code=1)

    success = config.remove_mirror(pm_name, url)

    if success:
        config.save()
        if url:
            TerminalUI.print_success(f"Removed mirror URL '{url}' for '{pm_name}'.")
        else:
            TerminalUI.print_success(f"Removed all mirror configurations for '{pm_name}'.")
    else:
        if url:
            TerminalUI.print_error(f"URL '{url}' not found in saved mirrors for '{pm_name}'.")
        else:
            TerminalUI.print_error(f"Failed to remove mirror configuration for '{pm_name}'.")
        raise typer.Exit(code=1)


@app.command("mirror-set-all")
def config_mirror_set_all(
    json_data: str = typer.Argument(
        ...,
        help='JSON string representing the full mirror dictionary (e.g., \'{"npm": "url", "pip": "url"}\')',
    ),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Overwrites the entire mirrors configuration with the provided JSON data.

    Args:
        json_data (str): A JSON formatted string containing package managers and URLs.
        path (str): Base directory for the configuration file.

    Raises:
        typer.Exit: If the JSON is malformed or validation fails.
    """
    config = ChegiConfig(base_path=path)
    config.load()

    try:
        # Parse incoming JSON payload
        new_mirrors = json.loads(json_data)

        # Validate basic structure
        if not isinstance(new_mirrors, dict):
            raise ValueError(
                "Data must be a valid JSON dictionary format (e.g., {...})."
            )

        # Ensure all keys are strings and values are strings or lists of strings
        for k, v in new_mirrors.items():
            if not isinstance(k, str) or not isinstance(v, (str, list)):
                raise ValueError(
                    f"All keys must be strings and values must be strings or lists. Invalid pair: '{k}': {v}"
                )

    except json.JSONDecodeError:
        TerminalUI.print_error(
            'Invalid JSON format! Please wrap the string properly (e.g. \'{"pip": "url"}\').'
        )
        raise typer.Exit(code=1)
    except ValueError as e:
        TerminalUI.print_error(f"Validation Error: {e}")
        raise typer.Exit(code=1)

    if not hasattr(config, "mirrors") or config.mirrors is None:
        config.mirrors = {}

    # Completely wipe existing mirrors and apply the new configuration
    config.mirrors.clear()
    try:
        config.update_setting("mirrors", new_mirrors)
        config.save()
    except ValueError as e:
        TerminalUI.print_error(f"Validation Error: {e}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]✔ Mirrors configuration has been completely overwritten with {len(new_mirrors)} items.[/green]"
    )


@app.command("mirror-clear")
def config_mirror_clear(
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Completely removes all stored mirror configurations permanently.

    Args:
        path (str): Base directory for the configuration file.
    """
    config = ChegiConfig(base_path=path)
    config.load()

    if hasattr(config, "mirrors") and config.mirrors:
        config.mirrors = {}
        config.save()
        console.print("[green]✔ All mirrors have been completely cleared.[/green]")
    else:
        console.print("[yellow]⚠ No mirrors were configured to clear.[/yellow]")
