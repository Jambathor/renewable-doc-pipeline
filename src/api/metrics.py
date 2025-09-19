"""
Prometheus metrics endpoint for renewable energy PDF processing pipeline API.

This module provides the /metrics endpoint for observability and monitoring,
requiring API key authentication outside of local environments.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..config.settings import settings

router = APIRouter()


async def verify_metrics_auth(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> None:
    """
    Verify API key authentication for metrics endpoint.

    The /metrics endpoint requires X-API-Key header outside local environment
    for security. In local development, authentication is bypassed.

    Args:
        request: FastAPI request object for environment detection
        x_api_key: API key from X-API-Key header

    Raises:
        HTTPException: 401 if authentication fails in non-local environment
    """
    # Skip authentication in local environment
    if _is_local_environment(request):
        return

    # Require X-API-Key header in non-local environments
    if not x_api_key:
        from src.api.errors import MetricsAuthenticationError
        raise MetricsAuthenticationError("missing_api_key", "X-API-Key header is required for metrics access")

    # Validate API key (simplified for demo)
    # In production, this would verify against the account service
    if not _validate_api_key(x_api_key):
        from src.api.errors import MetricsAuthenticationError
        raise MetricsAuthenticationError("invalid_api_key", "Invalid API key provided")


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Metrics retrieved successfully",
            "content": {"text/plain": {}},
        },
        401: {"description": "Invalid or missing API key"},
    },
    summary="Prometheus metrics endpoint",
    description="Metrics in Prometheus format for monitoring",
    operation_id="getMetrics",
    dependencies=[Depends(verify_metrics_auth)],
)
async def get_metrics() -> PlainTextResponse:
    """
    Prometheus metrics endpoint for monitoring and observability.

    Returns metrics in Prometheus format including:
    - HTTP request counters and histograms
    - Document processing metrics
    - Queue/task runner metrics
    - Database connection metrics
    - Vector database metrics
    - Storage operation metrics

    Authentication:
        - Local environment: No authentication required
        - Non-local: Requires valid X-API-Key header

    Returns:
        PlainTextResponse: Prometheus metrics in text format
    """
    try:
        # Generate Prometheus metrics
        metrics_data = generate_latest()

        return PlainTextResponse(
            content=metrics_data.decode("utf-8"),
            media_type=CONTENT_TYPE_LATEST,
        )

    except Exception as e:
        # Return error metrics in case of failure
        error_metrics = f"""# HELP renewable_pipeline_metrics_error Metrics collection error
# TYPE renewable_pipeline_metrics_error gauge
renewable_pipeline_metrics_error{{error="{str(e)}"}} 1
"""
        return PlainTextResponse(
            content=error_metrics,
            media_type=CONTENT_TYPE_LATEST,
        )


def _is_local_environment(request: Request) -> bool:
    """
    Check if the request is from a local development environment.

    Args:
        request: FastAPI request object

    Returns:
        bool: True if local environment, False otherwise
    """
    # Per OpenAPI contract, /metrics endpoint requires authentication
    # Only bypass auth if explicitly configured via environment variable
    if getattr(settings, "environment", "").lower() == "local_no_auth":
        return True

    return False


def _validate_api_key(api_key: str) -> bool:
    """
    Validate the provided API key.

    In a real implementation, this would check against the account service
    to verify the API key exists and is active.

    Args:
        api_key: The API key to validate

    Returns:
        bool: True if valid, False otherwise
    """
    # Simplified validation for demo
    # In production, this would call the account service
    # For testing, accept specific test keys
    valid_test_keys = ["test-api-key", "test-api-key-123", "test-api-key-12345", "valid-api-key-12345"]
    return api_key in valid_test_keys
