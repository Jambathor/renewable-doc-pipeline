"""
S3 storage client for document storage operations.

Implements the storage strategy for renewable energy PDF processing pipeline:
- Original PDF files: {account_id}/{document_id}/original.pdf
- Extracted images: {account_id}/{document_id}/images/{content_id}.{ext}
- Processing artifacts: {account_id}/{document_id}/artifacts/

Uses boto3 with async operations, error handling, and retry logic.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from ..config.settings import settings

logger = logging.getLogger(__name__)


class S3StorageError(Exception):
    """Base exception for S3 storage operations."""

    def __init__(self, message: str, error_type: str = "storage_error", details: Optional[dict] = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class S3ConnectionError(S3StorageError):
    """Exception for S3 connection failures."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "connection_error", details)


class S3OperationError(S3StorageError):
    """Exception for S3 operation failures."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "operation_error", details)


def async_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator for async retry logic with exponential backoff."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (ClientError, BotoCoreError) as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    
                    wait_time = delay * (2 ** attempt)
                    logger.warning(
                        f"S3 operation failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
            
            # Re-raise the last exception if all retries failed
            if isinstance(last_exception, ClientError):
                raise S3OperationError(
                    f"S3 operation failed after {max_retries + 1} attempts: {last_exception}",
                    details={"error_code": last_exception.response.get("Error", {}).get("Code")}
                )
            else:
                raise S3ConnectionError(
                    f"S3 connection failed after {max_retries + 1} attempts: {last_exception}"
                )
        
        return wrapper
    return decorator


class S3Client:
    """
    Async S3 client for document storage operations.
    
    Supports the storage strategy defined in data-model.md with proper
    error handling, retry logic, and async operations.
    """

    def __init__(self):
        """Initialize S3 client with configuration from settings."""
        self._client: Optional[Any] = None
        self._bucket_name = settings.s3_bucket_name
        
        if not self._bucket_name:
            raise S3StorageError(
                "S3 bucket name not configured",
                error_type="configuration_error"
            )

    def _get_client(self) -> Any:
        """Get or create boto3 S3 client with retry configuration."""
        if self._client is None:
            try:
                # Configure retry strategy and timeouts
                config = Config(
                    region_name=settings.aws_region,
                    retries={"max_attempts": 2, "mode": "adaptive"},
                    connect_timeout=10,
                    read_timeout=30,
                )
                
                self._client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    config=config,
                )
                
                logger.info(f"S3 client initialized for bucket: {self._bucket_name}")
                
            except Exception as e:
                raise S3ConnectionError(f"Failed to initialize S3 client: {e}")
        
        return self._client

    def _generate_document_key(self, account_id: str, document_id: str, filename: str) -> str:
        """Generate S3 key for original document storage."""
        # Use original.pdf as the filename to follow storage strategy
        return f"{account_id}/{document_id}/original.pdf"

    def _generate_image_key(self, account_id: str, document_id: str, content_id: str, extension: str) -> str:
        """Generate S3 key for extracted image storage."""
        return f"{account_id}/{document_id}/images/{content_id}.{extension}"

    def _generate_artifact_key(self, account_id: str, document_id: str, artifact_name: str) -> str:
        """Generate S3 key for processing artifact storage."""
        return f"{account_id}/{document_id}/artifacts/{artifact_name}"

    @async_retry(max_retries=3, delay=1.0)
    async def upload_document(
        self, 
        account_id: str, 
        document_id: str, 
        file_data: bytes, 
        filename: str
    ) -> str:
        """
        Upload original PDF document to S3.
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            file_data: PDF file content as bytes
            filename: Original filename (for metadata only)
            
        Returns:
            S3 key for the uploaded document
            
        Raises:
            S3StorageError: If upload fails
        """
        s3_key = self._generate_document_key(account_id, document_id, filename)
        client = self._get_client()
        
        try:
            # Run the upload in a thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.put_object(
                    Bucket=self._bucket_name,
                    Key=s3_key,
                    Body=file_data,
                    ContentType="application/pdf",
                    Metadata={
                        "original_filename": filename,
                        "account_id": account_id,
                        "document_id": document_id,
                    }
                )
            )
            
            logger.info(f"Successfully uploaded document to S3: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to upload document to S3 key {s3_key}: {e}")
            raise

    @async_retry(max_retries=3, delay=1.0)
    async def download_document(self, s3_key: str) -> bytes:
        """
        Download document from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Document content as bytes
            
        Raises:
            S3StorageError: If download fails
        """
        client = self._get_client()
        
        try:
            # Run the download in a thread pool to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.get_object(Bucket=self._bucket_name, Key=s3_key)
            )
            
            # Read the body content
            content = response["Body"].read()
            logger.info(f"Successfully downloaded document from S3: {s3_key}")
            return content
            
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                raise S3OperationError(
                    f"Document not found in S3: {s3_key}",
                    details={"s3_key": s3_key}
                )
            logger.error(f"Failed to download document from S3 key {s3_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to download document from S3 key {s3_key}: {e}")
            raise

    @async_retry(max_retries=3, delay=1.0)
    async def delete_document(self, s3_key: str) -> bool:
        """
        Delete document from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            S3StorageError: If deletion fails
        """
        client = self._get_client()
        
        try:
            # Run the deletion in a thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.delete_object(Bucket=self._bucket_name, Key=s3_key)
            )
            
            logger.info(f"Successfully deleted document from S3: {s3_key}")
            return True
            
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                logger.warning(f"Document not found for deletion in S3: {s3_key}")
                return False
            logger.error(f"Failed to delete document from S3 key {s3_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to delete document from S3 key {s3_key}: {e}")
            raise

    @async_retry(max_retries=3, delay=1.0)
    async def upload_artifact(
        self, 
        account_id: str, 
        document_id: str, 
        artifact_name: str, 
        data: bytes
    ) -> str:
        """
        Upload processing artifact to S3.
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            artifact_name: Name of the artifact file
            data: Artifact content as bytes
            
        Returns:
            S3 key for the uploaded artifact
            
        Raises:
            S3StorageError: If upload fails
        """
        s3_key = self._generate_artifact_key(account_id, document_id, artifact_name)
        client = self._get_client()
        
        try:
            # Determine content type based on artifact name
            content_type = "application/octet-stream"
            if artifact_name.endswith(".json"):
                content_type = "application/json"
            elif artifact_name.endswith(".txt"):
                content_type = "text/plain"
            elif artifact_name.endswith((".jpg", ".jpeg")):
                content_type = "image/jpeg"
            elif artifact_name.endswith(".png"):
                content_type = "image/png"
            
            # Run the upload in a thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.put_object(
                    Bucket=self._bucket_name,
                    Key=s3_key,
                    Body=data,
                    ContentType=content_type,
                    Metadata={
                        "account_id": account_id,
                        "document_id": document_id,
                        "artifact_type": artifact_name,
                    }
                )
            )
            
            logger.info(f"Successfully uploaded artifact to S3: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to upload artifact to S3 key {s3_key}: {e}")
            raise

    @async_retry(max_retries=3, delay=1.0)
    async def delete_account_data(self, account_id: str) -> bool:
        """
        Delete all data for an account from S3.
        
        Args:
            account_id: Account identifier
            
        Returns:
            True if deletion completed successfully
            
        Raises:
            S3StorageError: If deletion fails
        """
        client = self._get_client()
        prefix = f"{account_id}/"
        
        try:
            # List all objects with the account prefix
            paginator = client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self._bucket_name, Prefix=prefix)
            
            deleted_count = 0
            for page in pages:
                if "Contents" in page:
                    # Prepare objects for batch deletion
                    objects_to_delete = [{"Key": obj["Key"]} for obj in page["Contents"]]
                    
                    if objects_to_delete:
                        # Run deletion in thread pool
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: client.delete_objects(
                                Bucket=self._bucket_name,
                                Delete={"Objects": objects_to_delete}
                            )
                        )
                        deleted_count += len(objects_to_delete)
            
            logger.info(f"Successfully deleted {deleted_count} objects for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete account data for {account_id}: {e}")
            raise


# Global S3 client instance
s3_client = S3Client()