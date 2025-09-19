"""
Local filesystem storage backend for demo/testing environments.

This module provides a local storage implementation that mirrors the S3 client interface
for seamless switching between storage backends. It maintains the same directory structure
as S3 and supports all required operations for the renewable energy document pipeline.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID

import aiofiles


class LocalStorageError(Exception):
    """Base exception for local storage operations."""

    def __init__(self, message: str, operation: str = "", path: str = "") -> None:
        super().__init__(message)
        self.operation = operation
        self.path = path


class LocalStorageClient:
    """
    Local filesystem storage client that mirrors S3 interface.
    
    Provides async file operations with proper error handling and directory management.
    Maintains the same path structure as S3 for seamless backend switching.
    
    Path structure:
    - Original PDF files: {account_id}/{document_id}/original.pdf
    - Extracted images: {account_id}/{document_id}/images/{content_id}.{ext}
    - Processing artifacts: {account_id}/{document_id}/artifacts/
    """

    def __init__(self, base_path: str = "./data") -> None:
        """
        Initialize local storage client.
        
        Args:
            base_path: Root directory for local storage operations
        """
        self.base_path = Path(base_path).resolve()
        self._ensure_base_directory()

    def _ensure_base_directory(self) -> None:
        """Create base storage directory if it doesn't exist."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise LocalStorageError(
                f"Failed to create base storage directory: {e}",
                operation="init",
                path=str(self.base_path)
            ) from e

    def _get_document_path(self, account_id: UUID, document_id: UUID, filename: str) -> Path:
        """
        Get the full path for a document file.
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            filename: Filename (typically 'original.pdf')
            
        Returns:
            Path object for the document file
        """
        return self.base_path / str(account_id) / str(document_id) / filename

    def _get_artifact_path(self, account_id: UUID, document_id: UUID, artifact_name: str) -> Path:
        """
        Get the full path for an artifact file.
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            artifact_name: Name of the artifact file
            
        Returns:
            Path object for the artifact file
        """
        return self.base_path / str(account_id) / str(document_id) / "artifacts" / artifact_name

    def _get_account_path(self, account_id: UUID) -> Path:
        """
        Get the full path for an account directory.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Path object for the account directory
        """
        return self.base_path / str(account_id)

    async def upload_document(
        self, 
        account_id: UUID, 
        document_id: UUID, 
        file_data: bytes, 
        filename: str = "original.pdf"
    ) -> str:
        """
        Upload a document to local storage.
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            file_data: Binary file content
            filename: Filename for the stored file
            
        Returns:
            Local file path as string
            
        Raises:
            LocalStorageError: If upload operation fails
        """
        file_path = self._get_document_path(account_id, document_id, filename)
        
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file asynchronously
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)
                
            return str(file_path)
            
        except OSError as e:
            raise LocalStorageError(
                f"Failed to upload document: {e}",
                operation="upload_document",
                path=str(file_path)
            ) from e

    async def download_document(self, local_path: str) -> bytes:
        """
        Download a document from local storage.
        
        Args:
            local_path: Local file path
            
        Returns:
            Binary file content
            
        Raises:
            LocalStorageError: If download operation fails
        """
        file_path = Path(local_path)
        
        if not file_path.exists():
            raise LocalStorageError(
                f"File not found: {local_path}",
                operation="download_document",
                path=local_path
            )
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                return await f.read()
                
        except OSError as e:
            raise LocalStorageError(
                f"Failed to download document: {e}",
                operation="download_document",
                path=local_path
            ) from e

    async def delete_document(self, local_path: str) -> bool:
        """
        Delete a document from local storage.
        
        Args:
            local_path: Local file path
            
        Returns:
            True if file was deleted, False if file didn't exist
            
        Raises:
            LocalStorageError: If delete operation fails
        """
        file_path = Path(local_path)
        
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            
            # Clean up empty parent directories
            parent = file_path.parent
            while parent != self.base_path and parent.exists():
                try:
                    if not any(parent.iterdir()):  # Directory is empty
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
                except OSError:
                    break
                    
            return True
            
        except OSError as e:
            raise LocalStorageError(
                f"Failed to delete document: {e}",
                operation="delete_document",
                path=local_path
            ) from e

    async def upload_artifact(
        self, 
        account_id: UUID, 
        document_id: UUID, 
        artifact_name: str, 
        data: bytes
    ) -> str:
        """
        Upload a processing artifact to local storage.
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            artifact_name: Name of the artifact file
            data: Binary artifact content
            
        Returns:
            Local file path as string
            
        Raises:
            LocalStorageError: If upload operation fails
        """
        file_path = self._get_artifact_path(account_id, document_id, artifact_name)
        
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file asynchronously
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(data)
                
            return str(file_path)
            
        except OSError as e:
            raise LocalStorageError(
                f"Failed to upload artifact: {e}",
                operation="upload_artifact",
                path=str(file_path)
            ) from e

    async def delete_account_data(self, account_id: UUID) -> bool:
        """
        Delete all data for an account (cleanup operation).
        
        Args:
            account_id: Account identifier
            
        Returns:
            True if account data was deleted, False if account directory didn't exist
            
        Raises:
            LocalStorageError: If delete operation fails
        """
        account_path = self._get_account_path(account_id)
        
        if not account_path.exists():
            return False
        
        try:
            shutil.rmtree(account_path)
            return True
            
        except OSError as e:
            raise LocalStorageError(
                f"Failed to delete account data: {e}",
                operation="delete_account_data",
                path=str(account_path)
            ) from e

    def get_document_directory(self, account_id: UUID, document_id: UUID) -> str:
        """
        Get the directory path for a document (useful for organizing artifacts).
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            
        Returns:
            Directory path as string
        """
        return str(self.base_path / str(account_id) / str(document_id))

    def get_images_directory(self, account_id: UUID, document_id: UUID) -> str:
        """
        Get the directory path for extracted images.
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            
        Returns:
            Images directory path as string
        """
        return str(self.base_path / str(account_id) / str(document_id) / "images")

    async def ensure_images_directory(self, account_id: UUID, document_id: UUID) -> str:
        """
        Ensure images directory exists and return its path.
        
        Args:
            account_id: Account identifier
            document_id: Document identifier
            
        Returns:
            Images directory path as string
            
        Raises:
            LocalStorageError: If directory creation fails
        """
        images_dir = Path(self.get_images_directory(account_id, document_id))
        
        try:
            images_dir.mkdir(parents=True, exist_ok=True)
            return str(images_dir)
            
        except OSError as e:
            raise LocalStorageError(
                f"Failed to create images directory: {e}",
                operation="ensure_images_directory",
                path=str(images_dir)
            ) from e

    def is_local_path(self, path: str) -> bool:
        """
        Check if a path is within the local storage base directory.
        
        Args:
            path: File path to check
            
        Returns:
            True if path is within local storage, False otherwise
        """
        try:
            file_path = Path(path).resolve()
            return file_path.is_relative_to(self.base_path)
        except (OSError, ValueError):
            return False