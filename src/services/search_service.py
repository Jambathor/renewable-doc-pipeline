"""
Search service for the renewable energy PDF processing pipeline.

This module provides hybrid retrieval capabilities across text, tables, images, and charts
using Qdrant vector database. Supports semantic search with filtering and result ranking.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field

from ..config.settings import settings
from ..models.extracted_content import ContentType, ExtractedContent
from ..storage.qdrant_client import QdrantClient, SearchResult, get_qdrant_client


class SearchFilters(BaseModel):
    """Filters for search operations."""

    content_types: List[ContentType] = Field(
        default_factory=list, description="Filter by content types"
    )
    document_ids: List[UUID] = Field(
        default_factory=list, description="Filter by document IDs"
    )
    page_range: Optional[Tuple[int, int]] = Field(
        default=None, description="Page range filter (start, end)"
    )
    min_confidence: float = Field(
        default=0.0, description="Minimum confidence score", ge=0.0, le=1.0
    )
    account_id: UUID = Field(..., description="Account ID for multi-tenant filtering")


class SearchResults(BaseModel):
    """Search results with metadata."""

    results: List[SearchResult] = Field(
        default_factory=list, description="List of search results"
    )
    total_count: int = Field(description="Total number of results found")
    query_time_ms: float = Field(description="Query execution time in milliseconds")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict, description="Applied search filters"
    )


class SearchError(Exception):
    """Base exception for search operations."""

    def __init__(self, message: str, error_type: str = "search_error"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class EmbeddingError(SearchError):
    """Exception for embedding generation issues."""

    def __init__(self, message: str):
        super().__init__(message, "embedding_error")


class RateLimitError(SearchError):
    """Exception for rate limiting violations."""

    def __init__(self, message: str):
        super().__init__(message, "rate_limit_error")


class SearchService:
    """
    Search service providing hybrid retrieval across multiple content types.

    Supports semantic search using vector embeddings with filtering capabilities
    for content types, documents, pages, and confidence scores. Includes rate
    limiting and multi-tenant isolation.
    """

    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """
        Initialize search service.

        Args:
            qdrant_client: Optional Qdrant client instance. Defaults to global client.
        """
        self._qdrant_client = qdrant_client or get_qdrant_client()
        self._embedding_model = None
        self._rate_limiter = {}  # Simple in-memory rate limiter

    async def _get_embedding_model(self):
        """Get or initialize embedding model."""
        if self._embedding_model is None:
            try:
                # Use LlamaIndex's default embedding model
                from llama_index.embeddings.openai import OpenAIEmbedding
                from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                
                # Try HuggingFace sentence-transformers first (offline capability)
                try:
                    self._embedding_model = HuggingFaceEmbedding(
                        model_name="sentence-transformers/all-MiniLM-L6-v2",
                        max_length=512,
                    )
                except Exception:
                    # Fallback to OpenAI if available
                    self._embedding_model = OpenAIEmbedding()
                    
            except Exception as e:
                raise EmbeddingError(f"Failed to initialize embedding model: {str(e)}")
                
        return self._embedding_model

    async def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding vector for search query.

        Args:
            query: Search query text

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            if not query.strip():
                raise EmbeddingError("Query text cannot be empty")

            model = await self._get_embedding_model()
            
            # Generate embedding using LlamaIndex embedding model
            embedding = await asyncio.to_thread(model.get_query_embedding, query)
            
            if not embedding or len(embedding) == 0:
                raise EmbeddingError("Failed to generate embedding vector")
                
            return embedding

        except Exception as e:
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingError(f"Embedding generation failed: {str(e)}")

    def filter_by_content_types(self, content_types: List[ContentType]) -> Dict[str, Any]:
        """
        Create Qdrant filter for content types.

        Args:
            content_types: List of content types to include

        Returns:
            Qdrant filter dictionary
        """
        if not content_types:
            return {}

        # Convert enum values to strings for Qdrant filtering
        type_values = [ct.value for ct in content_types]
        
        if len(type_values) == 1:
            return {"content_type": type_values[0]}
        else:
            # For multiple values, we'll need to handle this in the search method
            # since Qdrant filter format may vary
            return {"content_type": {"$in": type_values}}

    def filter_by_document_ids(self, document_ids: List[UUID]) -> Dict[str, Any]:
        """
        Create Qdrant filter for document IDs.

        Args:
            document_ids: List of document IDs to include

        Returns:
            Qdrant filter dictionary
        """
        if not document_ids:
            return {}

        # Convert UUIDs to strings
        doc_id_strings = [str(doc_id) for doc_id in document_ids]
        
        if len(doc_id_strings) == 1:
            return {"document_id": doc_id_strings[0]}
        else:
            return {"document_id": {"$in": doc_id_strings}}

    def filter_by_confidence(self, min_confidence: float) -> Dict[str, Any]:
        """
        Create Qdrant filter for minimum confidence score.

        Args:
            min_confidence: Minimum confidence threshold

        Returns:
            Qdrant filter dictionary
        """
        if min_confidence <= 0.0:
            return {}

        return {"confidence_score": {"$gte": min_confidence}}

    def _build_qdrant_filters(self, filters: SearchFilters) -> Dict[str, Any]:
        """
        Build combined Qdrant filters from SearchFilters.

        Args:
            filters: Search filter parameters

        Returns:
            Combined filter dictionary for Qdrant
        """
        combined_filters = {}

        # Account ID filter (required for multi-tenancy)
        combined_filters["account_id"] = str(filters.account_id)

        # Content type filters
        if filters.content_types:
            type_filter = self.filter_by_content_types(filters.content_types)
            combined_filters.update(type_filter)

        # Document ID filters
        if filters.document_ids:
            doc_filter = self.filter_by_document_ids(filters.document_ids)
            combined_filters.update(doc_filter)

        # Confidence filter
        if filters.min_confidence > 0.0:
            conf_filter = self.filter_by_confidence(filters.min_confidence)
            combined_filters.update(conf_filter)

        # Page range filter
        if filters.page_range:
            start_page, end_page = filters.page_range
            if start_page > 0 and end_page >= start_page:
                combined_filters["page_number"] = {
                    "$gte": start_page,
                    "$lte": end_page,
                }

        return combined_filters

    def rank_results_by_relevance(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Rank search results by relevance score.

        Args:
            results: List of search results to rank

        Returns:
            Results sorted by relevance (highest first)
        """
        # Results from Qdrant are already sorted by similarity score
        # Apply additional ranking logic if needed
        return sorted(
            results,
            key=lambda r: (
                r.similarity_score,  # Primary: similarity score
                r.confidence_score,  # Secondary: extraction confidence
                -r.page_number,      # Tertiary: prefer earlier pages
            ),
            reverse=True,
        )

    def _check_rate_limit(self, account_id: UUID) -> None:
        """
        Check rate limiting for search operations.

        Args:
            account_id: Account ID for rate limiting

        Raises:
            RateLimitError: If rate limit exceeded
        """
        current_time = time.time()
        account_key = str(account_id)
        
        # Clean up old entries (older than 1 minute)
        if account_key in self._rate_limiter:
            self._rate_limiter[account_key] = [
                timestamp for timestamp in self._rate_limiter[account_key]
                if current_time - timestamp < 60
            ]
        else:
            self._rate_limiter[account_key] = []

        # Check rate limit
        request_count = len(self._rate_limiter[account_key])
        if request_count >= settings.search_rate_limit:
            raise RateLimitError(
                f"Search rate limit exceeded. Maximum {settings.search_rate_limit} requests per minute."
            )

        # Add current request
        self._rate_limiter[account_key].append(current_time)

    async def search_content(
        self,
        query: str,
        filters: SearchFilters,
        limit: int = 20,
    ) -> SearchResults:
        """
        Search content using hybrid retrieval across multiple content types.

        Args:
            query: Search query text
            filters: Search filters including content types, documents, etc.
            limit: Maximum number of results to return

        Returns:
            SearchResults with ranked results and metadata

        Raises:
            SearchError: If search operation fails
            RateLimitError: If rate limit exceeded
            EmbeddingError: If query embedding generation fails
        """
        start_time = time.time()

        try:
            # Check rate limiting
            self._check_rate_limit(filters.account_id)

            # Generate query embedding
            query_embedding = await self.generate_query_embedding(query)

            # Build Qdrant filters
            qdrant_filters = self._build_qdrant_filters(filters)

            # Get collection name for account
            collection_name = self._qdrant_client.get_account_collection_name(
                filters.account_id
            )

            # Perform vector search
            search_results = await self._qdrant_client.search_similar(
                collection_name=collection_name,
                query_embedding=query_embedding,
                limit=limit,
                filters=qdrant_filters,
                min_score=0.1,  # Minimum similarity threshold
            )

            # Rank results by relevance
            ranked_results = self.rank_results_by_relevance(search_results)

            # Calculate query time
            query_time_ms = (time.time() - start_time) * 1000

            return SearchResults(
                results=ranked_results,
                total_count=len(ranked_results),
                query_time_ms=query_time_ms,
                filters_applied={
                    "content_types": [ct.value for ct in filters.content_types],
                    "document_ids": [str(doc_id) for doc_id in filters.document_ids],
                    "page_range": filters.page_range,
                    "min_confidence": filters.min_confidence,
                    "account_id": str(filters.account_id),
                },
            )

        except (RateLimitError, EmbeddingError) as e:
            raise
        except Exception as e:
            raise SearchError(f"Search operation failed: {str(e)}")


# Global service instance
_search_service_instance: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """
    Get or create global search service instance.

    Returns:
        SearchService instance configured with application settings
    """
    global _search_service_instance
    if _search_service_instance is None:
        _search_service_instance = SearchService()
    return _search_service_instance


async def cleanup_search_service() -> None:
    """Clean up global search service instance."""
    global _search_service_instance
    if _search_service_instance:
        # Clean up embedding model if needed
        _search_service_instance._embedding_model = None
        _search_service_instance = None