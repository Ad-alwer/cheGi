import json
import subprocess
import importlib.resources as pkg_resources
from pathlib import Path
from typing import Dict, Optional, Any, List

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
    """Manages development environments and their associated tools.

    This class acts as an in-memory database by dynamically loading JSON
    configuration files from the 'environments' package directory.

    Attributes:
        db (Dict[str, Dict[str, Any]]): In-memory storage containing all 
            loaded language configurations and tools.
    """

    def __init__(self) -> None:
        """Initializes the EnvManager and loads all environment data into memory."""
        self.db: Dict[str, Dict[str, Any]] = {}
        self.load_environments()

    def load_environments(self) -> None:
        """Scans and loads all JSON files from the 'environments' package.

        Uses `importlib.resources` to safely access data files regardless of
        how the package is installed (e.g., source, wheel, zip).
        """
        try:
            package_dir = pkg_resources.files('chegi.environments')
            
            for file_item in package_dir.iterdir():
                if file_item.is_file() and file_item.name.endswith('.json'):
                    content = file_item.read_text(encoding='utf-8')
                    data = json.loads(content)
                    
                    lang_name = data.get("name")
                    if lang_name:
                        self.db[lang_name.lower()] = data
                        
        except Exception:
            pass

    def get_language(self, lang_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves the complete configuration for a specific language.

        Args:
            lang_name (str): The name of the language (e.g., 'python', 'ruby').

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing levels and tools data,
                or None if the requested language is not found.
        """
        return self.db.get(lang_name.lower())

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Searches across all loaded languages for a specific tool.

        Args:
            tool_name (str): The name of the tool (e.g., 'pip', 'rspec').

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the tool's check 
                command and installation instructions, or None if not found.
        """
        tool_name = tool_name.lower()
        for lang_data in self.db.values():
            tools = lang_data.get("tools", {})
            if tool_name in tools:
                return tools[tool_name]
        return None

    def get_available_envs(self) -> List[str]:
        """Returns a list of all available and loaded environment names.
        
        This method is used by the CLI to validate user input against 
        supported environments.

        Returns:
            List[str]: A list of lowercase environment names (e.g., ['python', 'ruby']).
        """
        return list(self.db.keys())

    def get_env(self, lang_name: str) -> Optional[Dict[str, Any]]:
        """Alias for get_language to maintain compatibility with the CLI module.

        Args:
            lang_name (str): The name of the environment/language.

        Returns:
            Optional[Dict[str, Any]]: The environment configuration data.
        """
        return self.get_language(lang_name)

    def get_envs_with_gitignore(self) -> List[str]:
        """Retrieves all environments that have a gitignore template defined.

        Returns:
            List[str]: A list of environment names.
        """
        return [env_name for env_name, data in self.db.items() if data.get("gitignore")]

    def has_existing_gitignore(self, target_dir: str) -> bool:
        """Checks if a .gitignore file already exists in the target directory.

        Args:
            target_dir (str): The directory path to check.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        return (Path(target_dir).expanduser().resolve() / ".gitignore").exists()

    def generate_gitignore(self, env_names: List[str], target_dir: str = ".") -> Path:
        """Generates a combined .gitignore file for multiple environments.

        Filters out duplicate rules across different environments and global templates.

        Args:
            env_names (List[str]): List of environment names to include.
            target_dir (str, optional): Directory to save the file. Defaults to ".".

        Returns:
            Path: The absolute path to the generated .gitignore file.

        Raises:
            ValueError: If the env_names list is empty.
        """
        if not env_names:
            raise ValueError("No environments provided for gitignore generation.")

        combined_content = []
        seen_rules = set()

        names_formatted = ", ".join([name.capitalize() for name in env_names])
        combined_content.append(f"# .gitignore generated by Chegi for: {names_formatted}\n")

        for env_name in env_names:
            env_data = self.get_env(env_name)
            if not env_data:
                continue

            combined_content.append(f"\n# =========================\n# {env_name.capitalize()}\n# =========================")
            
            ignore_data = env_data.get("gitignore", [])
            # Handle JSON values that might be either a list of strings or a single multiline string
            template_lines = ignore_data if isinstance(ignore_data, list) else ignore_data.splitlines()

            for line in template_lines:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith('#'):
                    combined_content.append(line)
                elif stripped_line not in seen_rules:
                    seen_rules.add(stripped_line)
                    combined_content.append(line)

        combined_content.append("\n# =========================\n# Global (OS/IDE)\n# =========================")
        for line in GLOBAL_GITIGNORE_TEMPLATE.strip().splitlines():
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                combined_content.append(line)
            elif stripped_line not in seen_rules:
                seen_rules.add(stripped_line)
                combined_content.append(line)

        final_content = "\n".join(combined_content).strip() + "\n"
        
        target_path = Path(target_dir).expanduser().resolve() / ".gitignore"
        target_path.write_text(final_content, encoding="utf-8")
        
        return target_path

    def is_git_repo(self, target_dir: str) -> bool:
        """Checks if the given directory is part of a git repository.

        Args:
            target_dir (str): The directory path to check.

        Returns:
            bool: True if it is a git repository, False otherwise.
        """
        target_path = str(Path(target_dir).expanduser().resolve())
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"], 
                check=True, capture_output=True, cwd=target_path
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def commit_gitignore(self, target_dir: str) -> str:
        """Adds and commits the .gitignore file to the repository.

        Args:
            target_dir (str): The directory containing the .gitignore file.

        Returns:
            str: The commit message used.
        """
        target_path = str(Path(target_dir).expanduser().resolve())
        commit_msg = "chore(gitignore): auto add .gitignore via cheGi 🐆"
        
        subprocess.run(["git", "add", ".gitignore"], check=True, cwd=target_path)
        subprocess.run(["git", "commit", ".gitignore", "-m", commit_msg], check=True, cwd=target_path)
        
        return commit_msg
