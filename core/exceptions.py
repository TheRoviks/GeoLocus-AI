class BotError(Exception):
    """Base exception for the application."""


class AIParseError(BotError):
    """Raised when the AI service cannot confidently parse a reminder."""


class ReminderNotFoundError(BotError):
    """Raised when a reminder lookup fails."""


class InvalidRecurrenceError(BotError):
    """Raised when a recurrence rule cannot be parsed."""
