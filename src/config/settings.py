"""
Application settings and configuration management.

Uses Pydantic Settings for environment variable parsing and validation.
Supports local and S3 storage backends via STORAGE_BACKEND toggle.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application settings
    app_name: str = "renewable-doc-pipeline"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="development", description="Environment name")

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # Storage backend configuration
    storage_backend: Literal["local", "s3"] = Field(
        default="local",
        description="Storage backend: 'local' for filesystem, 's3' for AWS S3",
    )

    # Local storage settings (when storage_backend='local')
    local_storage_path: str = Field(
        default="./data",
        description="Local storage directory for documents and artifacts",
    )

    # AWS S3 settings (when storage_backend='s3')
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-west-2"
    s3_bucket_name: str | None = None

    # Database settings
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/renewable_docs",
        description="PostgreSQL database connection URL",
    )

    # Qdrant vector database settings
    qdrant_url: str = Field(
        default="http://localhost:6333", description="Qdrant vector database URL"
    )
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "renewable_documents"

    # Document processing limits
    max_file_size_mb: int = 150
    max_pages_per_document: int = 300
    max_documents_per_account: int = 200

    # OCR settings
    ocr_engine: Literal["tesseract", "textract"] = "tesseract"
    tesseract_language: str = "eng"
    ocr_confidence_threshold: float = 0.7

    # Rate limiting
    search_rate_limit: int = 60  # requests per minute
    qa_rate_limit: int = 30  # requests per minute

    # Monitoring and observability
    metrics_enabled: bool = True
    metrics_api_key: str | None = None
    log_level: str = "INFO"

    # Security
    api_key_header: str = "X-API-Key"
    cors_origins: list[str] = ["*"]

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def is_local_storage(self) -> bool:
        """Check if using local storage backend."""
        return self.storage_backend == "local"

    @property
    def is_s3_storage(self) -> bool:
        """Check if using S3 storage backend."""
        return self.storage_backend == "s3"

    def validate_storage_config(self) -> None:
        """Validate storage backend configuration."""
        if self.is_s3_storage:
            if not self.s3_bucket_name:
                raise ValueError(
                    "S3_BUCKET_NAME required when using S3 storage backend"
                )
            if not self.aws_access_key_id or not self.aws_secret_access_key:
                raise ValueError(
                    "AWS credentials required when using S3 storage backend"
                )


# Global settings instance
settings = Settings()
