"""Application-wide exception hierarchy.

All domain/application errors inherit from AppError so the API layer can
translate them into consistent HTTP responses via a single exception handler.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application-raised errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class ValidationAppError(AppError):
    status_code = 422
    error_code = "validation_error"


class UnsupportedFileTypeError(AppError):
    status_code = 415
    error_code = "unsupported_file_type"


class FileTooLargeError(AppError):
    status_code = 413
    error_code = "file_too_large"


class DocumentProcessingError(AppError):
    status_code = 422
    error_code = "document_processing_error"


class EmbeddingProviderError(AppError):
    status_code = 502
    error_code = "embedding_provider_error"


class LLMProviderError(AppError):
    status_code = 502
    error_code = "llm_provider_error"


class DocumentNotReadyError(AppError):
    """Raised when a query references a document still being processed."""

    status_code = 409
    error_code = "document_not_ready"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"
