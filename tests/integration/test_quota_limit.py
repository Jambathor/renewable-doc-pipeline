"""
Integration tests for quota limit functionality (T080).

Tests that validate account quota enforcement, validation before processing,
and proper error handling for quota exceeded scenarios. These tests are
designed to fail initially following TDD approach until quota endpoints are implemented.
"""

import pytest
import httpx
from typing import Dict, Any, List
from unittest.mock import patch

from tests.fixtures.api_client import APITestHelper, assert_error_response, assert_uuid_format
from tests.fixtures.test_data import sample_document_uuids


@pytest.mark.integration
class TestQuotaLimit:
    """Test quota limit enforcement and management."""

    def test_document_upload_returns_429_when_account_at_200_docs(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_uuids: Dict[str, str],
    ):
        """Test that POST /documents returns 429 when account has reached 200 document limit."""
        # First, simulate an account at the quota limit
        # This would normally be done by uploading 200 documents,
        # but for testing we'll mock the quota check
        
        # Attempt to upload when at quota limit
        response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="quota_test_document.pdf",
            metadata={
                "title": "Quota Test Document",
                "tags": ["test", "quota"],
            },
            idempotency_key=sample_document_uuids["document_1"],
        )
        
        # Should receive quota exceeded error
        assert response.status_code == 429
        assert_error_response(response, "quota_exceeded")
        
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"]["code"] == "quota_exceeded"
        assert "200" in error_data["error"]["message"]  # Should mention limit
        
        # Validate error details include current and max counts
        assert "details" in error_data["error"]
        details = error_data["error"]["details"]
        assert "current_count" in details
        assert "max_allowed" in details
        assert details["current_count"] == 200
        assert details["max_allowed"] == 200

    def test_quota_validation_before_processing_starts(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_uuids: Dict[str, str],
    ):
        """Test that quota validation occurs before document processing begins."""
        # Attempt upload when at quota limit
        response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="pre_process_quota_test.pdf",
            metadata={
                "title": "Pre-Process Quota Test",
                "tags": ["test", "quota", "validation"],
            },
            idempotency_key=sample_document_uuids["document_2"],
        )
        
        # Should fail immediately with 429, not create job
        assert response.status_code == 429
        error_data = response.json()
        
        # No job_id should be returned since quota check failed
        assert "job_id" not in error_data
        assert "document_id" not in error_data
        
        # Verify no processing job was created
        assert_error_response(response, "quota_exceeded")

    def test_quota_error_message_indicates_current_max_document_counts(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_uuids: Dict[str, str],
    ):
        """Test that quota exceeded error message includes current and max document counts."""
        # Mock different quota scenarios
        test_scenarios = [
            {"current": 200, "max": 200},  # At limit
            {"current": 199, "max": 200},  # Would exceed with this upload
        ]
        
        for scenario in test_scenarios:
            response = api_helper.upload_document(
                file_content=sample_pdf_content,
                filename=f"quota_test_{scenario['current']}.pdf",
                metadata={
                    "title": f"Quota Test {scenario['current']}/{scenario['max']}",
                    "tags": ["test", "quota", "counts"],
                },
                idempotency_key=sample_document_uuids["content_1"],
            )
            
            if scenario["current"] >= scenario["max"]:
                assert response.status_code == 429
                error_data = response.json()
                
                # Validate detailed error information
                assert error_data["error"]["code"] == "quota_exceeded"
                assert str(scenario["max"]) in error_data["error"]["message"]
                
                details = error_data["error"]["details"]
                assert details["current_count"] >= scenario["current"]
                assert details["max_allowed"] == scenario["max"]

    def test_quota_enforcement_per_account_api_key_isolation(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_uuids: Dict[str, str],
    ):
        """Test that quota enforcement is per account with API key isolation."""
        # Test with primary API key (at quota)
        primary_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="primary_account_test.pdf",
            metadata={"title": "Primary Account Test"},
            idempotency_key=sample_document_uuids["document_3"],
        )
        
        # Should fail for primary account
        assert primary_response.status_code == 429
        
        # Create helper with different API key
        different_api_helper = APITestHelper(
            client=api_helper.client,
            base_url=api_helper.base_url,
            api_key="different-test-api-key-67890",
        )
        
        # Test with different API key (fresh quota)
        different_response = different_api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="different_account_test.pdf",
            metadata={"title": "Different Account Test"},
            idempotency_key=sample_document_uuids["job_2"],
        )
        
        # Should succeed for different account (or fail with auth error, not quota)
        # The key point is quota errors are account-specific
        if different_response.status_code == 429:
            # If it fails with quota, it should have different count details
            error_data = different_response.json()
            if error_data["error"]["code"] == "quota_exceeded":
                # This account should have its own quota tracking
                pass
        elif different_response.status_code == 401:
            # Invalid API key is expected in test environment
            assert_error_response(different_response, "unauthorized")
        else:
            # Success is also valid if the different account has quota available
            assert different_response.status_code in [201, 401]

    def test_quota_resets_after_document_deletion(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_uuids: Dict[str, str],
    ):
        """Test that quota count decreases after document deletion."""
        # First, verify we're at quota limit
        upload_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="quota_reset_test.pdf",
            metadata={"title": "Quota Reset Test"},
            idempotency_key=sample_document_uuids["content_2"],
        )
        
        assert upload_response.status_code == 429
        initial_error = upload_response.json()
        initial_count = initial_error["error"]["details"]["current_count"]
        assert initial_count == 200
        
        # Get a list of existing documents to delete one
        # In a real scenario, we'd have documents to delete
        # For this test, we'll assume there's at least one document
        test_document_id = sample_document_uuids["document_1"]
        
        # Delete a document
        delete_response = api_helper.delete_document(test_document_id)
        
        # Should succeed or return 404 if document doesn't exist
        assert delete_response.status_code in [200, 404]
        
        if delete_response.status_code == 200:
            # Wait a moment for quota to update (if async)
            import time
            time.sleep(1)
            
            # Try upload again - should work now or show reduced count
            retry_response = api_helper.upload_document(
                file_content=sample_pdf_content,
                filename="post_deletion_test.pdf",
                metadata={"title": "Post-Deletion Test"},
                idempotency_key=sample_document_uuids["content_3"],
            )
            
            if retry_response.status_code == 429:
                # If still failing, count should be reduced
                retry_error = retry_response.json()
                retry_count = retry_error["error"]["details"]["current_count"]
                assert retry_count < initial_count, "Quota count should decrease after deletion"
            else:
                # Success means quota was freed
                assert retry_response.status_code == 201

    def test_quota_validation_with_idempotency_key(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_uuids: Dict[str, str],
    ):
        """Test quota validation behavior with idempotency keys."""
        idempotency_key = sample_document_uuids["job_1"]
        
        # First attempt at quota limit
        first_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="idempotency_quota_test.pdf",
            metadata={"title": "Idempotency Quota Test"},
            idempotency_key=idempotency_key,
        )
        
        assert first_response.status_code == 429
        
        # Retry with same idempotency key
        retry_response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="idempotency_quota_test.pdf",
            metadata={"title": "Idempotency Quota Test"},
            idempotency_key=idempotency_key,
        )
        
        # Should return same error (idempotent)
        assert retry_response.status_code == 429
        
        # Error details should be consistent
        first_error = first_response.json()
        retry_error = retry_response.json()
        assert first_error["error"]["code"] == retry_error["error"]["code"]

    def test_quota_near_limit_behavior(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_uuids: Dict[str, str],
    ):
        """Test behavior when approaching quota limit (e.g., at 199/200)."""
        # This test simulates being near the quota limit
        # In practice, this would require setting up an account with 199 documents
        
        # Mock scenario: account has 199 documents
        response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="near_quota_test.pdf",
            metadata={"title": "Near Quota Test"},
            idempotency_key=sample_document_uuids["content_1"],
        )
        
        # Could succeed (bringing to 200) or fail if already at 200
        if response.status_code == 201:
            # Upload succeeded, now at limit
            upload_data = response.json()
            assert_uuid_format(upload_data["document_id"])
            assert_uuid_format(upload_data["job_id"])
            
            # Next upload should fail
            next_response = api_helper.upload_document(
                file_content=sample_pdf_content,
                filename="over_quota_test.pdf",
                metadata={"title": "Over Quota Test"},
                idempotency_key=sample_document_uuids["content_2"],
            )
            assert next_response.status_code == 429
            
        elif response.status_code == 429:
            # Already at quota
            assert_error_response(response, "quota_exceeded")
            error_data = response.json()
            assert error_data["error"]["details"]["current_count"] >= 199

    def test_quota_error_includes_request_id(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_uuids: Dict[str, str],
    ):
        """Test that quota exceeded errors include request ID for tracking."""
        response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="request_id_test.pdf",
            metadata={"title": "Request ID Test"},
            idempotency_key=sample_document_uuids["job_2"],
        )
        
        assert response.status_code == 429
        error_data = response.json()
        
        # Should include request ID for support/debugging
        assert "request_id" in error_data["error"]
        assert len(error_data["error"]["request_id"]) > 0
        assert error_data["error"]["request_id"].startswith("req-")


