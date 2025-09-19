"""
Health check endpoint for renewable energy PDF processing pipeline API.

This module provides the /healthz endpoint for service health monitoring,
including dependency status checks as specified in the OpenAPI contract.
"""

from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model matching OpenAPI specification."""

    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    dependencies: dict[str, str] = Field(..., description="Dependency health status")


@router.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
    summary="Health check endpoint",
    description="Check API service health status (unauthenticated health probe)",
    operation_id="healthCheck",
)
async def health_check() -> HealthResponse | dict:
    """
    Health check endpoint that verifies service and dependency status.

    This endpoint is unauthenticated and used for health probing by load balancers
    and monitoring systems. It checks the status of key dependencies:
    - database: PostgreSQL connection
    - vector_store: Qdrant vector database
    - storage: S3 or local storage backend
    - queue: Background task runner (in-process for demo)

    Returns:
        HealthResponse: Service health status with dependency checks
    """
    try:
        # Check dependencies (simplified for demo - would check actual connections)
        dependencies = await _check_dependencies()

        # Determine overall health status
        overall_status = (
            "healthy"
            if all(dep_status == "healthy" for dep_status in dependencies.values())
            else "unhealthy"
        )

        response = HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            dependencies=dependencies,
        )

        return response

    except Exception as e:
        # Return unhealthy status on any error
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "dependencies": {
                "database": "unhealthy",
                "vector_store": "unhealthy",
                "storage": "unhealthy",
                "queue": "unhealthy",
            },
            "error": str(e),
        }


async def _check_dependencies() -> dict[str, str]:
    """
    Check the health status of service dependencies.

    Note: In the demo implementation, "queue" refers to the background task runner
    since async processing uses in-process background tasks rather than external
    message queues like SQS.

    Returns:
        Dict[str, str]: Dictionary mapping dependency names to health status
    """
    dependencies = {}

    # Check database connection (PostgreSQL)
    try:
        # In a real implementation, this would ping the database
        # For demo purposes, assume healthy
        dependencies["database"] = "healthy"
    except Exception:
        dependencies["database"] = "unhealthy"

    # Check vector store connection (Qdrant)
    try:
        # In a real implementation, this would ping Qdrant
        # For demo purposes, assume healthy
        dependencies["vector_store"] = "healthy"
    except Exception:
        dependencies["vector_store"] = "unhealthy"

    # Check storage backend (S3 or local)
    try:
        # In a real implementation, this would check storage accessibility
        # For demo purposes, assume healthy
        dependencies["storage"] = "healthy"
    except Exception:
        dependencies["storage"] = "unhealthy"

    # Check background task runner (in-process queue for demo)
    try:
        # In a real implementation, this would check task runner status
        # For demo purposes, assume healthy
        dependencies["queue"] = "healthy"
    except Exception:
        dependencies["queue"] = "unhealthy"

    return dependencies
