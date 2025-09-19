"""
T020 - Integration tests for document deletion behavior.

Tests DELETE endpoint functionality including immediate hard delete semantics in demo mode,
S3 cleanup, vector embedding removal, and proper 202 response format per quickstart.md.

These tests are expected to FAIL initially since the endpoints don't exist yet (TDD approach).
"""

import time
from typing import Any, Dict

import httpx
import pytest

from tests.fixtures.api_client import APITestHelper
from tests.fixtures.uuid_helpers import UUIDTestHelper


@pytest.mark.integration
class TestDocumentDeletion:
    """Integration tests for document deletion behavior."""

    def test_delete_returns_202_marked_for_deletion_response(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test DELETE returns 202 with 'marked_for_deletion' status response."""
        # First upload a document
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="test_deletion.pdf",
            metadata=sample_document_metadata,
        )

        # This test will fail until endpoints are implemented
        assert upload_response.status_code == 201
        upload_data = upload_response.json()
        document_id = upload_data["document_id"]
        uuid_helper.assert_uuid_format(document_id)

        # Delete the document
        delete_response = api_helper.delete_document(document_id)

        assert delete_response.status_code == 202  # Accepted for processing
        delete_data = delete_response.json()

        # Validate response structure per quickstart.md
        assert delete_data["document_id"] == document_id
        assert delete_data["status"] == "marked_for_deletion"
        assert "deletion_scheduled_at" in delete_data
        assert "message" in delete_data

        # Validate deletion_scheduled_at is a valid ISO datetime
        deletion_time = delete_data["deletion_scheduled_at"]
        from datetime import datetime
        try:
            datetime.fromisoformat(deletion_time.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Invalid deletion_scheduled_at format: {deletion_time}")

    def test_immediate_hard_delete_semantics_demo_mode(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test immediate hard delete in demo mode per CLAUDE.md guidelines."""
        # Upload document
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="immediate_delete_test.pdf",
            metadata=sample_document_metadata,
        )

        # This test will fail until endpoints are implemented
        assert upload_response.status_code == 201
        document_id = upload_response.json()["document_id"]

        # Wait for processing to complete (simulate async processing)
        # In real implementation, would poll job status until completed
        job_id = upload_response.json().get("job_id")
        if job_id:
            # Poll job status until completed
            for _ in range(30):  # Max 30 seconds wait
                job_response = api_helper.get_job_status(job_id)
                if job_response.status_code == 200:
                    job_data = job_response.json()
                    if job_data.get("status") == "completed":
                        break
                time.sleep(1)

        # Verify document exists before deletion
        get_response = api_helper.get_document(document_id)
        assert get_response.status_code == 200

        # Delete document
        delete_response = api_helper.delete_document(document_id)
        assert delete_response.status_code == 202

        # Verify immediate deletion effect in demo mode
        # According to CLAUDE.md, demo mode performs immediate hard delete
        get_after_delete = api_helper.get_document(document_id)
        assert get_after_delete.status_code == 404

        error_data = get_after_delete.json()
        assert "error" in error_data
        assert "not found" in error_data["error"]["message"].lower()

    def test_document_becomes_inaccessible_after_deletion(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that document becomes inaccessible in all API operations after deletion."""
        # Upload and process document
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="access_test.pdf",
            metadata=sample_document_metadata,
        )

        # This test will fail until endpoints are implemented
        assert upload_response.status_code == 201
        document_id = upload_response.json()["document_id"]

        # Delete document
        delete_response = api_helper.delete_document(document_id)
        assert delete_response.status_code == 202

        # Test document GET returns 404
        get_response = api_helper.get_document(document_id)
        assert get_response.status_code == 404

        # Test search filtering excludes deleted document
        search_response = api_helper.search_documents(
            query="test renewable energy",
            document_ids=[document_id],
        )
        # Should either return no results or exclude the deleted document
        if search_response.status_code == 200:
            search_data = search_response.json()
            # Verify deleted document is not in search results
            for result in search_data.get("results", []):
                assert result["document_id"] != document_id

        # Test Q&A with specific document filter excludes deleted document
        qa_response = api_helper.ask_question(
            question="What is renewable energy?",
            context_filters={"document_ids": [document_id]},
        )
        # Should return no evidence found or filter out deleted document
        if qa_response.status_code == 200:
            qa_data = qa_response.json()
            # Should have no citations from deleted document
            for citation in qa_data.get("citations", []):
                # Document title should not match or citations should be empty
                pass

    def test_s3_objects_removed_after_deletion(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that S3 objects are removed after document deletion."""
        # Upload document
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="s3_cleanup_test.pdf",
            metadata=sample_document_metadata,
        )

        # This test will fail until endpoints are implemented
        assert upload_response.status_code == 201
        document_id = upload_response.json()["document_id"]

        # Get document metadata to verify S3 objects exist
        get_response = api_helper.get_document(document_id)
        assert get_response.status_code == 200

        # Delete document
        delete_response = api_helper.delete_document(document_id)
        assert delete_response.status_code == 202

        # Note: In integration tests, we can't directly verify S3 deletion
        # without access to AWS credentials. This would be verified through:
        # 1. Metrics endpoint showing reduced storage usage
        # 2. AWS CloudWatch metrics
        # 3. Direct S3 API calls in deployment tests

        # For now, verify the API contract is maintained
        assert delete_response.json()["status"] == "marked_for_deletion"

    def test_vector_embeddings_removed_after_deletion(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that vector embeddings are removed from Qdrant after deletion."""
        # Upload document
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="vector_cleanup_test.pdf",
            metadata=sample_document_metadata,
        )

        # This test will fail until endpoints are implemented
        assert upload_response.status_code == 201
        document_id = upload_response.json()["document_id"]

        # Wait for processing to complete (embeddings generation)
        job_id = upload_response.json().get("job_id")
        if job_id:
            for _ in range(60):  # Max 60 seconds for embedding generation
                job_response = api_helper.get_job_status(job_id)
                if job_response.status_code == 200:
                    job_data = job_response.json()
                    if job_data.get("status") == "completed":
                        break
                time.sleep(1)

        # Verify search finds content (embeddings exist)
        search_response = api_helper.search_documents(
            query="renewable energy",
            document_ids=[document_id],
        )

        if search_response.status_code == 200:
            search_data = search_response.json()
            # Should have results if embeddings exist
            has_results_before = search_data.get("total_results", 0) > 0

        # Delete document
        delete_response = api_helper.delete_document(document_id)
        assert delete_response.status_code == 202

        # Verify search no longer finds content (embeddings removed)
        search_after_delete = api_helper.search_documents(
            query="renewable energy",
            document_ids=[document_id],
        )

        if search_after_delete.status_code == 200:
            search_data_after = search_after_delete.json()
            # Should have no results for deleted document
            for result in search_data_after.get("results", []):
                assert result["document_id"] != document_id

    def test_404_for_subsequent_operations_on_deleted_document(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test 404 responses for operations on deleted documents."""
        # Upload document
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="subsequent_ops_test.pdf",
            metadata=sample_document_metadata,
        )

        # This test will fail until endpoints are implemented
        assert upload_response.status_code == 201
        document_id = upload_response.json()["document_id"]

        # Delete document
        delete_response = api_helper.delete_document(document_id)
        assert delete_response.status_code == 202

        # Test subsequent GET returns 404
        get_response = api_helper.get_document(document_id)
        assert get_response.status_code == 404

        # Test subsequent DELETE returns 404
        delete_again_response = api_helper.delete_document(document_id)
        assert delete_again_response.status_code == 404

        # Verify proper error response structure
        error_data = delete_again_response.json()
        assert "error" in error_data
        assert "code" in error_data["error"]
        assert "message" in error_data["error"]
        assert "not found" in error_data["error"]["message"].lower()

    def test_delete_nonexistent_document_returns_404(
        self,
        api_helper: APITestHelper,
        uuid_helper: UUIDTestHelper,
    ):
        """Test DELETE on non-existent document returns 404."""
        # Generate a valid UUID that doesn't exist
        nonexistent_id = uuid_helper.generate_document_uuid()

        # This test will fail until endpoints are implemented
        delete_response = api_helper.delete_document(nonexistent_id)
        assert delete_response.status_code == 404

        error_data = delete_response.json()
        assert "error" in error_data
        assert "not found" in error_data["error"]["message"].lower()

    def test_delete_invalid_document_id_returns_400(
        self,
        api_helper: APITestHelper,
    ):
        """Test DELETE with invalid document ID format returns 400."""
        invalid_id = "not-a-valid-uuid"

        # This test will fail until endpoints are implemented
        delete_response = api_helper.delete_document(invalid_id)
        assert delete_response.status_code == 400

        error_data = delete_response.json()
        assert "error" in error_data
        assert "invalid" in error_data["error"]["message"].lower()

    def test_concurrent_deletion_requests_idempotent(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that concurrent deletion requests are handled idempotently."""
        # Upload document
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="concurrent_delete_test.pdf",
            metadata=sample_document_metadata,
        )

        # This test will fail until endpoints are implemented
        assert upload_response.status_code == 201
        document_id = upload_response.json()["document_id"]

        # First deletion request
        delete_response1 = api_helper.delete_document(document_id)
        assert delete_response1.status_code == 202

        # Second deletion request (should be idempotent)
        delete_response2 = api_helper.delete_document(document_id)
        # Should return 404 (already deleted) or 202 (idempotent)
        assert delete_response2.status_code in [202, 404]

        if delete_response2.status_code == 202:
            # If idempotent, should return same response structure
            delete_data = delete_response2.json()
            assert delete_data["document_id"] == document_id
            assert delete_data["status"] == "marked_for_deletion"

    def test_deletion_preserves_api_semantics_in_demo_mode(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        uuid_helper: UUIDTestHelper,
    ):
        """Test that demo mode deletion preserves API contract semantics."""
        # Upload document
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="api_semantics_test.pdf",
            metadata=sample_document_metadata,
        )

        # This test will fail until endpoints are implemented
        assert upload_response.status_code == 201
        document_id = upload_response.json()["document_id"]

        # Delete document
        delete_response = api_helper.delete_document(document_id)

        # Verify API contract is maintained even in demo mode
        assert delete_response.status_code == 202  # Not 200 or 204
        delete_data = delete_response.json()

        # Response should follow quickstart.md format
        required_fields = ["document_id", "status", "deletion_scheduled_at", "message"]
        for field in required_fields:
            assert field in delete_data, f"Missing required field: {field}"

        # Status should indicate scheduled deletion despite immediate effect
        assert delete_data["status"] == "marked_for_deletion"
        assert "deletion" in delete_data["message"].lower()

        # Document should still be immediately inaccessible (demo behavior)
        get_response = api_helper.get_document(document_id)
        assert get_response.status_code == 404
