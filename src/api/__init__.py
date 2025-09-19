"""
API module for renewable energy PDF processing pipeline.

This package contains FastAPI endpoints and related functionality for
the renewable energy document processing system.

Modules:
    main: FastAPI application setup with middleware and routing
    documents: Document upload, retrieval, and deletion endpoints
    jobs: Processing job status monitoring endpoints
    search: Content search and retrieval endpoints
    qa: Question answering with evidence grounding endpoints
    health: Health check endpoint for monitoring
    metrics: Prometheus metrics endpoint for observability

All endpoints follow the OpenAPI specification defined in
specs/001-we-re-building/contracts/openapi.yaml.
"""
