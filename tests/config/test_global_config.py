"""Tests for GlobalConfig."""

import json
from pathlib import Path
from unittest.mock import patch

from chegi.config.global_config import DEFAULT_THEME, GlobalConfig


def test_global_config_default_theme_when_no_file(tmp_path: Path):
    """Test that GlobalConfig defaults to default theme when no file exists."""
    config_file = tmp_path / "config.json"
    with patch("chegi.config.global_config.GLOBAL_CONFIG_FILE", config_file):
        cfg = GlobalConfig()
        assert cfg.theme == DEFAULT_THEME
        assert cfg.get("theme") == DEFAULT_THEME


def test_global_config_loads_from_file(tmp_path: Path):
    """Test that GlobalConfig reads theme from existing file."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"theme": "hacker"}))

    with patch("chegi.config.global_config.GLOBAL_CONFIG_FILE", config_file):
        cfg = GlobalConfig()
        assert cfg.theme == "hacker"


def test_global_config_sets_theme(tmp_path: Path):
    """Test that GlobalConfig.set changes theme and persists."""
    config_file = tmp_path / "config.json"
    with patch("chegi.config.global_config.GLOBAL_CONFIG_FILE", config_file):
        cfg = GlobalConfig()
        cfg.theme = "nord"
        assert cfg.theme == "nord"

        cfg2 = GlobalConfig()
        assert cfg2.theme == "nord"


def test_global_config_set_saves_to_disk(tmp_path: Path):
    """Test that setting theme writes to the config file."""
    config_file = tmp_path / "config.json"
    with patch("chegi.config.global_config.GLOBAL_CONFIG_FILE", config_file):
        cfg = GlobalConfig()
        cfg.set("theme", "dark")
        assert config_file.is_file()
        data = json.loads(config_file.read_text())
        assert data["theme"] == "dark"


def test_global_config_get_with_default(tmp_path: Path):
    """Test that get returns the default when key is missing."""
    config_file = tmp_path / "config.json"
    with patch("chegi.config.global_config.GLOBAL_CONFIG_FILE", config_file):
        cfg = GlobalConfig()
        assert cfg.get("nonexistent", "fallback") == "fallback"
