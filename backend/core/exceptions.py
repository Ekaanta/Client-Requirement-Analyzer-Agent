class AppBaseException(Exception):
    """Base exception for the application."""
    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class FigmaError(AppBaseException):
    """Raised when Figma API interaction fails."""


class GrokError(AppBaseException):
    """Raised when Grok AI API fails."""


class N8NError(AppBaseException):
    """Raised when n8n webhook fails."""


class ValidationError(AppBaseException):
    """Raised on invalid request input."""
