"""Tests for CommitStyleManager."""

import json
from pathlib import Path

from chegi.services.commit import CommitStyleManager

TEST_REPO = Path("/fake/repo")


def test_get_styles_includes_builtin():
    """Test get_styles returns built-in styles when no custom styles exist."""
    manager = CommitStyleManager(TEST_REPO)
    styles = manager.get_styles()
    names = [s.name for s in styles]
    assert "free" in names
    assert "conventional" in names
    assert "conventional-scope" in names
    assert "conventional-body" in names
    assert "gitmoji" in names
    assert len(styles) == 5


def test_get_last_style_none(tmp_path: Path):
    """Test get_last_style returns None when no prefs file exists."""
    manager = CommitStyleManager(TEST_REPO)
    assert manager.get_last_style() is None


def test_save_and_get_last_style(tmp_path: Path):
    """Test saving and retrieving the last used style."""
    manager = CommitStyleManager(TEST_REPO)
    manager.config_dir = tmp_path / ".config" / "chegi"
    manager.hints_dir = manager.config_dir / "hints"
    manager.prefs_file = manager.config_dir / "prefs.json"

    manager.save_last_style("conventional-scope")
    assert manager.get_last_style() == "conventional-scope"


def test_should_show_hint_returns_true_first_time():
    """Test should_show_hint returns True when hint has not been shown."""
    manager = CommitStyleManager(TEST_REPO)
    assert manager.should_show_hint("commit_brand") is True


def test_mark_and_check_hint(tmp_path: Path):
    """Test marking a hint as shown makes should_show_hint return False."""
    manager = CommitStyleManager(TEST_REPO)
    manager.config_dir = tmp_path / ".config" / "chegi"
    manager.hints_dir = manager.config_dir / "hints"
    manager.prefs_file = manager.config_dir / "prefs.json"

    manager.mark_hint_shown("test_hint")
    assert manager.should_show_hint("test_hint") is False


def test_different_hints_independent(tmp_path: Path):
    """Test that different hints are tracked independently."""
    manager = CommitStyleManager(TEST_REPO)
    manager.config_dir = tmp_path / ".config" / "chegi"
    manager.hints_dir = manager.config_dir / "hints"
    manager.prefs_file = manager.config_dir / "prefs.json"

    manager.mark_hint_shown("hint_a")
    assert manager.should_show_hint("hint_a") is False
    assert manager.should_show_hint("hint_b") is True


def test_load_custom_styles_not_exists():
    """Test _load_custom_styles returns empty list when file doesn't exist."""
    manager = CommitStyleManager(TEST_REPO)
    custom = manager._load_custom_styles()
    assert custom == []


def test_load_custom_styles_valid(tmp_path: Path):
    """Test loading valid custom styles from .chegi/commit-styles.json."""
    chegi_dir = tmp_path / ".chegi"
    chegi_dir.mkdir()
    styles_file = chegi_dir / "commit-styles.json"
    styles_file.write_text(
        json.dumps(
            {
                "styles": [
                    {
                        "name": "custom-v1",
                        "label": "Custom V1",
                        "description": "My custom style",
                        "fields": ["type", "description"],
                        "types": ["feat", "fix"],
                    }
                ]
            }
        )
    )
    manager = CommitStyleManager(tmp_path)
    custom = manager._load_custom_styles()
    assert len(custom) == 1
    assert custom[0].name == "custom-v1"
    assert custom[0].label == "Custom V1"
    assert custom[0].fields == ["type", "description"]
    assert custom[0].types == ["feat", "fix"]


def test_get_styles_includes_custom(tmp_path: Path):
    """Test get_styles includes both built-in and custom styles."""
    chegi_dir = tmp_path / ".chegi"
    chegi_dir.mkdir()
    styles_file = chegi_dir / "commit-styles.json"
    styles_file.write_text(
        json.dumps(
            {
                "styles": [
                    {
                        "name": "my-style",
                        "label": "My Style",
                        "description": "Custom",
                        "fields": ["description"],
                    }
                ]
            }
        )
    )
    manager = CommitStyleManager(tmp_path)
    styles = manager.get_styles()
    assert len(styles) == 6
    names = [s.name for s in styles]
    assert "my-style" in names
    assert "free" in names


def test_load_custom_styles_invalid_json(tmp_path: Path):
    """Test loading custom styles with invalid JSON returns empty list."""
    chegi_dir = tmp_path / ".chegi"
    chegi_dir.mkdir()
    styles_file = chegi_dir / "commit-styles.json"
    styles_file.write_text("not valid json")
    manager = CommitStyleManager(tmp_path)
    custom = manager._load_custom_styles()
    assert custom == []
