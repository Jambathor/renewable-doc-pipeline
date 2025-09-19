"""Document model for renewable energy PDF processing pipeline.

This module defines the Document Pydantic model representing uploaded PDF documents
with metadata and processing status according to the data-model.md specification.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProcessingStatus(str, Enum):
    """Processing status enum for documents (lowercase values for wire format and DB storage)."""

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class Document(BaseModel):
    """Represent uploaded PDF documents with metadata and processing status.

    This model handles documents in the renewable energy PDF processing pipeline,
    tracking their lifecycle from upload through processing to completion or failure.
    """

    document_id: UUID = Field(..., description="Unique identifier for the document")
    account_id: UUID = Field(..., description="Owner account identifier")
    filename: str = Field(
        ..., min_length=1, description="Original filename, must not be empty"
    )
    file_size: int = Field(
        ...,
        ge=0,
        le=157_286_400,  # 150MB in bytes
        description="File size in bytes, must be <= 150MB (157,286,400 bytes)",
    )
    page_count: int = Field(
        ...,
        ge=0,
        le=300,
        description="Number of pages in the document, must be <= 300 pages when known",
    )
    s3_key: str = Field(..., description="S3 object key for the original PDF")
    upload_time: datetime = Field(..., description="Upload timestamp")
    processing_status: ProcessingStatus = Field(
        ..., description="Current processing state"
    )
    content_hash: str = Field(..., description="SHA-256 hash for deduplication")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional document metadata (includes optional source_url and uploaded_by fields)",
    )

    @field_validator("filename")
    @classmethod
    def validate_filename_not_empty(cls, v: str) -> str:
        """Validate that filename is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("filename must not be empty")
        return v.strip()

    @field_validator("processing_status")
    @classmethod
    def validate_processing_status(cls, v: ProcessingStatus) -> ProcessingStatus:
        """Validate that processing_status is a valid enum value."""
        if not isinstance(v, ProcessingStatus):
            try:
                # Convert string to enum if needed
                return ProcessingStatus(v)
            except ValueError as e:
                valid_values = [status.value for status in ProcessingStatus]
                raise ValueError(
                    f"processing_status must be one of: {valid_values}"
                ) from e
        return v

    class Config:
        """Pydantic model configuration."""

        # Use enum values in serialization
        use_enum_values = True
        # Validate assignment for runtime changes
        validate_assignment = True
        # JSON schema customization
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "filename": "renewable_energy_report_2024.pdf",
                "file_size": 5242880,  # 5MB
                "page_count": 45,
                "s3_key": "6ba7b810-9dad-11d1-80b4-00c04fd430c8/550e8400-e29b-41d4-a716-446655440000/original.pdf",
                "upload_time": "2025-09-17T10:30:00Z",
                "processing_status": "uploaded",
                "content_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
                "metadata": {
                    "source_url": "https://example.com/report.pdf",
                    "uploaded_by": "user@example.com",
                    "document_type": "research_report",
                },
            }
        }
