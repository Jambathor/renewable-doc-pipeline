"""
FastAPI dependencies for request validation and processing.

Provides reusable dependencies for common validation patterns.
"""

import json
import uuid
from typing import Any

from fastapi import Depends, File, Form, Header, Path, Query, UploadFile

from .errors import (
    PayloadTooLargeError,
    QuotaExceededError,
    UnauthorizedError,
    UnprocessableEntityError,
    UnsupportedMediaTypeError,
    ValidationError,
)


def validate_uuid(uuid_str: str, field_name: str) -> str:
    """
    Validate UUID format and return the string if valid.

    Args:
        uuid_str: The UUID string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated UUID string

    Raises:
        ValidationError: If UUID format is invalid
    """
    try:
        # This will raise ValueError if not a valid UUID
        uuid.UUID(uuid_str)
        return uuid_str
    except ValueError as e:
        raise ValidationError(
            message=f"Invalid UUID format for {field_name}",
            details={"field": field_name, "value": uuid_str, "expected": "UUID format"}
        ) from e


def validate_document_id(
    document_id: str = Path(..., description="Unique document identifier")
) -> str:
    """Validate document_id path parameter."""
    return validate_uuid(document_id, "document_id")


def validate_job_id(
    job_id: str = Path(..., description="Unique job identifier")
) -> str:
    """Validate job_id path parameter."""
    return validate_uuid(job_id, "job_id")


def validate_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """
    Validate API key from X-API-Key header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        UnauthorizedError: If API key is missing or invalid
    """
    if not x_api_key:
        raise UnauthorizedError(
            message="Missing API key in X-API-Key header",
            details={"header": "X-API-Key", "required": True}
        )

    # Valid API keys for demo purposes (same as existing routes)
    valid_api_keys = [
        "test-api-key",
        "test-api-key-123",
        "test-api-key-12345",
        "valid-api-key-12345"
    ]

    if x_api_key not in valid_api_keys:
        raise UnauthorizedError(
            message="Invalid API key",
            details={"header": "X-API-Key", "valid_format": "registered API key"}
        )

    return x_api_key


class Account:
    """Mock account structure for demo purposes."""

    def __init__(self, api_key: str):
        from uuid import uuid4
        self.api_key = api_key
        self.account_id = uuid4()  # Generate UUID for account_id
        self.documents_uploaded = 0  # Would be tracked in real implementation
        self.max_documents = 200


def get_current_account(api_key: str = Depends(validate_api_key)) -> Account:
    """
    Get current account based on validated API key.

    Args:
        api_key: Validated API key from dependency

    Returns:
        Account object for the authenticated user
    """
    return Account(api_key)


def validate_search_query(
    query: str = Query(..., min_length=1, max_length=500, description="Search query (1-500 characters)")
) -> str:
    """
    Validate search query parameter.

    Args:
        query: Search query string

    Returns:
        The validated query string

    Raises:
        ValidationError: If query is empty or too long
    """
    if not query or not query.strip():
        raise ValidationError(
            message="Search query cannot be empty",
            details={"parameter": "query", "min_length": 1, "max_length": 500}
        )

    if len(query) > 500:
        raise ValidationError(
            message="Search query exceeds maximum length of 500 characters",
            details={"parameter": "query", "length": len(query), "max_length": 500}
        )

    return query.strip()


def validate_optional_uuid_header(
    idempotency_key: str | None = Header(None, alias="Idempotency-Key")
) -> str | None:
    """
    Validate optional Idempotency-Key header as UUID.

    Args:
        idempotency_key: Optional UUID from Idempotency-Key header

    Returns:
        The validated UUID string or None

    Raises:
        ValidationError: If provided but not a valid UUID
    """
    if idempotency_key is None:
        return None

    return validate_uuid(idempotency_key, "Idempotency-Key")


def validate_pdf_file(file: UploadFile = File(...)) -> UploadFile:
    """
    Validate uploaded PDF file for size, type, and basic structure.

    Args:
        file: Uploaded file from FastAPI

    Returns:
        The validated UploadFile object

    Raises:
        PayloadTooLargeError: If file exceeds size limit
        UnsupportedMediaTypeError: If file is not a PDF
        UnprocessableEntityError: If PDF structure is invalid
    """
    # Check file size (150MB limit)
    MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB in bytes

    # Note: file.size is not available in FastAPI UploadFile
    # We'll need to read and check size, then reset the file pointer
    content = file.file.read()
    file_size = len(content)
    file.file.seek(0)  # Reset file pointer

    if file_size > MAX_FILE_SIZE:
        raise PayloadTooLargeError(
            message=f"File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size (150MB)",
            details={"file_size_bytes": file_size, "max_size_bytes": MAX_FILE_SIZE}
        )

    # Check MIME type
    if file.content_type != "application/pdf":
        raise UnsupportedMediaTypeError(
            message=f"Unsupported file type: {file.content_type}. Only PDF files are allowed.",
            details={"provided_type": file.content_type, "expected_type": "application/pdf"}
        )

    # Basic PDF structure validation
    if not content.startswith(b"%PDF"):
        raise UnprocessableEntityError(
            message="Invalid PDF file structure. File does not appear to be a valid PDF.",
            details={"issue": "Missing PDF header", "expected": "%PDF header"}
        )

    return file


def validate_document_metadata(
    metadata: str | None = Form(None, description="JSON string with document metadata")
) -> dict[str, Any] | None:
    """
    Validate and parse optional document metadata JSON.

    Args:
        metadata: Optional JSON string with document metadata

    Returns:
        Parsed metadata dictionary or None

    Raises:
        ValidationError: If metadata JSON is invalid
    """
    if metadata is None:
        return None

    try:
        parsed_metadata = json.loads(metadata)

        if not isinstance(parsed_metadata, dict):
            raise ValidationError(
                message="Metadata must be a JSON object",
                details={"provided_type": type(parsed_metadata).__name__, "expected_type": "object"}
            )

        # Validate allowed fields (optional validation)
        allowed_fields = {"title", "tags", "source_url", "uploaded_by", "description"}
        invalid_fields = set(parsed_metadata.keys()) - allowed_fields

        if invalid_fields:
            raise ValidationError(
                message=f"Invalid metadata fields: {', '.join(invalid_fields)}",
                details={
                    "invalid_fields": list(invalid_fields),
                    "allowed_fields": list(allowed_fields)
                }
            )

        return parsed_metadata

    except json.JSONDecodeError as e:
        raise ValidationError(
            message="Invalid JSON format in metadata",
            details={"json_error": str(e), "position": e.pos if hasattr(e, 'pos') else None}
        ) from e


def check_account_quota(account: Account = Depends(get_current_account)) -> Account:
    """
    Check if account has remaining quota for document uploads.

    Args:
        account: Current authenticated account

    Returns:
        The account object if quota allows

    Raises:
        QuotaExceededError: If account has reached document limit
    """
    if account.documents_uploaded >= account.max_documents:
        raise QuotaExceededError(
            message=f"Account quota exceeded. Maximum {account.max_documents} documents allowed.",
            details={
                "current_count": account.documents_uploaded,
                "max_allowed": account.max_documents,
                "account_id": account.account_id
            }
        )

    return account

