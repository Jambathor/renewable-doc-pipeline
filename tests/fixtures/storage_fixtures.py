"""
Storage fixtures for testing with local backend.

Provides test fixtures for local storage, database connections,
and Qdrant vector database for hermetic testing without AWS dependencies.
"""

import os
import shutil
import tempfile
from collections.abc import Generator, Iterator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.config.settings import Settings


@pytest.fixture
def temp_storage_dir() -> Iterator[str]:
    """Create a temporary directory for local storage testing."""
    temp_dir = tempfile.mkdtemp(prefix="renewable_test_")
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def local_storage_settings(temp_storage_dir: str) -> Settings:
    """Test settings configured for local storage backend."""
    return Settings(
        storage_backend="local",
        local_storage_path=temp_storage_dir,
        database_url="sqlite:///test.db",
        qdrant_url="memory",  # In-memory Qdrant for testing
        debug=True,
        environment="test",
    )


@pytest.fixture
def s3_storage_settings() -> Settings:
    """Test settings configured for S3 storage backend (mocked)."""
    return Settings(
        storage_backend="s3",
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret",
        aws_region="us-west-2",
        s3_bucket_name="test-bucket",
        debug=True,
        environment="test",
    )


@pytest.fixture
def mock_s3_client():
    """Mock AWS S3 client for testing S3 operations."""
    with patch("boto3.client") as mock_boto3:
        mock_client = Mock()
        mock_boto3.return_value = mock_client

        # Configure common S3 responses
        mock_client.put_object.return_value = {"ETag": '"test-etag"'}
        mock_client.get_object.return_value = {
            "Body": Mock(read=Mock(return_value=b"test content")),
            "ContentLength": 12,
        }
        mock_client.delete_object.return_value = {}
        mock_client.head_object.return_value = {"ContentLength": 12}

        yield mock_client


@pytest.fixture
def test_qdrant_client() -> Generator[QdrantClient, None, None]:
    """In-memory Qdrant client for testing."""
    client = QdrantClient(":memory:")

    # Create test collection
    collection_name = "test_renewable_documents"
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    yield client


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for testing uploads."""
    # Minimal PDF content (not a real PDF, but sufficient for unit tests)
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF"


@pytest.fixture
def sample_document_metadata() -> dict:
    """Sample document metadata for testing."""
    return {
        "title": "Test Solar Report",
        "tags": ["solar", "efficiency", "test"],
        "source_url": "https://example.com/test-report.pdf",
        "uploaded_by": "test@example.com",
    }


@pytest.fixture
def test_document_files(temp_storage_dir: str) -> dict[str, Path]:
    """Create test document files in temporary storage."""
    storage_path = Path(temp_storage_dir)

    # Create directory structure
    doc_id = "550e8400-e29b-41d4-a716-446655440000"
    doc_dir = storage_path / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Create test files
    files = {
        "original_pdf": doc_dir / "original.pdf",
        "extracted_text": doc_dir / "extracted.txt",
        "metadata": doc_dir / "metadata.json",
    }

    # Write sample content
    files["original_pdf"].write_bytes(b"%PDF-1.4\n%%EOF")
    files["extracted_text"].write_text("Sample extracted text content")
    files["metadata"].write_text('{"title": "Test Document"}')

    return files


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session_mock = Mock()
    session_mock.query.return_value = session_mock
    session_mock.filter.return_value = session_mock
    session_mock.first.return_value = None
    session_mock.all.return_value = []
    session_mock.commit.return_value = None
    session_mock.rollback.return_value = None
    session_mock.close.return_value = None

    return session_mock


@pytest.fixture
def mock_llama_index_documents():
    """Mock LlamaIndex Document objects for testing."""
    with patch("llama_index.Document") as mock_doc_class:
        mock_document = Mock()
        mock_document.text = "Sample document content for testing"
        mock_document.metadata = {"page_number": 1, "source": "test.pdf"}
        mock_doc_class.return_value = mock_document

        yield [mock_document]


class LocalStorageTestHelper:
    """Helper class for local storage testing operations."""

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)

    def create_test_document(self, doc_id: str, content: bytes = None) -> Path:
        """Create a test document in local storage."""
        if content is None:
            content = b"%PDF-1.4\nTest PDF content\n%%EOF"

        doc_dir = self.storage_path / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = doc_dir / "original.pdf"
        pdf_path.write_bytes(content)

        return pdf_path

    def cleanup_test_document(self, doc_id: str) -> None:
        """Clean up a test document from local storage."""
        doc_dir = self.storage_path / doc_id
        if doc_dir.exists():
            shutil.rmtree(doc_dir)

    def list_test_documents(self) -> list[str]:
        """List all test document IDs in storage."""
        if not self.storage_path.exists():
            return []

        return [d.name for d in self.storage_path.iterdir() if d.is_dir()]


@pytest.fixture
def local_storage_helper(temp_storage_dir: str) -> LocalStorageTestHelper:
    """Helper for local storage test operations."""
    return LocalStorageTestHelper(temp_storage_dir)


# Environment variable fixtures for testing different configurations


@pytest.fixture
def local_env_vars(temp_storage_dir: str, monkeypatch):
    """Set environment variables for local storage testing."""
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_PATH", temp_storage_dir)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("QDRANT_URL", "memory")
    monkeypatch.setenv("ENVIRONMENT", "test")


@pytest.fixture
def s3_env_vars(monkeypatch):
    """Set environment variables for S3 storage testing."""
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("ENVIRONMENT", "test")
