import json
import importlib.resources as pkg_resources
from typing import Dict, Optional, Any, List


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
            # Safely access the 'environments' directory within the 'chegi' package
            # pkg_resources.files returns a Traversable object similar to pathlib.Path
            package_dir = pkg_resources.files('chegi.environments')
            
            for file_item in package_dir.iterdir():
                if file_item.is_file() and file_item.name.endswith('.json'):
                    content = file_item.read_text(encoding='utf-8')
                    data = json.loads(content)
                    
                    lang_name = data.get("name")
                    if lang_name:
                        self.db[lang_name.lower()] = data
                        
        except Exception:
            # Silently pass if the directory is missing or JSON is invalid.
            # TODO: Implement proper logging for failure cases in the future.
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
