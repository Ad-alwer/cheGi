import pytest

from chegi.ui.exceptions import TableRenderingError, ThemeConfigurationError, UIError


def test_ui_exceptions_inheritance():
    """Verify custom exceptions correctly inherit from the base UIError."""
    with pytest.raises(UIError):
        raise TableRenderingError("Failed to render the table")

    with pytest.raises(UIError):
        raise ThemeConfigurationError("Invalid theme parameters")


def test_exception_message_retention():
    """Ensure exception instances retain and return their custom messages."""
    error_msg = "Critical UI failure"
    exc = UIError(error_msg)

    assert str(exc) == error_msg
