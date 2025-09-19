"""Quality metrics model for document processing SLA compliance."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator


class QualityMetrics(BaseModel):
    """Track quality metrics for documents to ensure SLA compliance.

    This model represents metrics captured during document processing
    to monitor extraction quality and processing performance against SLAs.
    """

    metric_id: UUID = Field(..., description="Unique identifier for the metrics record")
    document_id: UUID = Field(..., description="Associated document identifier")
    pages_with_anchors: int = Field(
        ..., ge=0, description="Pages with successful anchoring"
    )
    total_pages: int = Field(..., ge=0, description="Total pages in document")
    tables_extracted: int = Field(..., ge=0, description="Number of tables extracted")
    tables_detected: int = Field(..., ge=0, description="Number of tables detected")
    citations_correct: int = Field(..., ge=0, description="Number of correct citations")
    citations_total: int = Field(..., ge=0, description="Total citations generated")
    ocr_confidence_avg: float | None = Field(
        None, ge=0.0, le=1.0, description="Average OCR confidence score (0.0-1.0)"
    )
    processing_time_seconds: int = Field(..., ge=0, description="Total processing time")
    measured_at: datetime = Field(..., description="Metrics measurement timestamp")

    @field_validator("pages_with_anchors")
    @classmethod
    def validate_pages_with_anchors(cls, v: int, info) -> int:
        """Validate that pages_with_anchors <= total_pages."""
        if hasattr(info, "data") and "total_pages" in info.data:
            total_pages = info.data["total_pages"]
            if v > total_pages:
                raise ValueError("pages_with_anchors cannot exceed total_pages")
        return v

    @field_validator("tables_extracted")
    @classmethod
    def validate_tables_extracted(cls, v: int, info) -> int:
        """Validate that tables_extracted <= tables_detected."""
        if hasattr(info, "data") and "tables_detected" in info.data:
            tables_detected = info.data["tables_detected"]
            if v > tables_detected:
                raise ValueError("tables_extracted cannot exceed tables_detected")
        return v

    @field_validator("citations_correct")
    @classmethod
    def validate_citations_correct(cls, v: int, info) -> int:
        """Validate that citations_correct <= citations_total."""
        if hasattr(info, "data") and "citations_total" in info.data:
            citations_total = info.data["citations_total"]
            if v > citations_total:
                raise ValueError("citations_correct cannot exceed citations_total")
        return v

    @computed_field
    @property
    def anchor_success_rate(self) -> float:
        """Compute anchor success rate as pages_with_anchors / total_pages."""
        if self.total_pages == 0:
            return 0.0
        return self.pages_with_anchors / self.total_pages

    @computed_field
    @property
    def table_extraction_rate(self) -> float:
        """Compute table extraction rate as tables_extracted / tables_detected."""
        if self.tables_detected == 0:
            return 0.0
        return self.tables_extracted / self.tables_detected

    @computed_field
    @property
    def citation_accuracy_rate(self) -> float:
        """Compute citation accuracy rate as citations_correct / citations_total."""
        if self.citations_total == 0:
            return 0.0
        return self.citations_correct / self.citations_total

    def meets_sla_thresholds(self) -> bool:
        """Check if metrics meet SLA thresholds.

        SLA Requirements:
        - Anchor success rate >= 95%
        - Table extraction rate >= 90%
        - Citation accuracy rate >= 95%
        """
        return (
            self.anchor_success_rate >= 0.95
            and self.table_extraction_rate >= 0.90
            and self.citation_accuracy_rate >= 0.95
        )

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
