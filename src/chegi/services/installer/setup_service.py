"""Setup Service module.

Encapsulates the business logic for setting up environments and installing tools.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

import questionary
import typer
from rich.table import Table

from chegi.config import SUPPORTED_PMS, ChegiConfig
from chegi.services.environment import EnvManager
from chegi.services.environment.models import EnvironmentPreset
from chegi.ui import TerminalUI, console

from .exceptions import UserAbortedSetupError
from .system_installer import SystemInstaller


class SetupService:
    """Service class to handle the setup and installation workflow.

    Attributes:
        environment (str): The target programming language or toolset.
        auto_yes (bool): Flag to skip prompts and automatically accept.
        env_manager (EnvManager): Manager for parsing environment definitions.
        config (ChegiConfig): Configuration instance for managing settings/mirrors.
        env_data (Dict[str, Any]): Data of the resolved target environment.
        display_name (str): Capitalized or custom display name for the target.
        pkg_manager (str): Detected OS-level package manager (e.g., apt, brew).
        installed_tools (Set[str]): Tracks tools already installed during session.
    """

    def __init__(self, environment: str, auto_yes: bool) -> None:
        """Initializes the SetupService with necessary configurations.

        Args:
            environment (str): The name of the environment or tool to install.
            auto_yes (bool): If True, answers 'yes' to all prompts automatically.
        """
        self.environment = environment.lower()
        self.auto_yes = auto_yes

        # Initialize core components
        self.env_manager = EnvManager()
        self.config = ChegiConfig()

        # State variables
        self.env_data: Optional[EnvironmentPreset] = None
        self.display_name: str = ""
        self.pkg_manager: str = SystemInstaller.get_os_package_manager()
        self.installed_tools: Set[str] = set()

    def execute(self) -> None:
        """Runs the complete setup workflow.

        Executes the 7-step process: resolving target, normalizing data,
        checking status, sorting dependencies, asking user for selection,
        configuring mirrors, and executing the installation.

        Raises:
            typer.Exit: If target is not supported, or user aborts the process.
        """
        # 1. Resolve Target
        self._resolve_target()
        TerminalUI.print_info(
            f"Analyzing environment for: [bold yellow]{self.display_name}[/bold yellow]"
        )
        console.print(
            f"Detected Package Manager: [bold cyan]{self.pkg_manager}[/bold cyan]\n"
        )

        # 2. Normalize Data
        levels, levels_info, tools_data = self._normalize_data()

        # 3. Check Status
        tools_to_install = self._check_installed_tools(levels, levels_info, tools_data)

        if not tools_to_install:
            TerminalUI.print_success(
                f"All critical tools for {self.display_name} are already installed! 🎉"
            )
            raise typer.Exit()

        # 4. Sort Dependencies
        tools_to_install = self._sort_dependencies(tools_to_install)
        TerminalUI.print_info(f"Found {len(tools_to_install)} missing tools.")

        # 5. User Selection
        tools_to_install = self._prompt_user_selection(tools_to_install)

        # 6. Mirror Configuration
        session_mirrors = self._configure_mirrors(tools_to_install)

        # 7. Execute Installations
        self._execute_installations(tools_to_install, session_mirrors)

    def _resolve_target(self) -> None:
        """Finds the target tool or environment.

        Raises:
            typer.Exit: If the target environment cannot be found.
        """
        preset = self.env_manager.find_setup_target(self.environment)
        if not preset:
            available_envs = self.env_manager.get_available_envs()
            TerminalUI.print_error(f"Target '{self.environment}' is not supported.")
            TerminalUI.print_info(
                f"Available environments: {', '.join(available_envs)}"
            )
            raise typer.Exit(code=1)

        self.env_data = preset
        self.display_name = preset.name or self.environment.capitalize()

    def _normalize_data(
        self,
    ) -> Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, Any]]:
        """Normalizes data for both standalone tools and full environments.

        Returns:
            Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, Any]]: A tuple containing:
                - levels: Dictionary grouping tools by their installation levels.
                - levels_info: Dictionary providing names/descriptions for each level.
                - tools_data: Dictionary mapping tool names to their properties.
        """
        if self.env_data is None:
            return {}, {}, {}

        levels = self.env_data.levels
        levels_info = self.env_data.levels_info
        raw_tools = self.env_data.raw_tools

        if not levels or not raw_tools:
            levels = {"standalone": [self.environment]}
            levels_info = {"standalone": "Standalone App"}
            if raw_tools:
                tools_data = dict(raw_tools)
            else:
                tools_data = {self.environment: {}}
        else:
            tools_data = dict(raw_tools)

        return levels, levels_info, tools_data

    def _check_installed_tools(
        self, levels: Dict, levels_info: Dict, tools_data: Dict
    ) -> List[Dict[str, Any]]:
        """Checks the status of required tools and prints a status table.

        Args:
            levels (Dict): Groups of tool names by level.
            levels_info (Dict): Mapping of level IDs to descriptive names.
            tools_data (Dict): Data and configurations for each tool.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing tools
            that need to be installed.
        """
        table = Table(
            title=f"{self.display_name} Status",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Tool", style="cyan", no_wrap=True)
        table.add_column("Requires", style="dim")
        table.add_column("Level", style="blue")
        table.add_column("Status", justify="center")
        table.add_column("Version/Info", style="dim")

        tools_to_install = []

        with console.status(
            "[bold green]Checking installed tools...[/bold green]", spinner="dots"
        ):
            for level_id, tool_names in levels.items():
                level_name = levels_info.get(level_id, f"Level {level_id}")

                for t_name in tool_names:
                    tool_info = tools_data.get(t_name)
                    if not tool_info:
                        continue

                    check_cmd = (
                        tool_info.get("check_command")
                        or tool_info.get("check_cmd")
                        or f"{t_name} --version"
                    )
                    requires_list = tool_info.get("requires", [])
                    requires_str = ", ".join(requires_list) if requires_list else "-"
                    is_gui_app = bool(tool_info.get("is_gui", False))

                    is_installed, info = SystemInstaller.is_tool_installed(
                        check_cmd, is_gui=is_gui_app
                    )

                    if is_installed:
                        self.installed_tools.add(t_name)
                        status_str = "[bold green]✔ Installed[/bold green]"
                        if is_gui_app and not info:
                            info = "GUI Tool"
                    else:
                        status_str = "[bold red]✖ Missing[/bold red]"
                        cmd_to_run = SystemInstaller.get_install_command(
                            tool_info, self.pkg_manager
                        )

                        if cmd_to_run:
                            tools_to_install.append(
                                {
                                    "name": t_name,
                                    "level": level_name,
                                    "cmd": cmd_to_run,
                                    "requires": requires_list,
                                }
                            )
                        else:
                            status_str = "[bold yellow]⚠ Manual[/bold yellow]"

                    table.add_row(t_name, requires_str, level_name, status_str, info)

        console.print(table)
        console.print("\n")
        return tools_to_install

    def _sort_dependencies(
        self, tools_to_install: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Sorts tools based on their dependencies.

        Ensures that dependencies are installed before the tools that require them.

        Args:
            tools_to_install (List[Dict[str, Any]]): Unsorted list of tools to install.

        Returns:
            List[Dict[str, Any]]: Dependency-sorted list of tools.
        """
        sorted_tools = []
        remaining = tools_to_install.copy()

        while remaining:
            progress = False
            for tool in remaining:
                pending_deps = [
                    dep
                    for dep in tool.get("requires", [])
                    if any(t["name"] == dep for t in remaining)
                ]
                if not pending_deps:
                    sorted_tools.append(tool)
                    remaining.remove(tool)
                    progress = True
                    break

            if not progress:
                sorted_tools.extend(remaining)
                break

        return sorted_tools

    def _prompt_user_selection(
        self, tools_to_install: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prompts the user to select which tools to install.

        Args:
            tools_to_install (List[Dict[str, Any]]): List of tools pending installation.

        Returns:
            List[Dict[str, Any]]: The final list of tools selected by the user.

        Raises:
            typer.Exit: If the user cancels the prompt or selects no tools.
        """
        if self.auto_yes or not tools_to_install:
            return tools_to_install

        is_single_standalone = (
            len(tools_to_install) == 1
            and tools_to_install[0]["level"] == "Standalone App"
        )

        if is_single_standalone:
            if not typer.confirm(
                f"Do you want to install '{tools_to_install[0]['name']}'?"
            ):
                TerminalUI.print_info("Setup aborted by user. No changes were made.")
                raise typer.Exit()
            return tools_to_install

        choices = [
            questionary.Choice(
                title=f"{t['name']} ({t['level']})"
                + (f" [Requires: {', '.join(t['requires'])}]" if t["requires"] else ""),
                value=t,
                checked=True,
            )
            for t in tools_to_install
        ]

        selected = questionary.checkbox(
            "Select the tools you want to install (Space to toggle, Enter to confirm):",
            choices=choices,
        ).ask()

        if not selected:
            TerminalUI.print_info("Setup aborted by user or no tools selected.")
            raise typer.Exit()

        return selected

    def _configure_mirrors(
        self, tools_to_install: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Configures optional package manager mirrors.

        Args:
            tools_to_install (List[Dict[str, Any]]): Tools selected for installation.

        Returns:
            Dict[str, str]: A dictionary mapping package managers to their mirror URLs.
        """
        session_mirrors = {}
        active_pms = {tool["cmd"].split()[0].lower() for tool in tools_to_install}

        if self.environment in self.env_manager.get_available_envs():
            required_pms = self.env_manager.get_required_package_managers(
                [self.environment]
            )
        else:
            required_pms = active_pms.copy()

        pms_to_ask = required_pms.intersection(SUPPORTED_PMS).intersection(active_pms)

        if not pms_to_ask:
            return session_mirrors

        console.print(
            "\n[bold cyan]🪞 Mirror / Registry Configuration (Optional)[/bold cyan]"
        )
        console.print("[dim]Useful if you are behind a restricted network.[/dim]")

        for pm in list(pms_to_ask):
            saved_mirrors = (
                self.config.get_mirror(pm)
                if hasattr(self.config, "get_mirror")
                else None
            )

            if saved_mirrors:
                mirror_list = (
                    saved_mirrors
                    if isinstance(saved_mirrors, list)
                    else [saved_mirrors]
                )
                if self.auto_yes:
                    session_mirrors[pm] = mirror_list[0]
                    console.print(
                        f"[dim]Auto-using primary mirror for {pm}: {mirror_list[0]}[/dim]"
                    )
                    continue

                choices = [
                    questionary.Choice(f"✅ Use: {url}", value=url)
                    for url in mirror_list
                ]
                choices.extend(
                    [
                        questionary.Choice("✏️  Use a different mirror", value="new"),
                        questionary.Choice("❌ Do NOT use a mirror", value="none"),
                    ]
                )

                choice = questionary.select(
                    f"Configured mirror(s) for '{pm}'. Select one:", choices=choices
                ).ask()
                if choice is None:
                    raise typer.Exit(code=1)
                elif choice == "new":
                    new_url = questionary.text(
                        f"Enter new mirror URL for {pm}:", default=mirror_list[0]
                    ).ask()
                    if new_url and new_url.strip():
                        session_mirrors[pm] = new_url.strip()
                        if new_url.strip() not in mirror_list and typer.confirm(
                            f"Save URL permanently for {pm}?", default=False
                        ):
                            self.config.set_mirror(pm, session_mirrors[pm])
                            self.config.save()
                elif choice != "none":
                    session_mirrors[pm] = choice
            else:
                if not self.auto_yes and typer.confirm(
                    f"Use a mirror for '{pm}'?", default=False
                ):
                    mirror_url = questionary.text(f"Enter mirror URL for {pm}:").ask()
                    if mirror_url and mirror_url.strip():
                        session_mirrors[pm] = mirror_url.strip()
                        if typer.confirm("Save permanently?", default=True):
                            self.config.set_mirror(pm, session_mirrors[pm])
                            self.config.save()

        return session_mirrors

    def _execute_installations(
        self, tools_to_install: List[Dict[str, Any]], session_mirrors: Dict[str, str]
    ) -> None:
        """Executes the installation commands for selected tools.

        Args:
            tools_to_install (List[Dict[str, Any]]): Final sorted list of tools.
            session_mirrors (Dict[str, str]): Configured mirrors to pass to installer.

        Raises:
            typer.Exit: If the process is interrupted via Ctrl+C.
        """
        success_count = 0
        skipped_count = 0

        try:
            for tool in tools_to_install:
                missing_deps = [
                    dep
                    for dep in tool.get("requires", [])
                    if dep not in self.installed_tools
                ]
                if missing_deps:
                    TerminalUI.print_warning(
                        f"⏭️  Skipping {tool['name']}: Missing prerequisites ({', '.join(missing_deps)})"
                    )
                    skipped_count += 1
                    continue

                console.print(
                    f"\n[bold blue]▶ Installing {tool['name']} ({tool['level']})...[/bold blue]"
                )
                pm_name = tool["cmd"].split()[0].lower()
                mirror_url = session_mirrors.get(pm_name)

                success = SystemInstaller.run_custom_command(
                    tool["cmd"],
                    pm_name=pm_name if mirror_url else None,
                    mirror_url=mirror_url,
                )

                if success:
                    if len(tools_to_install) > 1:
                        console.print(
                            f"[bold green]✅ {tool['name']} installed successfully.[/bold green]"
                        )
                    self.installed_tools.add(tool["name"])
                    success_count += 1
                else:
                    TerminalUI.print_error(f"❌ Failed to install {tool['name']}.")

        except (KeyboardInterrupt, UserAbortedSetupError):
            console.print(
                "\n[bold red]❌ Installation interrupted by user (Ctrl+C).[/bold red]"
            )
            raise typer.Exit(code=1)

        # Final Output
        console.print("\n")
        if success_count == len(tools_to_install) and success_count > 0:
            if len(tools_to_install) == 1:
                TerminalUI.print_success(
                    f"✨ {tools_to_install[0]['name']} installed successfully! ✨"
                )
            else:
                TerminalUI.print_success(
                    f"✨ Setup for {self.display_name} completed successfully! ✨"
                )
        else:
            TerminalUI.print_info(
                f"Setup finished. Installed: {success_count}, Skipped: {skipped_count}, Failed/Canceled: {len(tools_to_install) - success_count - skipped_count}."
            )
