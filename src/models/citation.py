"""
Citation model for the renewable energy PDF processing pipeline.

This module defines the Citation entity which links query responses to specific
content sources with page references for accurate document citation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    """
    Link query responses to specific content sources with page references.

    This model stores citations that reference specific content within documents,
    providing traceability from query responses back to source material with
    relevance scoring and contextual snippets.
    """

    citation_id: UUID = Field(..., description="Unique identifier for the citation")

    content_id: UUID = Field(
        ..., description="Foreign key to the referenced extracted content"
    )

    document_id: UUID = Field(
        ..., description="Foreign key to the source document (denormalized)"
    )

    page_number: int = Field(
        ..., description="Page reference in the document (denormalized)", gt=0
    )

    relevance_score: float = Field(
        ..., description="Relevance score to the query", ge=0.0, le=1.0
    )

    snippet: str = Field(..., description="Highlighted content snippet", min_length=1)

    context: str | None = Field(
        default=None, description="Surrounding context for the snippet"
    )

    created_at: datetime = Field(..., description="Timestamp when citation was created")

    @field_validator("snippet")
    @classmethod
    def validate_snippet_not_empty(cls, v: str) -> str:
        """Ensure snippet is not empty."""
        if not v.strip():
            raise ValueError("snippet must not be empty")
        return v

    @field_validator("relevance_score")
    @classmethod
    def validate_relevance_score_range(cls, v: float) -> float:
        """Ensure relevance_score is within valid range."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("relevance_score must be between 0.0 and 1.0")
        return v

    @field_validator("page_number")
    @classmethod
    def validate_page_number_positive(cls, v: int) -> int:
        """Ensure page_number is positive."""
        if v <= 0:
            raise ValueError("page_number must be greater than 0")
        return v

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
