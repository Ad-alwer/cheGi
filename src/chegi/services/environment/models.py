from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

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
    levels: Dict[str, List[str]] = field(default_factory=dict)
    levels_info: Dict[str, str] = field(default_factory=dict)
    raw_tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
