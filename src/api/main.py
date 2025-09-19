"""
FastAPI application setup and middleware for renewable energy PDF processing pipeline.

This module sets up the main FastAPI application with all middleware,
error handlers, and route imports following the OpenAPI specification.
"""

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .documents import router as documents_router
from .errors import (
    APIError,
    MetricsAuthenticationError,
    NotFoundError,
    SystemError,
    UnprocessableEntityError,
    ValidationError,
    api_error_handler,
    create_error_response,
    metrics_auth_error_handler,
)
from .health import router as health_router
from .jobs import router as jobs_router
from .metrics import router as metrics_router
from .qa import router as qa_router
from .search import router as search_router

app = FastAPI(
    title="Renewable Energy PDF Processing Pipeline API",
    description="API for uploading, processing, and querying renewable energy PDF documents",
    version="1.0.0",
    contact={"name": "API Support"},
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request for tracking."""
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# Exception handlers - Order matters! More specific first, then general
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(MetricsAuthenticationError, metrics_auth_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors with proper error response format."""
    # Extract the first error message for user-friendly display
    first_error = exc.errors()[0] if exc.errors() else {"msg": "Validation error"}

    # Check if this is a path parameter validation error for UUIDs
    if first_error.get("type") == "value_error" and "uuid" in first_error.get("msg", "").lower():
        # Convert to 400 for invalid UUID format in path parameters
        validation_error = ValidationError(
            message="Invalid UUID format in request parameters",
            details={"validation_errors": exc.errors()}
        )
        return create_error_response(request, validation_error)

    # Default to 422 for other validation errors
    unprocessable_error = UnprocessableEntityError(
        message=first_error.get("msg", "Request validation failed"),
        details={"validation_errors": exc.errors()}
    )
    return create_error_response(request, unprocessable_error)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions with proper error response format."""
    # Convert ValueError to ValidationError for consistency
    validation_error = ValidationError(
        message=str(exc),
        details={"exception_type": "ValueError"}
    )
    return create_error_response(request, validation_error)


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Handle FileNotFoundError exceptions with proper error response format."""
    # Convert FileNotFoundError to NotFoundError for consistency
    not_found_error = NotFoundError(
        message=str(exc),
        details={"exception_type": "FileNotFoundError"}
    )
    return create_error_response(request, not_found_error)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions with proper error response format."""
    # Convert general exceptions to SystemError for consistency
    system_error = SystemError(
        message="An internal server error occurred",
        details={"exception_type": type(exc).__name__, "error_message": str(exc)}
    )
    return create_error_response(request, system_error)


# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(metrics_router, tags=["Metrics"])
app.include_router(documents_router, prefix="/documents", tags=["Documents"])
app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
app.include_router(search_router, tags=["Search"])
app.include_router(qa_router, tags=["Q&A"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    # Initialize storage backends, database connections, etc.
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    # Close database connections, cleanup resources, etc.
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
