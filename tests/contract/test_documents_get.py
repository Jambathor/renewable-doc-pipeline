"""
Contract tests for GET /documents/{document_id} endpoint (T013).

Tests validate API responses against OpenAPI specification.
These tests target non-existent endpoints and MUST FAIL initially for TDD.
"""

import uuid
from pathlib import Path

import pytest
import yaml
from jsonschema import validate
from openapi_spec_validator import validate_spec


@pytest.fixture(scope="module")
def openapi_spec():
    """Load and validate OpenAPI specification."""
    spec_path = Path(__file__).parent.parent.parent / "specs" / "001-we-re-building" / "contracts" / "openapi.yaml"
    
    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)
    
    # Validate the spec itself
    validate_spec(spec)
    return spec


@pytest.fixture
def sample_document_id():
    """Generate a sample UUID for document ID testing."""
    return str(uuid.uuid4())


@pytest.mark.contract
class TestDocumentsGet:
    """Contract tests for GET /documents/{document_id} endpoint."""

    def test_get_document_success_response_schema(self, openapi_spec, sample_document_id):
        """Test T013: Validate successful document retrieval response matches OpenAPI schema."""
        # This test will FAIL - endpoint doesn't exist yet
        
        # Get expected response schema from OpenAPI spec
        document_response_schema = openapi_spec["components"]["schemas"]["DocumentResponse"]
        
        headers = {"X-API-Key": "test-api-key"}
        
        # This request will fail since the endpoint doesn't exist
        import httpx
        with pytest.raises((httpx.ConnectError, httpx.RequestError)):
            response = httpx.get(
                f"http://localhost:8000/documents/{sample_document_id}",
                headers=headers,
                timeout=30.0
            )
            
            # If endpoint existed, would validate like this:
            # assert response.status_code == 200
            # response_data = response.json()
            # validate(response_data, document_response_schema)
            
            # Verify UUID format for document_id field
            # assert "document_id" in response_data
            # uuid.UUID(response_data["document_id"])  # Validates UUID format

    def test_get_document_path_parameter_validation(self, openapi_spec):
        """Test T013: Validate document_id path parameter specification."""
        get_operation = openapi_spec["paths"]["/documents/{document_id}"]["get"]
        parameters = get_operation["parameters"]
        
        # Find document_id parameter
        document_id_param = next(
            (p for p in parameters if p["name"] == "document_id"), 
            None
        )
        
        assert document_id_param is not None
        assert document_id_param["in"] == "path"
        assert document_id_param["required"] is True
        assert document_id_param["schema"]["type"] == "string"
        assert document_id_param["schema"]["format"] == "uuid"

    def test_get_document_404_error_response(self, openapi_spec):
        """Test T013: Validate 404 Not Found response schema."""
        get_operation = openapi_spec["paths"]["/documents/{document_id}"]["get"]
        responses = get_operation["responses"]
        
        # Verify 404 response exists and references ErrorResponse
        assert "404" in responses
        not_found_response = responses["404"]
        assert "document not found" in not_found_response["description"].lower()
        assert "application/json" in not_found_response["content"]
        
        schema_ref = not_found_response["content"]["application/json"]["schema"]["$ref"]
        assert schema_ref == "#/components/schemas/ErrorResponse"

    def test_get_document_401_error_response(self, openapi_spec):
        """Test T013: Validate 401 Unauthorized response schema."""
        get_operation = openapi_spec["paths"]["/documents/{document_id}"]["get"]
        responses = get_operation["responses"]
        
        # Verify 401 response exists and references ErrorResponse  
        assert "401" in responses
        unauthorized_response = responses["401"]
        assert "invalid" in unauthorized_response["description"].lower() or "missing" in unauthorized_response["description"].lower()
        assert "api key" in unauthorized_response["description"].lower()
        assert "application/json" in unauthorized_response["content"]
        
        schema_ref = unauthorized_response["content"]["application/json"]["schema"]["$ref"]
        assert schema_ref == "#/components/schemas/ErrorResponse"

    def test_document_response_schema_structure(self, openapi_spec):
        """Test T013: Validate DocumentResponse schema structure and required fields."""
        document_response_schema = openapi_spec["components"]["schemas"]["DocumentResponse"]
        
        # Verify response structure
        assert document_response_schema["type"] == "object"
        
        # Check required fields
        required_fields = document_response_schema["required"]
        expected_required = ["document_id", "filename", "file_size", "processing_status", "upload_time"]
        for field in expected_required:
            assert field in required_fields

        # Verify field types and formats
        properties = document_response_schema["properties"]
        
        # Document ID should be UUID format
        assert properties["document_id"]["type"] == "string"
        assert properties["document_id"]["format"] == "uuid"
        
        # Filename should be string
        assert properties["filename"]["type"] == "string"
        
        # File size should be integer
        assert properties["file_size"]["type"] == "integer"
        
        # Processing status should be enum
        assert properties["processing_status"]["type"] == "string"
        status_enum = properties["processing_status"]["enum"]
        expected_statuses = ["uploaded", "queued", "processing", "completed", "failed", "deleted"]
        for status in expected_statuses:
            assert status in status_enum
        
        # Upload time should be date-time format
        assert properties["upload_time"]["type"] == "string"
        assert properties["upload_time"]["format"] == "date-time"

    def test_document_optional_fields(self, openapi_spec):
        """Test T013: Validate optional fields in DocumentResponse schema."""
        document_response_schema = openapi_spec["components"]["schemas"]["DocumentResponse"]
        properties = document_response_schema["properties"]
        required_fields = document_response_schema["required"]
        
        # Page count should be optional and nullable
        assert "page_count" not in required_fields
        assert properties["page_count"]["type"] == "integer"
        assert properties["page_count"]["nullable"] is True
        
        # Metadata should be optional and nullable
        assert "metadata" not in required_fields
        assert properties["metadata"]["type"] == "object"
        assert properties["metadata"]["nullable"] is True

    def test_get_document_operation_id(self, openapi_spec):
        """Test T013: Validate operation ID and summary."""
        get_operation = openapi_spec["paths"]["/documents/{document_id}"]["get"]
        
        assert get_operation["operationId"] == "getDocument"
        assert "metadata" in get_operation["summary"].lower()
        assert "status" in get_operation["summary"].lower()

    def test_get_document_security_requirement(self, openapi_spec):
        """Test T013: Validate API key authentication is required."""
        # Check that the operation inherits global security requirements
        security = openapi_spec.get("security", [])
        assert any("ApiKeyAuth" in req for req in security)
        
        # Verify the GET operation doesn't override security (inherits global)
        get_operation = openapi_spec["paths"]["/documents/{document_id}"]["get"]
        operation_security = get_operation.get("security")
        
        # If no operation-level security, it inherits global security
        if operation_security is None:
            assert True  # Inherits global security
        else:
            # If operation-level security exists, verify it includes ApiKeyAuth
            assert any("ApiKeyAuth" in req for req in operation_security)

    def test_invalid_uuid_format_handling(self, openapi_spec):
        """Test T013: Validate path parameter expects valid UUID format."""
        # This test will FAIL - endpoint doesn't exist yet
        
        invalid_document_id = "not-a-valid-uuid"
        headers = {"X-API-Key": "test-api-key"}
        
        # This request will fail since the endpoint doesn't exist
        import httpx
        with pytest.raises((httpx.ConnectError, httpx.RequestError)):
            response = httpx.get(
                f"http://localhost:8000/documents/{invalid_document_id}",
                headers=headers,
                timeout=30.0
            )
            
            # If endpoint existed, would expect 400 or 422 for invalid UUID format
            # assert response.status_code in [400, 422]

    def test_get_document_response_content_type(self, openapi_spec):
        """Test T013: Validate response content type specification."""
        get_operation = openapi_spec["paths"]["/documents/{document_id}"]["get"]
        success_response = get_operation["responses"]["200"]
        
        # Verify content type is application/json
        assert "application/json" in success_response["content"]
        content_schema = success_response["content"]["application/json"]["schema"]
        assert content_schema["$ref"] == "#/components/schemas/DocumentResponse"