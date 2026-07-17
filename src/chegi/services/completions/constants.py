"""Constants for the completions service."""

from pathlib import Path
from typing import Dict, List

from chegi.services.completions.models import SupportedShell

VALID_SHELLS: List[str] = [s.value for s in SupportedShell]

INSTALL_PATHS: Dict[str, Path] = {
    "bash": Path.home()
    / ".local"
    / "share"
    / "bash-completion"
    / "completions"
    / "chegi",
    "zsh": Path.home() / ".zfunc" / "_chegi",
    "fish": Path.home() / ".config" / "fish" / "completions" / "chegi.fish",
}

INSTALL_GUIDES: Dict[str, str] = {
    "bash": (
        "# Bash — source in ~/.bashrc or install globally:\n"
        "chegi completions bash > /etc/bash_completion.d/chegi"
    ),
    "zsh": (
        "# Zsh — place in a directory listed in $fpath:\n"
        "chegi completions zsh > /usr/local/share/zsh/site-functions/_chegi"
    ),
    "fish": (
        "# Fish — copy to completions directory:\n"
        "chegi completions fish > ~/.config/fish/completions/chegi.fish"
    ),
    "powershell": (
        "# PowerShell — add to your profile:\n"
        "chegi completions powershell | Out-String | Invoke-Expression"
    ),
    "pwsh": (
        "# PowerShell Core — same as powershell:\n"
        "chegi completions pwsh | Out-String | Invoke-Expression"
    ),
}
