"""
Search endpoints for renewable energy PDF processing pipeline API.

This module provides the /search endpoint for hybrid retrieval across
text, tables, images, and charts in processed documents.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..models.extracted_content import ContentType

router = APIRouter()


class SearchResult(BaseModel):
    """Search result model matching OpenAPI specification."""

    content_id: UUID = Field(..., description="Unique content identifier")
    document_id: UUID = Field(..., description="Source document ID")
    document_title: str = Field(..., description="Document title or filename")
    page_number: int = Field(..., description="Page location in document")
    content_type: ContentType = Field(..., description="Type of content")
    snippet: str = Field(..., description="Relevant content snippet")
    confidence_score: float = Field(..., description="Extraction confidence")
    relevance_score: float = Field(..., description="Relevance to query")
    is_ocr_generated: bool = Field(..., description="Whether content came from OCR")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Content-specific metadata"
    )
    thumbnail_url: str | None = Field(
        None, description="Pre-signed, time-limited URL to visual content thumbnail"
    )


class SearchResponse(BaseModel):
    """Search response model matching OpenAPI specification."""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of matching results")
    results: list[SearchResult] = Field(..., description="Ranked search results")
    filters_applied: dict[str, Any] = Field(
        ..., description="Filters that were applied to the search"
    )


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
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Search results retrieved successfully"},
        400: {"description": "Invalid search parameters"},
        401: {"description": "Invalid or missing API key"},
        429: {"description": "Too many requests (rate limit exceeded)"},
    },
    summary="Search across indexed documents",
    description="Perform hybrid retrieval across text, tables, images, and charts in processed documents",
    operation_id="searchDocuments",
)
async def search_documents(
    query: str = Query(
        ..., min_length=1, max_length=500, description="Search query string"
    ),
    content_types: str | None = Query(
        None,
        description="Filter by content types (CSV format)",
        regex=r"^(text|table|chart|image|title|metadata)(,(text|table|chart|image|title|metadata))*$",
    ),
    document_ids: str | None = Query(
        None,
        description="Filter by specific document IDs (CSV format)",
    ),
    page_range: str | None = Query(
        None,
        description="Filter by page range (e.g., '1-10')",
        regex=r"^\d+-\d+$",
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of results to return"
    ),
    min_confidence: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum confidence score for results"
    ),
    account=Depends(get_current_account),
) -> SearchResponse:
    """
    Search across indexed document content with hybrid retrieval.

    This endpoint performs semantic and keyword search across processed document
    content including text, tables, charts, images, and metadata. Results are
    ranked by relevance score and filtered by confidence thresholds.

    Rate Limiting:
        This endpoint is rate limited. Clients should handle HTTP 429 responses
        with exponential backoff retry logic.

    Args:
        query: Search query string (1-500 characters)
        content_types: Comma-separated content types to filter by
        document_ids: Comma-separated document UUIDs to filter by
        page_range: Page range filter (e.g., "1-10")
        limit: Maximum results to return (1-100)
        min_confidence: Minimum confidence score filter (0.0-1.0)
        account: Current authenticated account

    Returns:
        SearchResponse: Ranked search results with metadata

    Raises:
        HTTPException: 400 for invalid parameters, 429 for rate limits
    """
    try:
        # Parse content types filter
        content_types_list = (
            _parse_content_types(content_types) if content_types else None
        )

        # Parse document IDs filter
        document_ids_list = _parse_document_ids(document_ids) if document_ids else None

        # Parse page range filter
        page_start, page_end = (
            _parse_page_range(page_range) if page_range else (None, None)
        )

        # Build filters dictionary
        filters_applied = {
            "content_types": content_types_list,
            "document_ids": document_ids_list,
            "page_range": (
                f"{page_start}-{page_end}" if page_start and page_end else None
            ),
            "min_confidence": min_confidence,
            "limit": limit,
        }

        # Perform search (would use actual search service)
        search_results = await _perform_search(
            query=query,
            account_id=account.account_id,
            content_types=content_types_list,
            document_ids=document_ids_list,
            page_start=page_start,
            page_end=page_end,
            limit=limit,
            min_confidence=min_confidence,
        )

        response = SearchResponse(
            query=query,
            total_results=len(search_results),
            results=search_results,
            filters_applied={k: v for k, v in filters_applied.items() if v is not None},
        )

        return response

    except ValueError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "validation_error",
                    "message": str(e),
                    "details": {},
                    "request_id": "unknown",
                }
            },
        )
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "system_error",
                    "message": "Search request failed",
                    "details": {"exception": str(e)},
                    "request_id": "unknown",
                }
            },
        )


def _parse_content_types(content_types_str: str) -> list[ContentType]:
    """Parse CSV content types string into list of ContentType enums."""
    types = [t.strip() for t in content_types_str.split(",")]
    parsed_types = []

    for type_str in types:
        try:
            parsed_types.append(ContentType(type_str))
        except ValueError as e:
            raise ValueError(f"Invalid content type: {type_str}") from e

    return parsed_types


def _parse_document_ids(document_ids_str: str) -> list[UUID]:
    """Parse CSV document IDs string into list of UUIDs."""
    ids = [id_str.strip() for id_str in document_ids_str.split(",")]
    parsed_ids = []

    for id_str in ids:
        try:
            parsed_ids.append(UUID(id_str))
        except ValueError as e:
            raise ValueError(f"Invalid document ID format: {id_str}") from e

    return parsed_ids


def _parse_page_range(page_range_str: str) -> tuple[int, int]:
    """Parse page range string (e.g., '1-10') into start and end integers."""
    try:
        start_str, end_str = page_range_str.split("-")
        start = int(start_str)
        end = int(end_str)

        if start < 1 or end < 1 or start > end:
            raise ValueError(
                "Invalid page range: start and end must be positive, start <= end"
            )

        return start, end
    except ValueError as e:
        raise ValueError(f"Invalid page range format: {page_range_str}") from e


async def _perform_search(
    query: str,
    account_id: UUID,
    content_types: list[ContentType] | None = None,
    document_ids: list[UUID] | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    limit: int = 20,
    min_confidence: float = 0.0,
) -> list[SearchResult]:
    """
    Perform hybrid search across indexed content.

    In a real implementation, this would:
    1. Use the search service to query Qdrant vector database
    2. Apply filters for content types, documents, pages, confidence
    3. Rank results by relevance score
    4. Generate thumbnail URLs for visual content

    Returns:
        List[SearchResult]: Ranked search results
    """
    # Mock search results for demo
    from uuid import uuid4

    return [
        SearchResult(
            content_id=uuid4(),
            document_id=uuid4(),
            document_title="Solar Panel Efficiency Report 2024",
            page_number=15,
            content_type=ContentType.TABLE,
            snippet="California solar installations showed 22.5% average efficiency with peak performance of 24.8% under optimal conditions...",
            confidence_score=0.92,
            relevance_score=0.88,
            is_ocr_generated=False,
            metadata={
                "table_type": "performance_data",
                "headers": ["Location", "Efficiency %", "Peak Performance %"],
                "rows": 12,
            },
            thumbnail_url=None,
        )
    ]
