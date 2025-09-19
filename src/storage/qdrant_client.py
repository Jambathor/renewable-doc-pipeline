"""
Qdrant vector database client for the renewable energy PDF processing pipeline.

This module provides an async client for Qdrant operations including collection management,
content storage, similarity search, and deletion. Supports both single-tenant and multi-tenant
modes for flexible deployment scenarios.
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException

from ..config.settings import settings


class SearchResult(BaseModel):
    """Result from vector similarity search operations."""

    content_id: UUID = Field(..., description="Unique identifier for the content")
    document_id: UUID = Field(..., description="Source document identifier")
    page_number: int = Field(..., description="Page number in the document")
    content_type: str = Field(..., description="Type of content (text, table, etc.)")
    text_content: str = Field(..., description="The actual text content")
    confidence_score: float = Field(..., description="Extraction confidence score")
    similarity_score: float = Field(..., description="Similarity score from search")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional content metadata"
    )


class QdrantError(Exception):
    """Base exception for Qdrant operations."""

    def __init__(self, message: str, error_type: str = "qdrant_error"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class QdrantConnectionError(QdrantError):
    """Exception for Qdrant connection issues."""

    def __init__(self, message: str):
        super().__init__(message, "qdrant_connection_error")


class QdrantCollectionError(QdrantError):
    """Exception for Qdrant collection operations."""

    def __init__(self, message: str):
        super().__init__(message, "qdrant_collection_error")


class QdrantOperationError(QdrantError):
    """Exception for Qdrant CRUD operations."""

    def __init__(self, message: str):
        super().__init__(message, "qdrant_operation_error")


class QdrantClient:
    """
    Async Qdrant vector database client.

    Provides methods for collection management, content storage, similarity search,
    and deletion operations. Supports both single-tenant and multi-tenant modes
    based on configuration.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initialize Qdrant client.

        Args:
            url: Qdrant server URL. Defaults to settings.qdrant_url
            api_key: Qdrant API key. Defaults to settings.qdrant_api_key
            collection_name: Default collection name. Defaults to settings.qdrant_collection_name
        """
        self._url = url or settings.qdrant_url
        self._api_key = api_key or settings.qdrant_api_key
        self._default_collection = collection_name or settings.qdrant_collection_name
        self._client: Optional[AsyncQdrantClient] = None

    async def _get_client(self) -> AsyncQdrantClient:
        """Get or create Qdrant client instance."""
        if self._client is None:
            try:
                self._client = AsyncQdrantClient(
                    url=self._url,
                    api_key=self._api_key,
                )
            except Exception as e:
                raise QdrantConnectionError(f"Failed to connect to Qdrant: {str(e)}")
        return self._client

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 384,
        distance: models.Distance = models.Distance.COSINE,
    ) -> bool:
        """
        Create a new collection in Qdrant.

        Args:
            collection_name: Name of the collection to create
            vector_size: Dimension of vectors (default: 384 for sentence-transformers)
            distance: Distance metric for similarity calculation

        Returns:
            True if collection created successfully, False if already exists

        Raises:
            QdrantCollectionError: If collection creation fails
        """
        try:
            client = await self._get_client()

            # Check if collection already exists
            collections = await client.get_collections()
            existing_names = [col.name for col in collections.collections]
            
            if collection_name in existing_names:
                return False

            # Create collection with vector configuration
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=distance,
                ),
                # Optimize for search performance
                optimizers_config=models.OptimizersConfig(
                    default_segment_number=2,
                ),
                # Enable indexing for payload fields used in filtering
                hnsw_config=models.HnswConfig(
                    m=16,
                    ef_construct=100,
                ),
            )

            # Create indexes for common filter fields
            await self._create_payload_indexes(client, collection_name)

            return True

        except ResponseHandlingException as e:
            raise QdrantCollectionError(f"Failed to create collection '{collection_name}': {str(e)}")
        except Exception as e:
            raise QdrantError(f"Unexpected error creating collection '{collection_name}': {str(e)}")

    async def _create_payload_indexes(self, client: AsyncQdrantClient, collection_name: str) -> None:
        """Create indexes for payload fields used in filtering."""
        index_fields = [
            ("document_id", models.PayloadSchemaType.KEYWORD),
            ("content_type", models.PayloadSchemaType.KEYWORD),
            ("page_number", models.PayloadSchemaType.INTEGER),
            ("confidence_score", models.PayloadSchemaType.FLOAT),
        ]

        for field_name, field_type in index_fields:
            try:
                await client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                )
            except ResponseHandlingException:
                # Index might already exist, ignore
                pass

    async def upsert_content(
        self,
        collection_name: str,
        content_id: UUID,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> bool:
        """
        Insert or update content in the collection.

        Args:
            collection_name: Target collection name
            content_id: Unique identifier for the content
            embedding: Vector embedding for the content
            payload: Metadata payload including document_id, content_type, etc.

        Returns:
            True if operation successful

        Raises:
            QdrantOperationError: If upsert operation fails
        """
        try:
            client = await self._get_client()

            # Convert UUID to string for storage
            point_id = str(content_id)

            # Ensure required payload fields are present
            required_fields = ["document_id", "content_type", "page_number", "confidence_score"]
            for field in required_fields:
                if field not in payload:
                    raise QdrantOperationError(f"Missing required payload field: {field}")

            # Convert UUID fields to strings for JSON serialization
            if isinstance(payload.get("document_id"), UUID):
                payload["document_id"] = str(payload["document_id"])
            if isinstance(payload.get("content_id"), UUID):
                payload["content_id"] = str(payload["content_id"])

            # Create point for upsert
            point = models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )

            # Perform upsert operation
            await client.upsert(
                collection_name=collection_name,
                points=[point],
            )

            return True

        except ResponseHandlingException as e:
            raise QdrantOperationError(f"Failed to upsert content '{content_id}': {str(e)}")
        except Exception as e:
            raise QdrantError(f"Unexpected error upserting content '{content_id}': {str(e)}")

    async def search_similar(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Search for similar content in the collection.

        Args:
            collection_name: Collection to search in
            query_embedding: Query vector for similarity search
            limit: Maximum number of results to return
            filters: Optional filters for payload fields
            min_score: Minimum similarity score threshold

        Returns:
            List of SearchResult objects ordered by similarity score

        Raises:
            QdrantOperationError: If search operation fails
        """
        try:
            client = await self._get_client()

            # Build filter conditions
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if key == "document_id" and isinstance(value, UUID):
                        value = str(value)
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value),
                        )
                    )
                
                if conditions:
                    search_filter = models.Filter(must=conditions)

            # Perform similarity search
            search_results = await client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                score_threshold=min_score,
                with_payload=True,
                with_vectors=False,  # Don't return vectors to save bandwidth
            )

            # Convert to SearchResult objects
            results = []
            for result in search_results:
                payload = result.payload or {}
                
                # Extract required fields with defaults
                content_id = UUID(payload.get("content_id", result.id))
                document_id = UUID(payload.get("document_id"))
                page_number = payload.get("page_number", 1)
                content_type = payload.get("content_type", "text")
                text_content = payload.get("text_content", "")
                confidence_score = payload.get("confidence_score", 0.0)
                
                # Extract metadata, excluding system fields
                metadata = {
                    k: v for k, v in payload.items()
                    if k not in ["content_id", "document_id", "page_number", 
                                "content_type", "text_content", "confidence_score"]
                }

                search_result = SearchResult(
                    content_id=content_id,
                    document_id=document_id,
                    page_number=page_number,
                    content_type=content_type,
                    text_content=text_content,
                    confidence_score=confidence_score,
                    similarity_score=result.score,
                    metadata=metadata,
                )
                results.append(search_result)

            return results

        except ResponseHandlingException as e:
            raise QdrantOperationError(f"Failed to search collection '{collection_name}': {str(e)}")
        except Exception as e:
            raise QdrantError(f"Unexpected error searching collection '{collection_name}': {str(e)}")

    async def delete_content(self, collection_name: str, content_id: UUID) -> bool:
        """
        Delete specific content from the collection.

        Args:
            collection_name: Collection containing the content
            content_id: Unique identifier of content to delete

        Returns:
            True if deletion successful

        Raises:
            QdrantOperationError: If deletion fails
        """
        try:
            client = await self._get_client()

            point_id = str(content_id)

            # Delete the point
            await client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=[point_id],
                ),
            )

            return True

        except ResponseHandlingException as e:
            raise QdrantOperationError(f"Failed to delete content '{content_id}': {str(e)}")
        except Exception as e:
            raise QdrantError(f"Unexpected error deleting content '{content_id}': {str(e)}")

    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete an entire collection.

        Args:
            collection_name: Name of collection to delete

        Returns:
            True if deletion successful, False if collection doesn't exist

        Raises:
            QdrantCollectionError: If deletion fails
        """
        try:
            client = await self._get_client()

            # Check if collection exists
            collections = await client.get_collections()
            existing_names = [col.name for col in collections.collections]
            
            if collection_name not in existing_names:
                return False

            # Delete the collection
            await client.delete_collection(collection_name=collection_name)

            return True

        except ResponseHandlingException as e:
            raise QdrantCollectionError(f"Failed to delete collection '{collection_name}': {str(e)}")
        except Exception as e:
            raise QdrantError(f"Unexpected error deleting collection '{collection_name}': {str(e)}")

    async def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection.

        Args:
            collection_name: Name of collection to inspect

        Returns:
            Collection info dict or None if collection doesn't exist

        Raises:
            QdrantOperationError: If operation fails
        """
        try:
            client = await self._get_client()

            # Get collection info
            collection_info = await client.get_collection(collection_name=collection_name)
            
            return {
                "name": collection_info.config.params.vectors.size,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status,
            }

        except ResponseHandlingException:
            # Collection doesn't exist
            return None
        except Exception as e:
            raise QdrantOperationError(f"Failed to get collection info '{collection_name}': {str(e)}")

    def get_account_collection_name(self, account_id: UUID) -> str:
        """
        Generate collection name for account-specific collections.

        Args:
            account_id: Account UUID

        Returns:
            Collection name in format 'account_{account_id}'
        """
        return f"account_{str(account_id).replace('-', '_')}"

    async def close(self) -> None:
        """Close the Qdrant client connection."""
        if self._client:
            await self._client.close()
            self._client = None


# Global client instance
_client_instance: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """
    Get or create global Qdrant client instance.

    Returns:
        QdrantClient instance configured with application settings
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = QdrantClient()
    return _client_instance


async def cleanup_qdrant_client() -> None:
    """Close global Qdrant client connection."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None