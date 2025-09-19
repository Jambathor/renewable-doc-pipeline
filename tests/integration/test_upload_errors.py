"""
T078 - Upload Error Integration Tests

Tests for document upload error scenarios including file size limits, 
unsupported media types, and corrupted PDF validation.

Expected to FAIL until /documents endpoint is implemented (TDD approach).
"""

import io
import pytest
import httpx
from tests.fixtures.api_client import APITestHelper, assert_error_response


@pytest.mark.integration
class TestUploadErrors:
    """Integration tests for document upload error scenarios."""
    
    def test_upload_returns_413_for_oversized_file(
        self, 
        api_helper: APITestHelper
    ):
        """Test 413 Payload Too Large for files >150MB."""
        # Create content that simulates a file larger than 150MB
        # Using a smaller size but with appropriate headers for testing
        large_content = b"A" * (150 * 1024 * 1024 + 1)  # 150MB + 1 byte
        
        # This test MUST fail since /documents endpoint doesn't exist yet
        response = api_helper.upload_document(
            file_content=large_content,
            filename="large_renewable_report.pdf"
        )
        
        assert response.status_code == 413
        assert response.headers.get("content-type", "").startswith("application/json")
        
        # Verify error response structure per OpenAPI spec
        assert_error_response(response, "payload_too_large")
        
        response_data = response.json()
        error = response_data["error"]
        
        # Verify error details match quickstart.md example
        assert "File size exceeds maximum limit" in error["message"]
        assert "details" in error
        assert "file_size" in error["details"]
        assert "max_allowed" in error["details"]
        assert error["details"]["max_allowed"] == 157286400  # 150MB in bytes
        assert "request_id" in error
    
    def test_upload_returns_415_for_non_pdf_file(
        self, 
        api_helper: APITestHelper
    ):
        """Test 415 Unsupported Media Type for non-PDF files."""
        # Create a Word document content
        word_content = b"PK\x03\x04"  # ZIP signature (DOCX files are ZIP-based)
        
        # This test MUST fail since /documents endpoint doesn't exist yet
        response = api_helper.client.post(
            url=api_helper.get_endpoint_url("/documents"),
            headers={"X-API-Key": api_helper.api_key},
            files={
                "file": ("report.docx", word_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            }
        )
        
        assert response.status_code == 415
        assert response.headers.get("content-type", "").startswith("application/json")
        
        # Verify error response structure per OpenAPI spec
        assert_error_response(response, "unsupported_media_type")
        
        response_data = response.json()
        error = response_data["error"]
        
        # Verify error details match quickstart.md example
        assert "Only PDF files are supported" in error["message"]
        assert "details" in error
        assert "provided_type" in error["details"]
        assert "supported_types" in error["details"]
        assert error["details"]["supported_types"] == ["application/pdf"]
        assert "request_id" in error
    
    def test_upload_returns_415_for_image_file(
        self, 
        api_helper: APITestHelper
    ):
        """Test 415 Unsupported Media Type for image files."""
        # Create a JPEG file signature
        jpeg_content = b"\xFF\xD8\xFF\xE0"  # JPEG file signature
        
        # This test MUST fail since /documents endpoint doesn't exist yet
        response = api_helper.client.post(
            url=api_helper.get_endpoint_url("/documents"),
            headers={"X-API-Key": api_helper.api_key},
            files={
                "file": ("solar_panel_image.jpg", jpeg_content, "image/jpeg")
            }
        )
        
        assert response.status_code == 415
        assert_error_response(response, "unsupported_media_type")
        
        response_data = response.json()
        error = response_data["error"]
        
        assert "Only PDF files are supported" in error["message"]
        assert error["details"]["provided_type"] == "image/jpeg"
        assert error["details"]["supported_types"] == ["application/pdf"]
    
    def test_upload_returns_422_for_corrupted_pdf(
        self, 
        api_helper: APITestHelper
    ):
        """Test 422 Unprocessable Entity for corrupted PDFs."""
        # Create invalid PDF content that looks like PDF but is corrupted
        corrupted_pdf = b"%PDF-1.4\n" + b"CORRUPTED_DATA_NOT_VALID_PDF" + b"\n%%EOF"
        
        # This test MUST fail since /documents endpoint doesn't exist yet
        response = api_helper.upload_document(
            file_content=corrupted_pdf,
            filename="corrupted_solar_report.pdf"
        )
        
        assert response.status_code == 422
        assert response.headers.get("content-type", "").startswith("application/json")
        
        # Verify error response structure per OpenAPI spec
        assert_error_response(response, "unprocessable_entity")
        
        response_data = response.json()
        error = response_data["error"]
        
        # Verify error details match quickstart.md example
        assert "PDF file is corrupted" in error["message"] or "invalid structure" in error["message"]
        assert "details" in error
        assert "validation_error" in error["details"]
        assert "request_id" in error
    
    def test_upload_returns_422_for_empty_pdf(
        self, 
        api_helper: APITestHelper
    ):
        """Test 422 Unprocessable Entity for empty PDF files."""
        # Empty file content
        empty_content = b""
        
        # This test MUST fail since /documents endpoint doesn't exist yet
        response = api_helper.upload_document(
            file_content=empty_content,
            filename="empty_file.pdf"
        )
        
        assert response.status_code == 422
        assert_error_response(response, "unprocessable_entity")
        
        response_data = response.json()
        error = response_data["error"]
        
        assert "PDF file is corrupted" in error["message"] or "invalid structure" in error["message"]
    
    def test_upload_error_response_schema_compliance(
        self, 
        api_helper: APITestHelper
    ):
        """Test error response schemas match OpenAPI specification."""
        # Test with a text file to trigger 415 error
        text_content = b"This is not a PDF file content."
        
        # This test MUST fail since /documents endpoint doesn't exist yet
        response = api_helper.client.post(
            url=api_helper.get_endpoint_url("/documents"),
            headers={"X-API-Key": api_helper.api_key},
            files={
                "file": ("text_file.txt", text_content, "text/plain")
            }
        )
        
        assert response.status_code == 415
        assert response.headers.get("content-type", "").startswith("application/json")
        
        response_data = response.json()
        
        # Verify all required fields per OpenAPI ErrorResponse schema
        assert "error" in response_data
        error = response_data["error"]
        
        # Required fields per OpenAPI spec
        assert "code" in error
        assert "message" in error
        assert isinstance(error["code"], str)
        assert isinstance(error["message"], str)
        
        # Optional fields should be present for our implementation
        assert "details" in error
        assert "request_id" in error
        assert isinstance(error["details"], dict)
        assert isinstance(error["request_id"], str)
    
    def test_upload_proper_http_status_codes(
        self, 
        api_helper: APITestHelper
    ):
        """Test proper HTTP status codes for different error scenarios."""
        test_cases = [
            {
                "name": "Large file",
                "content": b"X" * (150 * 1024 * 1024 + 1),  # 150MB + 1
                "filename": "large.pdf",
                "content_type": "application/pdf",
                "expected_status": 413,
                "expected_code": "payload_too_large"
            },
            {
                "name": "Wrong media type",
                "content": b"Not a PDF",
                "filename": "document.txt",
                "content_type": "text/plain",
                "expected_status": 415,
                "expected_code": "unsupported_media_type"
            },
            {
                "name": "Corrupted PDF",
                "content": b"%PDF-1.4\nBAD_CONTENT\n%%EOF",
                "filename": "bad.pdf",
                "content_type": "application/pdf",
                "expected_status": 422,
                "expected_code": "unprocessable_entity"
            }
        ]
        
        for case in test_cases:
            # This test MUST fail since /documents endpoint doesn't exist yet
            response = api_helper.client.post(
                url=api_helper.get_endpoint_url("/documents"),
                headers={"X-API-Key": api_helper.api_key},
                files={
                    "file": (case["filename"], case["content"], case["content_type"])
                }
            )
            
            assert response.status_code == case["expected_status"], f"Failed for {case['name']}"
            assert_error_response(response, case["expected_code"])
    
    def test_upload_error_messages_match_quickstart(
        self, 
        api_helper: APITestHelper
    ):
        """Test error messages match examples from quickstart.md."""
        # Test 415 error message
        doc_content = b"Microsoft Word Document"
        
        # This test MUST fail since /documents endpoint doesn't exist yet
        response = api_helper.client.post(
            url=api_helper.get_endpoint_url("/documents"),
            headers={"X-API-Key": api_helper.api_key},
            files={
                "file": ("report.docx", doc_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            }
        )
        
        assert response.status_code == 415
        response_data = response.json()
        error = response_data["error"]
        
        # Verify specific message format from quickstart.md
        assert error["message"] == "Only PDF files are supported"
        assert error["code"] == "unsupported_media_type"
        
        # Verify details structure matches quickstart example
        details = error["details"]
        assert "provided_type" in details
        assert "supported_types" in details
        assert details["supported_types"] == ["application/pdf"]
    
    def test_upload_with_metadata_validation_errors(
        self, 
        api_helper: APITestHelper,
        sample_pdf_content: bytes
    ):
        """Test upload errors with invalid metadata."""
        # Test with malformed JSON metadata
        response = api_helper.client.post(
            url=api_helper.get_endpoint_url("/documents"),
            headers={"X-API-Key": api_helper.api_key},
            files={
                "file": ("test.pdf", sample_pdf_content, "application/pdf")
            },
            data={
                "metadata": "invalid-json-{not-valid"  # Malformed JSON
            }
        )
        
        # This test MUST fail since /documents endpoint doesn't exist yet
        # Could return 400 for invalid JSON or 422 for validation
        assert response.status_code in [400, 422]
        
        if response.status_code == 400:
            assert_error_response(response, "validation_error")
        elif response.status_code == 422:
            assert_error_response(response, "unprocessable_entity")