"""Application-specific exceptions for AML Investigation Copilot."""


class AMLCopilotError(Exception):
    """Base exception class for AML Copilot errors."""


class PDFExtractionError(AMLCopilotError):
    """Base exception for PDF extraction and processing failures."""


class PDFNotFoundError(PDFExtractionError):
    """Raised when the specified PDF file cannot be found."""


class PDFInvalidFormatError(PDFExtractionError):
    """Raised when a file is not a valid or readable PDF document."""


class TransactionParsingError(AMLCopilotError):
    """Raised when parsing transactions from raw extracted document fails."""


class TransactionValidationError(AMLCopilotError):
    """Raised when a parsed transaction fails domain validation invariants."""


class ToolExecutionError(AMLCopilotError):
    """Raised when an investigation tool encounters an unrecoverable runtime error."""


class AgentConfigurationError(AMLCopilotError):
    """Raised when the investigation agent is misconfigured or lacks required LLM credentials."""

