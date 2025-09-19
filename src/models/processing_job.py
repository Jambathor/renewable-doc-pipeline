"""ProcessingJob model for tracking asynchronous document processing tasks."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class JobStatus(str, Enum):
    """Job status enumeration (lowercase values for consistency)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ErrorType(str, Enum):
    """Error type enumeration (lowercase values for consistency)."""

    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    STORAGE_ERROR = "storage_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    SYSTEM_ERROR = "system_error"


class ProcessingJob(BaseModel):
    """
    Model for tracking asynchronous document processing tasks with progress and error details.

    This model represents a processing job that tracks the conversion of an uploaded document
    through OCR, content extraction, and indexing phases.
    """

    job_id: UUID = Field(..., description="Unique identifier for the processing job")

    document_id: UUID = Field(..., description="Associated document being processed")

    account_id: UUID = Field(..., description="Owner account identifier")

    status: JobStatus = Field(..., description="Current job processing status")

    progress_percentage: int = Field(
        ..., ge=0, le=100, description="Completion percentage (0-100)"
    )

    started_at: datetime = Field(..., description="Processing start timestamp")

    completed_at: datetime | None = Field(
        None, description="Processing completion timestamp"
    )

    error_message: str | None = Field(
        None, description="Error details if processing failed"
    )

    error_type: ErrorType | None = Field(
        None, description="Error category for failed jobs"
    )

    retry_count: int = Field(..., ge=0, description="Number of retry attempts")

    worker_id: str | None = Field(
        None, description="Identifier of the processing worker"
    )

    @field_validator("progress_percentage")
    @classmethod
    def validate_progress_percentage(cls, v: int) -> int:
        """Validate progress percentage is within valid range."""
        if not 0 <= v <= 100:
            raise ValueError("progress_percentage must be between 0 and 100")
        return v

    @field_validator("retry_count")
    @classmethod
    def validate_retry_count(cls, v: int) -> int:
        """Validate retry count is non-negative."""
        if v < 0:
            raise ValueError("retry_count must be >= 0")
        return v

    @model_validator(mode="after")
    def validate_completed_at_after_started_at(self) -> "ProcessingJob":
        """Validate that completed_at is after started_at when present."""
        if self.completed_at is not None and self.completed_at <= self.started_at:
            raise ValueError("completed_at must be after started_at when present")
        return self

    class Config:
        """Pydantic model configuration."""

        # Use enum values for serialization
        use_enum_values = True

        # Allow extra fields for future extensibility
        extra = "forbid"

        # Example for documentation
        json_schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_id": "123e4567-e89b-12d3-a456-426614174001",
                "account_id": "123e4567-e89b-12d3-a456-426614174002",
                "status": "running",
                "progress_percentage": 75,
                "started_at": "2025-09-17T10:30:00Z",
                "completed_at": None,
                "error_message": None,
                "error_type": None,
                "retry_count": 0,
                "worker_id": "worker-instance-001",
            }
        }
