"""
Document processing service with LlamaIndex integration.

This service handles document processing operations including PDF parsing,
content extraction, chunking, embedding generation, and storage operations
for the renewable energy PDF processing pipeline.
"""

import hashlib
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import SimpleDirectoryReader

from ..config.settings import settings
from ..models.document import Document as DocumentModel, ProcessingStatus
from ..models.extracted_content import ContentType, ExtractedContent
from ..storage.local_storage import LocalStorageClient, LocalStorageError
from ..storage.s3_client import S3Client, S3StorageError

logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Base exception for document processing operations."""

    def __init__(self, message: str, error_type: str = "processing_error", details: Dict[str, Any] | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class ValidationError(DocumentProcessingError):
    """Exception for validation errors during document processing."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None):
        super().__init__(message, "validation_error", details)


class ExtractionError(DocumentProcessingError):
    """Exception for content extraction failures."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None):
        super().__init__(message, "extraction_error", details)


class EmbeddingError(DocumentProcessingError):
    """Exception for embedding generation failures."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None):
        super().__init__(message, "embedding_error", details)


class DocumentService:
    """
    Document processing service with LlamaIndex integration.
    
    Handles the complete document processing pipeline including:
    - PDF parsing and content extraction
    - Text chunking and embedding generation
    - Storage operations for content and metadata
    - Processing status tracking
    """

    def __init__(self):
        """Initialize document service with storage clients."""
        self.storage_client = self._get_storage_client()
        self.node_parser = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50,
            separator=" ",
            paragraph_separator="\n\n",
        )

    def _get_storage_client(self) -> LocalStorageClient | S3Client:
        """Get appropriate storage client based on configuration."""
        if settings.is_local_storage:
            return LocalStorageClient(base_path=settings.local_storage_path)
        else:
            return S3Client()

    def _calculate_content_hash(self, file_data: bytes) -> str:
        """Calculate SHA-256 hash for file content deduplication."""
        return hashlib.sha256(file_data).hexdigest()

    async def process_document(
        self, 
        document_id: UUID, 
        file_data: bytes, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Process a document through the complete pipeline.
        
        Args:
            document_id: Unique document identifier
            file_data: PDF file content as bytes
            metadata: Document metadata including account_id, filename
            
        Returns:
            True if processing completed successfully
            
        Raises:
            DocumentProcessingError: If processing fails
            ValidationError: If inputs are invalid
        """
        try:
            # Validate inputs
            if not file_data:
                raise ValidationError("File data cannot be empty")
            
            if not metadata.get("account_id") or not metadata.get("filename"):
                raise ValidationError("account_id and filename are required in metadata")

            account_id = metadata["account_id"]
            filename = metadata["filename"]
            
            logger.info(f"Starting document processing for document_id={document_id}")
            
            # Store original document
            if settings.is_local_storage:
                document_path = await self.storage_client.upload_document(
                    account_id, document_id, file_data, "original.pdf"
                )
            else:
                document_path = await self.storage_client.upload_document(
                    str(account_id), str(document_id), file_data, filename
                )
            
            # Extract content chunks from the stored document
            chunks = await self.extract_content_chunks(document_path)
            
            # Generate embeddings for text chunks
            text_chunks = [chunk.text_content for chunk in chunks]
            embeddings = await self.generate_embeddings(text_chunks)
            
            # Update chunks with embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.vector_embedding = embedding
            
            # Store document content
            success = await self.store_document_content(document_id, chunks)
            
            if success:
                logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks")
                return True
            else:
                raise DocumentProcessingError("Failed to store document content")
                
        except (LocalStorageError, S3StorageError) as e:
            logger.error(f"Storage error processing document {document_id}: {e}")
            raise DocumentProcessingError(f"Storage operation failed: {e}", details={"document_id": str(document_id)})
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            raise DocumentProcessingError(f"Document processing failed: {e}", details={"document_id": str(document_id)})

    async def get_document_status(self, document_id: UUID) -> ProcessingStatus:
        """
        Get the current processing status of a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Current processing status
            
        Raises:
            DocumentProcessingError: If status retrieval fails
        """
        try:
            # This would typically query the database for the document status
            # For now, return a default status - this should be implemented
            # when database operations are added
            logger.info(f"Retrieving status for document {document_id}")
            return ProcessingStatus.PROCESSING
            
        except Exception as e:
            logger.error(f"Error retrieving document status for {document_id}: {e}")
            raise DocumentProcessingError(f"Failed to retrieve document status: {e}")

    async def extract_content_chunks(self, file_path: str) -> List[ExtractedContent]:
        """
        Extract content chunks from a PDF file using LlamaIndex.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of extracted content chunks with metadata
            
        Raises:
            ExtractionError: If content extraction fails
        """
        try:
            # For local storage, use the path directly
            # For S3, we would need to download first to a temp file
            if settings.is_s3_storage:
                # Download from S3 to temporary file
                file_data = await self.storage_client.download_document(file_path)
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_file.write(file_data)
                    temp_file.flush()
                    actual_file_path = temp_file.name
            else:
                actual_file_path = file_path
            
            # Load documents using LlamaIndex SimpleDirectoryReader
            documents = SimpleDirectoryReader(
                input_files=[actual_file_path]
            ).load_data()
            
            if not documents:
                raise ExtractionError("No content could be extracted from the document")
            
            # Parse documents into nodes/chunks
            nodes = self.node_parser.get_nodes_from_documents(documents)
            
            chunks = []
            for i, node in enumerate(nodes):
                # Extract metadata from the node
                page_number = node.metadata.get("page_label", 1)
                if isinstance(page_number, str):
                    try:
                        page_number = int(page_number)
                    except ValueError:
                        page_number = 1
                
                # Create ExtractedContent instance
                chunk = ExtractedContent(
                    content_id=UUID(int=i),  # Generate deterministic UUID from index
                    document_id=UUID(int=0),  # Will be set by caller
                    page_number=page_number,
                    content_type=ContentType.TEXT,
                    text_content=node.text,
                    metadata={
                        "node_id": node.node_id,
                        "file_path": node.metadata.get("file_path", ""),
                        "file_name": node.metadata.get("file_name", ""),
                        "chunk_index": i,
                    },
                    vector_embedding=[],  # Will be populated by generate_embeddings
                    bounding_box=None,
                    confidence_score=0.9,  # Default confidence for LlamaIndex extraction
                    is_ocr_generated=False,  # LlamaIndex typically extracts native text
                    extracted_at=datetime.utcnow(),
                )
                chunks.append(chunk)
            
            # Clean up temporary file if created
            if settings.is_s3_storage:
                Path(actual_file_path).unlink(missing_ok=True)
            
            logger.info(f"Extracted {len(chunks)} content chunks from {file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {e}")
            raise ExtractionError(f"Content extraction failed: {e}", details={"file_path": file_path})

    async def generate_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for text chunks.
        
        Args:
            text_chunks: List of text content to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            # For now, return dummy embeddings
            # This should be replaced with actual embedding model integration
            # when LlamaIndex embedding service is implemented
            
            embeddings = []
            for chunk in text_chunks:
                # Generate a simple hash-based embedding for demonstration
                # In production, this would use a proper embedding model
                chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
                # Convert hex string to list of floats (normalized to 0-1 range)
                embedding = [int(chunk_hash[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
                embeddings.append(embedding)
            
            logger.info(f"Generated embeddings for {len(text_chunks)} text chunks")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")

    async def store_document_content(
        self, 
        document_id: UUID, 
        chunks: List[ExtractedContent]
    ) -> bool:
        """
        Store document content chunks in the vector database.
        
        Args:
            document_id: Document identifier
            chunks: List of extracted content chunks
            
        Returns:
            True if storage succeeded
            
        Raises:
            DocumentProcessingError: If storage fails
        """
        try:
            # Update document_id in all chunks
            for chunk in chunks:
                chunk.document_id = document_id
            
            # Store chunks in vector database (Qdrant)
            # This would integrate with the Qdrant client
            # For now, just log the operation
            logger.info(f"Storing {len(chunks)} content chunks for document {document_id}")
            
            # TODO: Implement actual Qdrant storage when qdrant_client is available
            # await self.qdrant_client.store_chunks(chunks)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing document content for {document_id}: {e}")
            raise DocumentProcessingError(f"Content storage failed: {e}")

    async def delete_document_content(self, document_id: UUID) -> bool:
        """
        Delete all content for a document from storage.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if deletion succeeded
            
        Raises:
            DocumentProcessingError: If deletion fails
        """
        try:
            # Delete from vector database
            # This would integrate with the Qdrant client
            logger.info(f"Deleting content for document {document_id}")
            
            # TODO: Implement actual Qdrant deletion when qdrant_client is available
            # await self.qdrant_client.delete_document_content(document_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document content for {document_id}: {e}")
            raise DocumentProcessingError(f"Content deletion failed: {e}")


# Global document service instance
document_service = DocumentService()