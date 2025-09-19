"""
Storage layer for renewable energy PDF processing pipeline.

This package provides data storage abstractions and clients for:
- S3 object storage for document files and artifacts
- Qdrant vector database for embeddings and semantic search
- PostgreSQL for relational data and ACID transactions
- Local storage backend for development and testing
- Database migrations for schema management

The storage layer supports both cloud deployment (S3) and local development
(filesystem) modes via the STORAGE_BACKEND configuration setting.
"""

from .s3_client import S3StorageClient, S3StorageError
from .qdrant_client import QdrantClient, QdrantError, SearchResult
from .postgres_client import PostgresClient, DatabaseError
from .local_storage import LocalStorageClient, LocalStorageError
from .migrations import MigrationRunner, migrate_to_latest, get_migration_status

__all__ = [
    "S3StorageClient",
    "S3StorageError", 
    "QdrantClient",
    "QdrantError",
    "SearchResult",
    "PostgresClient",
    "DatabaseError",
    "LocalStorageClient", 
    "LocalStorageError",
    "MigrationRunner",
    "migrate_to_latest",
    "get_migration_status",
]