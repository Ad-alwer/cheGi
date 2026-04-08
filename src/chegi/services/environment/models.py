from dataclasses import dataclass
from typing import Dict, List, Optional, Union

@dataclass
class ToolConfig:
    command: str
    args: List[str]
    description: Optional[str] = None

@dataclass
class EnvironmentPreset:
    name: str
    description: str
    tools: Dict[str, ToolConfig]
    gitignore: Union[List[str], str]
