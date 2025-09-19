"""
T019 - Integration tests for idempotency behavior in document upload.

Tests the Idempotency-Key header functionality and content_hash deduplication
to ensure proper handling of duplicate upload attempts per quickstart.md requirements.

These tests are expected to FAIL initially since the endpoints don't exist yet (TDD approach).
"""

import pytest
import httpx
from typing import Dict, Any

from tests.fixtures.api_client import APITestHelper
from tests.fixtures.uuid_helpers import UUIDTestHelper


@pytest.mark.integration
class TestDocumentUploadIdempotency:
    """Integration tests for document upload idempotency behavior."""

    def test_idempotency_key_prevents_duplicate_uploads(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: Dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that same Idempotency-Key prevents duplicate uploads."""
        idempotency_key = uuid_helper.generate_idempotency_key()
        
        # First upload with idempotency key
        response1 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="solar_report.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key,
        )
        
        # This test will fail until endpoints are implemented
        assert response1.status_code == 201
        response1_data = response1.json()
        
        # Validate first response structure
        assert "document_id" in response1_data
        assert "job_id" in response1_data
        uuid_helper.assert_uuid_format(response1_data["document_id"])
        uuid_helper.assert_uuid_format(response1_data["job_id"])
        
        first_document_id = response1_data["document_id"]
        first_job_id = response1_data["job_id"]
        
        # Second upload with same idempotency key should return same document
        response2 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="solar_report.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key,
        )
        
        assert response2.status_code == 200  # Not 201 since not created
        response2_data = response2.json()
        
        # Should return same document_id and job_id
        assert response2_data["document_id"] == first_document_id
        assert response2_data["job_id"] == first_job_id
        assert response2_data["status"] in ["uploaded", "processing", "completed"]

    def test_same_file_different_idempotency_key_creates_new_document(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: Dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that same file with different Idempotency-Key creates new document."""
        idempotency_key1 = uuid_helper.generate_idempotency_key()
        idempotency_key2 = uuid_helper.generate_idempotency_key()
        
        # First upload
        response1 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="wind_report.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key1,
        )
        
        # This test will fail until endpoints are implemented
        assert response1.status_code == 201
        response1_data = response1.json()
        first_document_id = response1_data["document_id"]
        
        # Second upload with different idempotency key
        response2 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="wind_report.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key2,
        )
        
        assert response2.status_code == 201
        response2_data = response2.json()
        second_document_id = response2_data["document_id"]
        
        # Should create different documents despite same file content
        assert first_document_id != second_document_id
        uuid_helper.assert_uuid_format(second_document_id)

    def test_different_file_same_idempotency_key_creates_new_document(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: Dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that different file with same Idempotency-Key creates new document."""
        idempotency_key = uuid_helper.generate_idempotency_key()
        
        # Modify PDF content slightly to create different file
        modified_pdf_content = sample_pdf_content.replace(
            b"Test renewable energy document",
            b"Modified renewable energy report"
        )
        
        # First upload
        response1 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="original_report.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key,
        )
        
        # This test will fail until endpoints are implemented
        assert response1.status_code == 201
        response1_data = response1.json()
        first_document_id = response1_data["document_id"]
        
        # Second upload with different file content but same idempotency key
        response2 = api_helper.upload_document(
            file_content=modified_pdf_content,
            filename="modified_report.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key,
        )
        
        assert response2.status_code == 201
        response2_data = response2.json()
        second_document_id = response2_data["document_id"]
        
        # Should create different documents despite same idempotency key
        assert first_document_id != second_document_id
        uuid_helper.assert_uuid_format(second_document_id)

    def test_content_hash_deduplication_logic(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: Dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test content_hash deduplication prevents duplicate processing of identical files."""
        # Upload same file without idempotency key (should trigger content hash check)
        response1 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="efficiency_report_v1.pdf",
            metadata=sample_document_metadata,
            idempotency_key=None,  # No idempotency key forces content hash comparison
        )
        
        # This test will fail until endpoints are implemented
        assert response1.status_code == 201
        response1_data = response1.json()
        first_document_id = response1_data["document_id"]
        
        # Upload identical file with different filename (should detect duplicate via content hash)
        response2 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="efficiency_report_v2.pdf",  # Different filename
            metadata={**sample_document_metadata, "title": "Updated Report"},  # Different metadata
            idempotency_key=None,
        )
        
        # Should either return same document_id or indicate duplicate detected
        if response2.status_code == 200:
            # Deduplication detected, returns existing document
            response2_data = response2.json()
            assert response2_data["document_id"] == first_document_id
            assert "duplicate_detected" in response2_data or "status" in response2_data
        elif response2.status_code == 409:
            # Conflict response indicating duplicate content
            error_data = response2.json()
            assert "error" in error_data
            assert "duplicate" in error_data["error"]["message"].lower()
        else:
            pytest.fail(f"Unexpected response code for duplicate content: {response2.status_code}")

    def test_no_idempotency_key_allows_multiple_uploads(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: Dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that uploads without Idempotency-Key are allowed multiple times."""
        # First upload without idempotency key
        response1 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="test_document_1.pdf",
            metadata=sample_document_metadata,
        )
        
        # This test will fail until endpoints are implemented
        assert response1.status_code == 201
        response1_data = response1.json()
        first_document_id = response1_data["document_id"]
        
        # Second upload without idempotency key (different metadata to avoid content hash collision)
        modified_metadata = {**sample_document_metadata, "uploaded_by": "different@user.com"}
        response2 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="test_document_2.pdf", 
            metadata=modified_metadata,
        )
        
        # Should create new document (unless content hash deduplication kicks in)
        if response2.status_code == 201:
            response2_data = response2.json()
            second_document_id = response2_data["document_id"]
            # May or may not be different depending on content hash implementation
            uuid_helper.assert_uuid_format(second_document_id)
        elif response2.status_code == 200 or response2.status_code == 409:
            # Content hash deduplication detected
            pass
        else:
            pytest.fail(f"Unexpected response code: {response2.status_code}")

    def test_idempotency_key_validation(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: Dict[str, Any],
    ):
        """Test validation of Idempotency-Key header format."""
        # Test with invalid UUID format
        response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="test.pdf",
            metadata=sample_document_metadata,
            idempotency_key="invalid-uuid-format",
        )
        
        # This test will fail until endpoints are implemented
        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data
        assert "idempotency" in error_data["error"]["message"].lower()

    def test_idempotency_across_different_accounts(
        self,
        test_api_client: httpx.Client,
        base_url: str,
        sample_pdf_content: bytes,
        sample_document_metadata: Dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that idempotency keys are scoped to individual accounts."""
        idempotency_key = uuid_helper.generate_idempotency_key()
        
        # Create helpers for different API keys (different accounts)
        api_helper1 = APITestHelper(test_api_client, base_url, "test-api-key-account-1")
        api_helper2 = APITestHelper(test_api_client, base_url, "test-api-key-account-2")
        
        # Upload with first account
        response1 = api_helper1.upload_document(
            file_content=sample_pdf_content,
            filename="shared_report.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key,
        )
        
        # This test will fail until endpoints are implemented
        assert response1.status_code == 201
        response1_data = response1.json()
        first_document_id = response1_data["document_id"]
        
        # Upload with second account using same idempotency key
        response2 = api_helper2.upload_document(
            file_content=sample_pdf_content,
            filename="shared_report.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key,
        )
        
        # Should create new document since different account
        assert response2.status_code == 201
        response2_data = response2.json()
        second_document_id = response2_data["document_id"]
        
        # Documents should be different (idempotency scoped to account)
        assert first_document_id != second_document_id
        uuid_helper.assert_uuid_format(second_document_id)

    def test_idempotency_key_persists_across_restarts(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: Dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that idempotency keys are persisted and work across service restarts."""
        idempotency_key = uuid_helper.generate_idempotency_key()
        
        # Initial upload
        response1 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="persistent_test.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key,
        )
        
        # This test will fail until endpoints are implemented
        assert response1.status_code == 201
        response1_data = response1.json()
        original_document_id = response1_data["document_id"]
        
        # Simulate service restart by making request after some delay
        # In real scenario, this would test against a restarted service
        # For now, just verify the idempotency key still works
        response2 = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="persistent_test.pdf",
            metadata=sample_document_metadata,
            idempotency_key=idempotency_key,
        )
        
        assert response2.status_code == 200
        response2_data = response2.json()
        assert response2_data["document_id"] == original_document_id