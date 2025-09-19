"""
Custom exception classes and error handlers for the API.

Provides standardized error responses that match the OpenAPI specification.
"""

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Base class for all API exceptions with standardized error structure."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(APIError):
    """400 - Bad Request for validation errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error_code="validation_error",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class UnauthorizedError(APIError):
    """401 - Unauthorized for authentication failures."""

    def __init__(self, message: str = "Invalid or missing API key", details: dict[str, Any] | None = None):
        super().__init__(
            error_code="unauthorized",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class NotFoundError(APIError):
    """404 - Not Found for missing resources."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error_code="not_found",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class PayloadTooLargeError(APIError):
    """413 - Payload Too Large for file size exceeding limits."""

    def __init__(self, message: str = "Request payload exceeds maximum allowed size", details: dict[str, Any] | None = None):
        super().__init__(
            error_code="payload_too_large",
            message=message,
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            details=details
        )


class UnsupportedMediaTypeError(APIError):
    """415 - Unsupported Media Type for invalid file types."""

    def __init__(self, message: str = "Unsupported media type", details: dict[str, Any] | None = None):
        super().__init__(
            error_code="unsupported_media_type",
            message=message,
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            details=details
        )


class UnprocessableEntityError(APIError):
    """422 - Unprocessable Entity for semantic validation errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error_code="unprocessable_entity",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=details
        )


class QuotaExceededError(APIError):
    """429 - Too Many Requests for quota/rate limit violations."""

    def __init__(self, message: str = "Account quota exceeded", details: dict[str, Any] | None = None):
        super().__init__(
            error_code="quota_exceeded",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


class SystemError(APIError):
    """500 - Internal Server Error for system failures."""

    def __init__(self, message: str = "An internal server error occurred", details: dict[str, Any] | None = None):
        super().__init__(
            error_code="system_error",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


# Legacy exception for backward compatibility
class MetricsAuthenticationError(UnauthorizedError):
    """Legacy exception for metrics endpoint authentication failures."""

    def __init__(self, error_code: str, message: str):
        # Map to new structure
        super().__init__(message=message, details={"legacy_code": error_code})


def create_error_response(request: Request, error: APIError) -> JSONResponse:
    """Create standardized error response with proper content type."""
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.error_code,
                "message": error.message,
                "details": error.details,
                "request_id": getattr(request.state, "request_id", "unknown"),
            }
        },
        headers={"Content-Type": "application/json; charset=utf-8"}
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle all APIError exceptions with standardized response format."""
    return create_error_response(request, exc)


async def metrics_auth_error_handler(request: Request, exc: MetricsAuthenticationError) -> JSONResponse:
    """Handle legacy MetricsAuthenticationError with proper error response format."""
    return create_error_response(request, exc)

