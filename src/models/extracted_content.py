"""
ExtractedContent model for the renewable energy PDF processing pipeline.

This module defines the ExtractedContent entity which represents chunks of content
extracted from documents with vector embeddings for semantic search.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ContentType(str, Enum):
    """Content type enumeration for extracted content."""

    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    IMAGE = "image"
    TITLE = "title"
    METADATA = "metadata"


class ExtractedContent(BaseModel):
    """
    Represent chunks of content extracted from documents with vector embeddings.

    This model stores processed content from PDF documents including text,
    tables, charts, images, and metadata with their semantic embeddings
    for search and retrieval operations.
    """

    content_id: UUID = Field(
        ..., description="Unique identifier for the extracted content"
    )

    document_id: UUID = Field(..., description="Foreign key to the source document")

    page_number: int = Field(..., description="Page location in document", gt=0)

    content_type: ContentType = Field(..., description="Type of extracted content")

    text_content: str = Field(..., description="Extracted text content", min_length=1)

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Content-specific metadata in JSON format"
    )

    vector_embedding: list[float] = Field(
        ..., description="Semantic embedding vector for search"
    )

    bounding_box: dict[str, Any] | None = Field(
        default=None, description="Coordinates in source page (JSON format)"
    )

    confidence_score: float = Field(
        ..., description="Extraction confidence score", ge=0.0, le=1.0
    )

    is_ocr_generated: bool = Field(
        ..., description="Whether content came from OCR processing"
    )

    extracted_at: datetime = Field(
        ..., description="Timestamp when content was extracted"
    )

    @field_validator("text_content")
    @classmethod
    def validate_text_content_not_empty(cls, v: str) -> str:
        """Ensure text_content is not empty."""
        if not v.strip():
            raise ValueError("text_content must not be empty")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: ContentType) -> ContentType:
        """Ensure content_type is a valid enum value."""
        if v not in ContentType:
            raise ValueError(f"content_type must be one of {list(ContentType)}")
        return v

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
