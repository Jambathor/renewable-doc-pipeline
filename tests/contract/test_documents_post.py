"""
Contract tests for POST /documents endpoint (T009).

Tests validate API responses against OpenAPI specification.
These tests target non-existent endpoints and MUST FAIL initially for TDD.
"""

import json
import uuid
from io import BytesIO
from pathlib import Path

import pytest
import yaml
from jsonschema import validate
from openapi_spec_validator import validate_spec


@pytest.fixture(scope="module")
def openapi_spec():
    """Load and validate OpenAPI specification."""
    spec_path = Path(__file__).parent.parent.parent / "specs" / "001-we-re-building" / "contracts" / "openapi.yaml"

    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    # Validate the spec itself
    validate_spec(spec)
    return spec


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    # Create a minimal PDF-like binary content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"
    return BytesIO(pdf_content)


@pytest.fixture
def valid_document_metadata():
    """Sample valid document metadata."""
    return {
        "title": "Solar Panel Efficiency Report",
        "tags": ["solar", "efficiency", "renewable"],
        "source_url": "https://example.com/solar-report.pdf",
        "uploaded_by": "test@example.com"
    }


@pytest.mark.contract
class TestDocumentsPost:
    """Contract tests for POST /documents endpoint."""

    def test_upload_document_success_response_schema(self, openapi_spec, sample_pdf_file, valid_document_metadata):
        """Test T009: Validate successful upload response matches OpenAPI schema."""
        # Get expected response schema from OpenAPI spec
        upload_response_schema = openapi_spec["components"]["schemas"]["DocumentUploadResponse"]

        # Prepare multipart form data
        files = {"file": ("test.pdf", sample_pdf_file, "application/pdf")}
        data = {"metadata": json.dumps(valid_document_metadata)}
        headers = {
            "X-API-Key": "test-api-key",
            "Idempotency-Key": str(uuid.uuid4())
        }

        # Test the actual endpoint
        import httpx
        response = httpx.post(
            "http://localhost:8000/documents",
            files=files,
            data=data,
            headers=headers,
            timeout=30.0
        )

        # Validate successful response
        assert response.status_code == 201
        response_data = response.json()
        validate(response_data, upload_response_schema)

        # Verify UUID format for content_id fields
        assert "document_id" in response_data
        uuid.UUID(response_data["document_id"])  # Validates UUID format
        assert "job_id" in response_data
        uuid.UUID(response_data["job_id"])

        # Verify required fields are present
        assert "filename" in response_data
        assert "file_size" in response_data
        assert "status" in response_data
        assert "upload_time" in response_data

        # Verify status is valid enum value
        assert response_data["status"] in ["uploaded", "queued"]

    def test_upload_document_multipart_content_type(self, openapi_spec):
        """Test T009: Validate multipart/form-data content type requirement."""
        # Get request schema from OpenAPI spec
        post_operation = openapi_spec["paths"]["/documents"]["post"]
        request_body = post_operation["requestBody"]

        # Verify multipart/form-data is required
        assert "multipart/form-data" in request_body["content"]
        multipart_schema = request_body["content"]["multipart/form-data"]["schema"]

        # Verify required fields
        assert "file" in multipart_schema["required"]
        assert multipart_schema["properties"]["file"]["type"] == "string"
        assert multipart_schema["properties"]["file"]["format"] == "binary"

    def test_upload_document_idempotency_key_header(self, openapi_spec):
        """Test T009: Validate Idempotency-Key header specification."""
        post_operation = openapi_spec["paths"]["/documents"]["post"]
        parameters = post_operation["parameters"]

        # Find Idempotency-Key parameter
        idempotency_param = next(
            (p for p in parameters if p["name"] == "Idempotency-Key"),
            None
        )

        assert idempotency_param is not None
        assert idempotency_param["in"] == "header"
        assert idempotency_param["required"] is False
        assert idempotency_param["schema"]["type"] == "string"
        assert idempotency_param["schema"]["format"] == "uuid"

    def test_upload_document_error_responses_schema(self, openapi_spec):
        """Test T009: Validate error response schemas for various HTTP status codes."""
        post_operation = openapi_spec["paths"]["/documents"]["post"]
        responses = post_operation["responses"]

        # Test error status codes match specification
        expected_error_codes = ["400", "401", "413", "415", "422", "429"]
        for error_code in expected_error_codes:
            assert error_code in responses
            error_response = responses[error_code]
            assert "application/json" in error_response["content"]

            # Verify all errors reference ErrorResponse schema
            schema_ref = error_response["content"]["application/json"]["schema"]["$ref"]
            assert schema_ref == "#/components/schemas/ErrorResponse"

    def test_error_response_schema_structure(self, openapi_spec):
        """Test T009: Validate ErrorResponse schema structure."""
        error_schema = openapi_spec["components"]["schemas"]["ErrorResponse"]

        # Verify error response structure
        assert error_schema["type"] == "object"
        assert "error" in error_schema["required"]

        error_object = error_schema["properties"]["error"]
        assert error_object["type"] == "object"
        assert "code" in error_object["required"]
        assert "message" in error_object["required"]

        # Verify error object properties
        assert error_object["properties"]["code"]["type"] == "string"
        assert error_object["properties"]["message"]["type"] == "string"
        assert error_object["properties"]["details"]["type"] == "object"
        assert error_object["properties"]["request_id"]["type"] == "string"

    def test_upload_file_size_limit_specification(self, openapi_spec):
        """Test T009: Validate file size limit is documented in schema."""
        post_operation = openapi_spec["paths"]["/documents"]["post"]

        # Check description mentions file size limit (operation or file property)
        description = post_operation["description"]
        file_description = post_operation["requestBody"]["content"]["multipart/form-data"]["schema"]["properties"]["file"]["description"]

        has_size_limit = (
            "150MB" in description or "max" in description.lower() or
            "150MB" in file_description or "max" in file_description.lower()
        )
        assert has_size_limit, "File size limit should be documented in operation or file property description"

        # Check 413 response for payload too large
        responses = post_operation["responses"]
        assert "413" in responses
        assert "too large" in responses["413"]["description"].lower()

    def test_upload_pdf_format_requirement(self, openapi_spec):
        """Test T009: Validate PDF format requirement and 415 error."""
        post_operation = openapi_spec["paths"]["/documents"]["post"]
        responses = post_operation["responses"]

        # Verify 415 Unsupported Media Type response
        assert "415" in responses
        unsupported_response = responses["415"]
        assert "unsupported media type" in unsupported_response["description"].lower()
        assert "pdf" in unsupported_response["description"].lower()

    def test_upload_quota_limit_specification(self, openapi_spec):
        """Test T009: Validate document quota limit and 429 error."""
        post_operation = openapi_spec["paths"]["/documents"]["post"]
        responses = post_operation["responses"]

        # Verify 429 Too Many Requests response for quota
        assert "429" in responses
        quota_response = responses["429"]
        assert "quota" in quota_response["description"].lower()
        assert "200 documents" in quota_response["description"]

    def test_security_requirement(self, openapi_spec):
        """Test T009: Validate API key authentication requirement."""
        # Check global security requirement
        security = openapi_spec.get("security", [])
        assert any("ApiKeyAuth" in req for req in security)

        # Verify ApiKeyAuth scheme definition
        auth_scheme = openapi_spec["components"]["securitySchemes"]["ApiKeyAuth"]
        assert auth_scheme["type"] == "apiKey"
        assert auth_scheme["in"] == "header"
        assert auth_scheme["name"] == "X-API-Key"
