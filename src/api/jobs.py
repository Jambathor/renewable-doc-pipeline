"""
Processing job status endpoints for renewable energy PDF processing pipeline API.

This module provides the /jobs/{job_id} endpoint for monitoring document
processing job status and progress.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from ..models.processing_job import ErrorType, JobStatus, ProcessingJob

router = APIRouter()


class JobStatusResponse(BaseModel):
    """Job status response model matching OpenAPI specification."""

    job_id: UUID = Field(..., description="Job identifier")
    document_id: UUID = Field(..., description="Associated document ID")
    status: JobStatus = Field(..., description="Current job status")
    progress_percentage: int = Field(..., description="Completion percentage")
    started_at: str = Field(..., description="Processing start time")
    completed_at: str | None = Field(None, description="Processing completion time")
    error_message: str | None = Field(None, description="Error details if failed")
    error_type: ErrorType | None = Field(None, description="Error category")
    retry_count: int = Field(..., description="Number of retry attempts")


async def get_current_account(
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Dependency to get current authenticated account.

    Returns:
        Account: Current authenticated account
    """
    from uuid import uuid4
    from ..models.account import Account
    from ..api.errors import MetricsAuthenticationError

    # Require X-API-Key header
    if not x_api_key:
        raise MetricsAuthenticationError("missing_api_key", "X-API-Key header is required")

    # Validate API key (simplified for demo)
    valid_test_keys = ["test-api-key", "test-api-key-123", "test-api-key-12345", "valid-api-key-12345"]
    if x_api_key not in valid_test_keys:
        raise MetricsAuthenticationError("invalid_api_key", "Invalid API key provided")

    return Account(
        account_id=uuid4(),
        api_key=x_api_key,
        document_count=10,
        max_documents=200,
        is_active=True,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"description": "Job not found"},
        401: {"description": "Invalid or missing API key"},
    },
    summary="Get processing job status",
    description="Retrieve the current status and progress of a document processing job",
    operation_id="getJobStatus",
)
async def get_job_status(
    job_id: UUID,
    account=Depends(get_current_account),
) -> JobStatusResponse:
    """
    Get processing job status and progress information.

    This endpoint retrieves the current status of a document processing job,
    including progress percentage, error information, and retry count.

    Args:
        job_id: Unique job identifier returned from document upload
        account: Current authenticated account from dependency injection

    Returns:
        JobStatusResponse: Current job status and progress information

    Raises:
        HTTPException: 404 if job not found or doesn't belong to account
    """
    try:
        # Get job from storage (would use actual database/storage service)
        job = await _get_job_by_id(job_id, account.account_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "job_not_found",
                        "message": f"Job {job_id} not found",
                        "details": {"job_id": str(job_id)},
                        "request_id": "unknown",
                    }
                },
            )

        # Convert job model to response format
        response_data = {
            "job_id": job.job_id,
            "document_id": job.document_id,
            "status": job.status,
            "progress_percentage": job.progress_percentage,
            "started_at": job.started_at.isoformat() + "Z",
            "retry_count": job.retry_count,
        }
        
        # Only include nullable fields if they have values
        if job.completed_at:
            response_data["completed_at"] = job.completed_at.isoformat() + "Z"
        else:
            response_data["completed_at"] = None
            
        if job.error_message:
            response_data["error_message"] = job.error_message
        else:
            response_data["error_message"] = None
            
        if job.error_type:
            response_data["error_type"] = job.error_type
        else:
            response_data["error_type"] = None

        response = JobStatusResponse(**response_data)
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "system_error",
                    "message": "Failed to retrieve job status",
                    "details": {"exception": str(e)},
                    "request_id": "unknown",
                }
            },
        ) from e


async def _get_job_by_id(job_id: UUID, account_id: UUID) -> ProcessingJob | None:
    """
    Retrieve a processing job by ID for the given account.

    In a real implementation, this would query the database to find
    the job and verify it belongs to the authenticated account.

    Args:
        job_id: Job identifier to retrieve
        account_id: Account ID for authorization check

    Returns:
        ProcessingJob | None: Job if found and authorized, None otherwise
    """
    # Simplified demo implementation
    # In production, this would query the database:
    # - SELECT * FROM processing_jobs WHERE job_id = ? AND account_id = ?

    from datetime import datetime
    from uuid import uuid4

    # Return mock job for demonstration
    # In real implementation, would return None if not found
    return ProcessingJob(
        job_id=job_id,
        document_id=uuid4(),
        account_id=account_id,
        status=JobStatus.RUNNING,
        progress_percentage=75,
        started_at=datetime.utcnow(),
        completed_at=None,
        error_message=None,
        error_type=None,
        retry_count=0,
        worker_id="worker-instance-001",
    )
