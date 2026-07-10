"""
Custom exceptions for the UI module.
"""


class UIError(Exception):
    """
    Base exception for all UI-related errors in cheGi.
    """

    pass


class TableRenderingError(UIError):
    """
    Raised when there is an error rendering a table.

    This can happen if the provided data structure does not match
    the expected format for the table columns.
    """

    pass


class ThemeConfigurationError(UIError):
    """
    Raised when there is an invalid theme configuration provided.

    For example, using an invalid Rich style string for colors or borders.
    """

    pass
