from chegi.ui.models import MessageType, TableTheme


def test_message_type_values():
    """Ensure Enum values match their Rich text styles."""
    assert MessageType.SUCCESS.value == "bold green"
    assert MessageType.ERROR.value == "bold red"
    assert MessageType.WARNING.value == "bold yellow"
    assert MessageType.INFO.value == "bold blue"
    assert MessageType.NEUTRAL.value == "white"


def test_table_theme_defaults():
    """Verify default styling configurations for TableTheme."""
    theme = TableTheme()

    assert theme.header_style == "bold cyan"
    assert theme.border_style == "blue"
    assert theme.show_lines is True