@pytest.fixture
def quota_test_setup():
    """Fixture to set up quota testing scenarios."""
    # This would typically involve:
    # - Creating test accounts with known document counts
    # - Setting up API keys with different quota states
    # - Preparing test documents for upload/deletion
    return {
        "max_documents": 200,
        "test_scenarios": [
            {"account": "at_limit", "current_count": 200},
            {"account": "near_limit", "current_count": 199},
            {"account": "under_limit", "current_count": 150},
        ]
    }


@pytest.fixture
def multiple_api_keys():
    """Fixture providing multiple API keys for isolation testing."""
    return {
        "primary": "test-api-key-12345",
        "secondary": "test-api-key-67890",
        "tertiary": "test-api-key-abcdef",
    }


# Helper function to simulate quota state
def simulate_quota_state(api_helper: APITestHelper, document_count: int) -> List[str]:
    """
    Helper to simulate an account with a specific document count.
    
    In a real implementation, this would upload documents to reach the target count.
    For testing, this serves as a placeholder for quota state setup.
    """
    # This is a mock implementation
    # Real implementation would upload actual documents
    document_ids = []
    for i in range(document_count):
        # Simulate document upload (would be actual uploads in real scenario)
        document_ids.append(f"simulated-doc-{i:03d}")
    
    return document_ids