"""Data models for the completions service."""

from enum import Enum


class SupportedShell(str, Enum):
    """Shell types supported for tab completion."""

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    POWERSHELL = "powershell"
    PWSH = "pwsh"
