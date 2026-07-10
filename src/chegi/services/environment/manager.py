import importlib.resources as pkg_resources
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from .exceptions import NoEnvironmentsProvidedError
from .models import EnvironmentPreset, ToolConfig


class _Py38FileResource:
    """Compatibility wrapper around importlib.resources for Python 3.8."""

    def __init__(self, name: str, package: str) -> None:
        self.name = name
        self._package = package

    def is_file(self) -> bool:
        return self.name.endswith(".json")

    def read_text(self, encoding: str = "utf-8") -> str:
        return pkg_resources.read_text(self._package, self.name, encoding=encoding)


GLOBAL_GITIGNORE_TEMPLATE = """
# macOS
.DS_Store
.AppleDouble
.LSOverride

# Windows
Thumbs.db
ehthumbs.db
Desktop.ini

# IDEs and Editors
.idea/
.vscode/
*.swp
*.swo
*~
*.sublime-workspace
*.sublime-project

# Logs and databases
*.log
*.sql
*.sqlite

# Environment variables
.env
.env.local
.env.*.local
"""


class EnvManager:
    """Manages development environments and tools configurations in-memory.

    Attributes:
        db (Dict[str, EnvironmentPreset]): In-memory storage for environment presets.
    """

    def __init__(self) -> None:
        """Initializes the EnvManager and loads environment presets."""
        self.db: Dict[str, EnvironmentPreset] = {}
        self.load_environments()

    def _get_preset_files(self):
        """Iterate JSON preset files with Python 3.8+ compatibility."""
        try:
            package_dir = pkg_resources.files("chegi.services.environment.presets")
            return list(package_dir.iterdir())
        except AttributeError:
            pass

        # Python 3.8 fallback — importlib.resources.files() does not exist
        files = []
        for name in pkg_resources.contents("chegi.services.environment.presets"):
            files.append(_Py38FileResource(name, "chegi.services.environment.presets"))
        return files

    def load_environments(self) -> None:
        """Loads all JSON environment presets from the package resources.

        Reads `.json` files from the presets directory and populates the database.
        Skips unreadable or malformed files without failing the whole load.
        If the presets directory does not exist, the database stays empty.
        """
        try:
            items = self._get_preset_files()
        except (FileNotFoundError, ModuleNotFoundError):
            return

        for file_item in items:
            if not (file_item.is_file() and file_item.name.endswith(".json")):
                continue

            try:
                content = file_item.read_text(encoding="utf-8")
                data = json.loads(content)

                lang_name = data.get("name")
                if not lang_name:
                    continue

                raw_tools = data.get("tools", {})
                tools_dict = {
                    t_name: ToolConfig(
                        command=t_data.get("command", ""),
                        args=t_data.get("args", []),
                        description=t_data.get("description"),
                    )
                    for t_name, t_data in raw_tools.items()
                }

                self.db[lang_name.lower()] = EnvironmentPreset(
                    name=lang_name,
                    description=data.get("description", ""),
                    tools=tools_dict,
                    gitignore=data.get("gitignore", []),
                    levels=data.get("levels", {}),
                    levels_info=data.get("levels_info", {}),
                    raw_tools=raw_tools,
                )
            except (json.JSONDecodeError, OSError):
                continue

    def get_language(self, lang_name: str) -> Optional[EnvironmentPreset]:
        """Retrieves the configuration preset for a specific language.

        Args:
            lang_name (str): The name of the language to retrieve.

        Returns:
            Optional[EnvironmentPreset]: The environment preset if found, otherwise None.
        """
        return self.db.get(lang_name.lower())

    def get_tool(self, tool_name: str) -> Optional[ToolConfig]:
        """Searches across all loaded languages for a specific tool.

        Args:
            tool_name (str): The name of the tool to search for.

        Returns:
            Optional[ToolConfig]: The tool configuration if found, otherwise None.
        """
        tool_name = tool_name.lower()
        for preset in self.db.values():
            if tool_name in preset.tools:
                return preset.tools[tool_name]
        return None

    def get_available_envs(self) -> List[str]:
        """Gets a list of all available and loaded environment names.

        Returns:
            List[str]: A list containing the names of all loaded environments.
        """
        return list(self.db.keys())

    def get_required_package_managers(self, env_names: List[str]) -> Set[str]:
        """Extracts a unique set of required package managers for given environments.

        Args:
            env_names (List[str]): A list of environment names to check.

        Returns:
            Set[str]: A set of unique package manager/tool names.
        """
        required_pms: Set[str] = set()
        for env_name in env_names:
            preset = self.get_env(env_name)
            if preset and preset.tools:
                required_pms.update(tool.lower() for tool in preset.tools)
        return required_pms

    def get_env(self, lang_name: str) -> Optional[EnvironmentPreset]:
        """Alias for get_language to maintain backward compatibility.

        Args:
            lang_name (str): The name of the language to retrieve.

        Returns:
            Optional[EnvironmentPreset]: The environment preset if found, otherwise None.
        """
        return self.get_language(lang_name)

    def get_envs_with_gitignore(self) -> List[str]:
        """Retrieves all environments that have a gitignore template defined.

        Returns:
            List[str]: A list of environment names that include gitignore rules.
        """
        return [name for name, preset in self.db.items() if preset.gitignore]

    def has_existing_gitignore(self, target_dir: str) -> bool:
        """Checks if a .gitignore file already exists in the target directory.

        Args:
            target_dir (str): The directory path to check.

        Returns:
            bool: True if .gitignore exists, False otherwise.
        """
        return (Path(target_dir).expanduser().resolve() / ".gitignore").exists()

    def generate_gitignore(self, env_names: List[str], target_dir: str = ".") -> Path:
        """Generates and writes a combined .gitignore file for given environments.

        Args:
            env_names (List[str]): List of environments to include in the .gitignore.
            target_dir (str, optional): The directory where the file will be saved. Defaults to ".".

        Returns:
            Path: The absolute path to the generated .gitignore file.

        Raises:
            NoEnvironmentsProvidedError: If the env_names list is empty.
        """
        if not env_names:
            raise NoEnvironmentsProvidedError(
                "No environments provided for gitignore generation."
            )

        combined_content = []
        seen_rules = set()

        names_formatted = ", ".join([name.capitalize() for name in env_names])
        combined_content.append(
            f"# .gitignore generated by Chegi for: {names_formatted}\n"
        )

        for env_name in env_names:
            preset = self.get_env(env_name)
            if not preset:
                continue

            combined_content.append(
                f"\n# =========================\n# {preset.name.capitalize()}\n# ========================="
            )

            ignore_data = preset.gitignore
            template_lines = (
                ignore_data
                if isinstance(ignore_data, list)
                else ignore_data.splitlines()
            )

            for line in template_lines:
                stripped_line = line.strip()
                if (
                    not stripped_line
                    or stripped_line.startswith("#")
                    or stripped_line not in seen_rules
                ):
                    if stripped_line and not stripped_line.startswith("#"):
                        seen_rules.add(stripped_line)
                    combined_content.append(line)

        combined_content.append(
            "\n# =========================\n# Global (OS/IDE)\n# ========================="
        )
        for line in GLOBAL_GITIGNORE_TEMPLATE.strip().splitlines():
            stripped_line = line.strip()
            if (
                not stripped_line
                or stripped_line.startswith("#")
                or stripped_line not in seen_rules
            ):
                if stripped_line and not stripped_line.startswith("#"):
                    seen_rules.add(stripped_line)
                combined_content.append(line)

        final_content = "\n".join(combined_content).strip() + "\n"
        target_path = Path(target_dir).expanduser().resolve() / ".gitignore"
        target_path.write_text(final_content, encoding="utf-8")

        return target_path

    def find_setup_target(self, target_name: str) -> Optional[EnvironmentPreset]:
        """Finds an environment preset or wraps a standalone tool in a preset.

        Args:
            target_name (str): The name of the environment or tool to find.

        Returns:
            Optional[EnvironmentPreset]: The preset for the environment or dynamically
                created preset for a standalone tool. Returns None if not found.
        """
        preset = self.get_env(target_name)
        if preset:
            return preset

        tool_data = self.get_tool(target_name)
        if tool_data:
            raw = {}
            for p in self.db.values():
                if target_name.lower() in p.raw_tools:
                    raw = p.raw_tools[target_name.lower()]
                    break
            if not raw:
                raw = {"command": tool_data.command}
            return EnvironmentPreset(
                name=tool_data.description or target_name.capitalize(),
                description=f"Standalone tool: {target_name.capitalize()}",
                tools={target_name.lower(): tool_data},
                gitignore=[],
                raw_tools={target_name.lower(): raw},
            )

        return None
