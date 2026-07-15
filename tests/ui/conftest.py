"""Shared fixtures for UI tests."""

from pathlib import Path
from unittest.mock import patch

import pytest

from chegi.ui.console import TerminalUI


@pytest.fixture(autouse=True)
def _reset_theme_and_config(tmp_path: Path):
    """Resets the TerminalUI theme cache and patches global config to a temp dir.

    Ensures each test starts with the default theme regardless of the
    real ~/.config/chegi/config.json on the host.
    """
    TerminalUI._current_theme = None
    config_file = tmp_path / "config.json"
    with patch("chegi.config.global_config.GLOBAL_CONFIG_FILE", config_file):
        yield
