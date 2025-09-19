"""
Renewable Energy PDF Processing Pipeline Data Models.

This package contains Pydantic v2 models representing the core entities
in the renewable energy document processing system.

Models:
    Account: API key holders with document limits and usage tracking
    Document: Uploaded PDF documents with metadata and processing status
    ProcessingJob: Asynchronous document processing tasks with progress tracking
    ExtractedContent: Content chunks extracted from documents with embeddings
    Citation: Links between query responses and specific content sources
    QualityMetrics: Document processing quality metrics for SLA compliance

All models follow the specifications in data-model.md and use lowercase enum values
for consistency with wire format and database storage requirements.
"""

from .account import Account
from .citation import Citation
from .document import Document, ProcessingStatus
from .extracted_content import ContentType, ExtractedContent
from .processing_job import ErrorType, JobStatus, ProcessingJob
from .quality_metrics import QualityMetrics

__all__ = [
    "Account",
    "Citation",
    "ContentType",
    "Document",
    "ErrorType",
    "ExtractedContent",
    "JobStatus",
    "ProcessingJob",
    "ProcessingStatus",
    "QualityMetrics",
]
