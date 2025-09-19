"""
Document management endpoints for renewable energy PDF processing pipeline API.

This module provides document upload, retrieval, and deletion endpoints
with file validation and processing job creation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from ..models.document import Document, ProcessingStatus
from .dependencies import (
    Account,
    check_account_quota,
    get_current_account,
    validate_document_id,
    validate_document_metadata,
    validate_optional_uuid_header,
    validate_pdf_file,
)
from .errors import NotFoundError, SystemError

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Document upload response model matching OpenAPI specification."""

    document_id: UUID = Field(..., description="Unique document identifier")
    job_id: UUID = Field(..., description="Processing job identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Initial processing status")
    upload_time: str = Field(..., description="Upload timestamp")


class DocumentResponse(BaseModel):
    """Document response model matching OpenAPI specification."""

    document_id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    page_count: int | None = Field(
        None, description="Number of pages (available after processing)"
    )
    processing_status: str = Field(..., description="Current processing status")
    upload_time: str = Field(..., description="Upload timestamp")
    metadata: dict[str, Any] | None = Field(None, description="Document metadata")


class DeletionResponse(BaseModel):
    """Document deletion response model matching OpenAPI specification."""

    document_id: UUID = Field(..., description="Document identifier")
    status: str = Field(..., description="Deletion status")
    deletion_scheduled_at: str = Field(
        ..., description="When deletion will be completed"
    )
    message: str = Field(..., description="Deletion confirmation message")




@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Document uploaded successfully"},
        400: {"description": "Invalid request (file too large, wrong format, etc.)"},
        401: {"description": "Invalid or missing API key"},
        413: {"description": "Payload too large (file exceeds 150MB limit)"},
        415: {"description": "Unsupported media type (not a PDF)"},
        422: {"description": "Unprocessable entity (invalid PDF structure)"},
        429: {"description": "Account quota exceeded (200 documents max)"},
    },
    summary="Upload a PDF document for processing",
    description="Upload a renewable energy PDF document for asynchronous processing and indexing",
    operation_id="uploadDocument",
)
async def upload_document(
    file: UploadFile = Depends(validate_pdf_file),
    metadata: dict[str, Any] | None = Depends(validate_document_metadata),
    idempotency_key: str | None = Depends(validate_optional_uuid_header),
    account: Account = Depends(check_account_quota),
) -> DocumentUploadResponse:
    """
    Upload a PDF document for processing and indexing.

    All validation (file size, type, structure, account quota, metadata) is handled
    by FastAPI dependencies before this function is called.

    Args:
        file: Validated PDF file from dependency
        metadata: Parsed and validated metadata dictionary or None
        idempotency_key: Optional UUID for duplicate prevention
        account: Current authenticated account (quota already checked)

    Returns:
        DocumentUploadResponse: Upload confirmation with document and job IDs
    """
    try:
        # Read file content (already validated by dependency)
        file_content = await file.read()
        file_size = len(file_content)

        # Create document and job records
        document_id = uuid4()
        job_id = uuid4()
        upload_time = datetime.utcnow()

        # In real implementation, would save to storage and database
        document = await _create_document_record(
            document_id=document_id,
            account_id=account.account_id,
            filename=file.filename or "uploaded_document.pdf",
            file_size=file_size,
            content=file_content,
            metadata=metadata or {},
            upload_time=upload_time,
        )

        # Create processing job
        await _create_processing_job(
            job_id=job_id,
            document_id=document_id,
            account_id=account.account_id,
        )

        response = DocumentUploadResponse(
            document_id=document_id,
            job_id=job_id,
            filename=document.filename,
            file_size=document.file_size,
            status=document.processing_status.value,
            upload_time=upload_time.isoformat() + "Z",
        )

        return response

    except Exception as e:
        # Convert any unexpected errors to SystemError
        raise SystemError(
            message="Document upload failed due to internal error",
            details={"exception": str(e), "exception_type": type(e).__name__}
        ) from e


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Document metadata retrieved successfully"},
        404: {"description": "Document not found"},
        401: {"description": "Invalid or missing API key"},
    },
    summary="Get document metadata and status",
    description="Retrieve document metadata, processing status, and basic information",
    operation_id="getDocument",
)
async def get_document(
    document_id: str = Depends(validate_document_id),
    account: Account = Depends(get_current_account),
) -> DocumentResponse:
    """
    Get document metadata and processing status.

    This endpoint retrieves basic document information including metadata,
    processing status, and file information for authorized documents.

    Args:
        document_id: Unique document identifier
        account: Current authenticated account

    Returns:
        DocumentResponse: Document metadata and status information

    Raises:
        HTTPException: 404 if document not found or unauthorized
    """
    try:
        # Retrieve document from storage (convert string UUID to UUID object)
        document_uuid = UUID(document_id)
        document = await _get_document_by_id(document_uuid, account.account_id)

        if not document:
            raise NotFoundError(
                message=f"Document {document_id} not found",
                details={"document_id": document_id}
            )

        response = DocumentResponse(
            document_id=document.document_id,
            filename=document.filename,
            file_size=document.file_size,
            page_count=document.page_count if document.page_count > 0 else None,
            processing_status=document.processing_status.value,
            upload_time=document.upload_time.isoformat() + "Z",
            metadata=document.metadata if document.metadata else None,
        )

        return response

    except (NotFoundError, SystemError):
        raise
    except Exception as e:
        raise SystemError(
            message="Failed to retrieve document",
            details={"exception": str(e), "exception_type": type(e).__name__}
        ) from e


