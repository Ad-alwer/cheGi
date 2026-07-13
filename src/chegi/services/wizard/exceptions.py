"""Wizard-specific exceptions."""


class WizardError(Exception):
    """Base exception for wizard-related errors."""

    pass


class WizardAbortedError(WizardError):
    """Raised when the wizard is aborted by the user."""

    pass
