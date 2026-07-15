"""Tests for the theme preset module."""

from chegi.ui.themes import THEMES, ChegiTheme, get_theme, list_themes


def test_themes_has_all_keys():
    """Test that THEMES contains all expected presets."""
    for name in ("default", "dark", "hacker", "solarized", "nord"):
        assert name in THEMES


def test_get_theme_returns_theme():
    """Test that get_theme returns the correct theme by name."""
    theme = get_theme("hacker")
    assert isinstance(theme, ChegiTheme)
    assert theme.name == "hacker"
    assert theme.label == "Hacker"


def test_get_theme_fallback_to_default():
    """Test that get_theme returns default for unknown names."""
    theme = get_theme("nonexistent")
    assert theme.name == "default"


def test_list_themes_returns_dict():
    """Test that list_themes returns name -> label mapping."""
    result = list_themes()
    assert "default" in result
    assert "hacker" in result
    assert result["default"] == "Default"
    assert result["hacker"] == "Hacker"


def test_theme_has_all_styles():
    """Test that every theme has all required style attributes."""
    for theme in THEMES.values():
        assert theme.success
        assert theme.error
        assert theme.warning
        assert theme.info
        assert theme.neutral
        assert theme.table is not None