@router.delete(
    "/{document_id}",
    response_model=DeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Document marked for deletion"},
        404: {"description": "Document not found"},
        401: {"description": "Invalid or missing API key"},
    },
    summary="Delete a document and its indexed content",
    description="Mark a document for deletion",
    operation_id="deleteDocument",
)
async def delete_document(
    document_id: str = Depends(validate_document_id),
    account: Account = Depends(get_current_account),
) -> DeletionResponse:
    """
    Delete a document and all its associated data.

    This endpoint performs immediate hard deletion in demo mode while preserving
    API semantics. In production, this would mark for deletion and schedule
    cleanup of:
    - Original PDF file from S3
    - Extracted content and embeddings from Qdrant
    - Database records and processing jobs
    - Generated thumbnails and artifacts

    Demo Behavior:
        - Immediate hard delete of all associated data
        - API response preserves contract format for compatibility

    Args:
        document_id: Unique document identifier
        account: Current authenticated account

    Returns:
        DeletionResponse: Deletion confirmation with scheduled time

    Raises:
        HTTPException: 404 if document not found or unauthorized
    """
    try:
        # Verify document exists and belongs to account (convert string UUID to UUID object)
        document_uuid = UUID(document_id)
        document = await _get_document_by_id(document_uuid, account.account_id)

        if not document:
            raise NotFoundError(
                message=f"Document {document_id} not found",
                details={"document_id": document_id}
            )

        # Perform immediate hard deletion (demo mode)
        deletion_time = datetime.utcnow()
        await _hard_delete_document(document_uuid, account.account_id)

        response = DeletionResponse(
            document_id=document_uuid,
            status="marked_for_deletion",
            deletion_scheduled_at=deletion_time.isoformat() + "Z",
            message="Document will be permanently deleted within 24 hours",
        )

        return response

    except (NotFoundError, SystemError):
        raise
    except Exception as e:
        raise SystemError(
            message="Failed to delete document",
            details={"exception": str(e), "exception_type": type(e).__name__}
        ) from e


def _validate_pdf_structure(file_content: bytes) -> bool:
    """
    Validate PDF file structure and readability.

    Args:
        file_content: PDF file content bytes

    Returns:
        bool: True if valid PDF structure, False otherwise
    """
    # Basic PDF validation - check for PDF header
    if not file_content.startswith(b"%PDF-"):
        return False

    # In real implementation, would use PyPDF2 or similar to validate structure
    # For demo, assume valid if starts with PDF header
    return True


async def _create_document_record(
    document_id: UUID,
    account_id: UUID,
    filename: str,
    file_size: int,
    content: bytes,
    metadata: dict[str, Any],
    upload_time: datetime,
) -> Document:
    """Create document record in storage."""
    # Mock document creation for demo
    import hashlib

    content_hash = hashlib.sha256(content).hexdigest()

    return Document(
        document_id=document_id,
        account_id=account_id,
        filename=filename,
        file_size=file_size,
        page_count=0,  # Would be determined during processing
        s3_key=f"{account_id}/{document_id}/original.pdf",
        upload_time=upload_time,
        processing_status=ProcessingStatus.UPLOADED,
        content_hash=content_hash,
        metadata=metadata,
    )


async def _create_processing_job(job_id: UUID, document_id: UUID, account_id: UUID):
    """Create processing job record."""
    # In real implementation, would create job in database and queue
    pass


async def _get_document_by_id(document_id: UUID, account_id: UUID) -> Document | None:
    """Retrieve document by ID for authorized account."""
    # Mock document retrieval for demo
    return Document(
        document_id=document_id,
        account_id=account_id,
        filename="solar-panel-efficiency-report.pdf",
        file_size=2457600,
        page_count=42,
        s3_key=f"{account_id}/{document_id}/original.pdf",
        upload_time=datetime.utcnow(),
        processing_status=ProcessingStatus.COMPLETED,
        content_hash="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
        metadata={
            "title": "Solar Panel Efficiency Report 2024",
            "tags": ["solar", "efficiency", "california"],
            "source_url": "https://example.com/report.pdf",
            "uploaded_by": "researcher@company.com",
        },
    )


async def _hard_delete_document(document_id: UUID, account_id: UUID):
    """Perform immediate hard deletion of document and all associated data."""
    # In real implementation, would:
    # 1. Delete S3 objects (original PDF + extracted assets)
    # 2. Delete vector embeddings from Qdrant
    # 3. Delete database records (document, jobs, content, citations, metrics)
    # 4. Update account document count
    pass
