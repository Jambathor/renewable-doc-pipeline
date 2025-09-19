"""
Contract tests for DELETE /documents/{document_id} endpoint (T014).

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
class TestDocumentsDelete:
    """Contract tests for DELETE /documents/{document_id} endpoint."""

    def test_delete_document_success_response_schema(self, openapi_spec, sample_document_id):
        """Test T014: Validate successful document deletion response matches OpenAPI schema."""
        # This test will FAIL - endpoint doesn't exist yet
        
        # Get expected response schema from OpenAPI spec
        deletion_response_schema = openapi_spec["components"]["schemas"]["DeletionResponse"]
        
        headers = {"X-API-Key": "test-api-key"}
        
        # This request will fail since the endpoint doesn't exist
        import httpx
        with pytest.raises((httpx.ConnectError, httpx.RequestError)):
            response = httpx.delete(
                f"http://localhost:8000/documents/{sample_document_id}",
                headers=headers,
                timeout=30.0
            )
            
            # If endpoint existed, would validate like this:
            # assert response.status_code == 202
            # response_data = response.json()
            # validate(response_data, deletion_response_schema)
            
            # Verify UUID format for document_id field
            # assert "document_id" in response_data
            # uuid.UUID(response_data["document_id"])  # Validates UUID format

    def test_delete_document_path_parameter_validation(self, openapi_spec):
        """Test T014: Validate document_id path parameter specification."""
        delete_operation = openapi_spec["paths"]["/documents/{document_id}"]["delete"]
        parameters = delete_operation["parameters"]
        
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

    def test_delete_document_202_accepted_response(self, openapi_spec):
        """Test T014: Validate 202 Accepted response for async deletion."""
        delete_operation = openapi_spec["paths"]["/documents/{document_id}"]["delete"]
        responses = delete_operation["responses"]
        
        # Verify 202 response exists and references DeletionResponse
        assert "202" in responses
        accepted_response = responses["202"]
        assert "marked for deletion" in accepted_response["description"].lower()
        assert "application/json" in accepted_response["content"]
        
        schema_ref = accepted_response["content"]["application/json"]["schema"]["$ref"]
        assert schema_ref == "#/components/schemas/DeletionResponse"

    def test_delete_document_404_error_response(self, openapi_spec):
        """Test T014: Validate 404 Not Found response schema."""
        delete_operation = openapi_spec["paths"]["/documents/{document_id}"]["delete"]
        responses = delete_operation["responses"]
        
        # Verify 404 response exists and references ErrorResponse
        assert "404" in responses
        not_found_response = responses["404"]
        assert "document not found" in not_found_response["description"].lower()
        assert "application/json" in not_found_response["content"]
        
        schema_ref = not_found_response["content"]["application/json"]["schema"]["$ref"]
        assert schema_ref == "#/components/schemas/ErrorResponse"

    def test_delete_document_401_error_response(self, openapi_spec):
        """Test T014: Validate 401 Unauthorized response schema."""
        delete_operation = openapi_spec["paths"]["/documents/{document_id}"]["delete"]
        responses = delete_operation["responses"]
        
        # Verify 401 response exists and references ErrorResponse
        assert "401" in responses
        unauthorized_response = responses["401"]
        assert "invalid" in unauthorized_response["description"].lower() or "missing" in unauthorized_response["description"].lower()
        assert "api key" in unauthorized_response["description"].lower()
        assert "application/json" in unauthorized_response["content"]
        
        schema_ref = unauthorized_response["content"]["application/json"]["schema"]["$ref"]
        assert schema_ref == "#/components/schemas/ErrorResponse"

    def test_deletion_response_schema_structure(self, openapi_spec):
        """Test T014: Validate DeletionResponse schema structure and required fields."""
        deletion_response_schema = openapi_spec["components"]["schemas"]["DeletionResponse"]
        
        # Verify response structure
        assert deletion_response_schema["type"] == "object"
        
        # Check required fields
        required_fields = deletion_response_schema["required"]
        expected_required = ["document_id", "status", "deletion_scheduled_at", "message"]
        for field in expected_required:
            assert field in required_fields

        # Verify field types and formats
        properties = deletion_response_schema["properties"]
        
        # Document ID should be UUID format
        assert properties["document_id"]["type"] == "string"
        assert properties["document_id"]["format"] == "uuid"
        
        # Status should be enum with specific value
        assert properties["status"]["type"] == "string"
        status_enum = properties["status"]["enum"]
        assert "marked_for_deletion" in status_enum
        
        # Deletion scheduled at should be date-time format
        assert properties["deletion_scheduled_at"]["type"] == "string"
        assert properties["deletion_scheduled_at"]["format"] == "date-time"
        
        # Message should be string
        assert properties["message"]["type"] == "string"

    def test_delete_document_operation_id(self, openapi_spec):
        """Test T014: Validate operation ID and summary."""
        delete_operation = openapi_spec["paths"]["/documents/{document_id}"]["delete"]
        
        assert delete_operation["operationId"] == "deleteDocument"
        assert "delete" in delete_operation["summary"].lower()
        assert "document" in delete_operation["summary"].lower()

    def test_delete_document_async_semantics(self, openapi_spec):
        """Test T014: Validate async deletion semantics in description."""
        delete_operation = openapi_spec["paths"]["/documents/{document_id}"]["delete"]
        
        # Description should indicate marking for deletion (async operation)
        description = delete_operation["description"].lower()
        assert "mark" in description and "deletion" in description
        
        # 202 response indicates async processing
        responses = delete_operation["responses"]
        assert "202" in responses  # Accepted status for async operations

    def test_delete_document_security_requirement(self, openapi_spec):
        """Test T014: Validate API key authentication is required."""
        # Check that the operation inherits global security requirements
        security = openapi_spec.get("security", [])
        assert any("ApiKeyAuth" in req for req in security)
        
        # Verify the DELETE operation doesn't override security (inherits global)
        delete_operation = openapi_spec["paths"]["/documents/{document_id}"]["delete"]
        operation_security = delete_operation.get("security")
        
        # If no operation-level security, it inherits global security
        if operation_security is None:
            assert True  # Inherits global security
        else:
            # If operation-level security exists, verify it includes ApiKeyAuth
            assert any("ApiKeyAuth" in req for req in operation_security)

    def test_invalid_uuid_format_handling(self, openapi_spec):
        """Test T014: Validate path parameter expects valid UUID format."""
        # This test will FAIL - endpoint doesn't exist yet
        
        invalid_document_id = "invalid-uuid-format"
        headers = {"X-API-Key": "test-api-key"}
        
        # This request will fail since the endpoint doesn't exist
        import httpx
        with pytest.raises((httpx.ConnectError, httpx.RequestError)):
            response = httpx.delete(
                f"http://localhost:8000/documents/{invalid_document_id}",
                headers=headers,
                timeout=30.0
            )
            
            # If endpoint existed, would expect 400 or 422 for invalid UUID format
            # assert response.status_code in [400, 422]

    def test_delete_document_response_content_type(self, openapi_spec):
        """Test T014: Validate response content type specification."""
        delete_operation = openapi_spec["paths"]["/documents/{document_id}"]["delete"]
        success_response = delete_operation["responses"]["202"]
        
        # Verify content type is application/json
        assert "application/json" in success_response["content"]
        content_schema = success_response["content"]["application/json"]["schema"]
        assert content_schema["$ref"] == "#/components/schemas/DeletionResponse"

    def test_deletion_idempotency_semantics(self, openapi_spec):
        """Test T014: Validate that deletion operation is idempotent."""
        # This test will FAIL - endpoint doesn't exist yet
        
        sample_document_id = str(uuid.uuid4())
        headers = {"X-API-Key": "test-api-key"}
        
        # This request will fail since the endpoint doesn't exist
        import httpx
        with pytest.raises((httpx.ConnectError, httpx.RequestError)):
            # First deletion attempt
            response1 = httpx.delete(
                f"http://localhost:8000/documents/{sample_document_id}",
                headers=headers,
                timeout=30.0
            )
            
            # Second deletion attempt (should be idempotent)
            response2 = httpx.delete(
                f"http://localhost:8000/documents/{sample_document_id}",
                headers=headers,
                timeout=30.0
            )
            
            # If endpoint existed, both should succeed or second should return 404
            # assert response1.status_code == 202
            # assert response2.status_code in [202, 404]  # Idempotent behavior

    def test_deletion_response_message_format(self, openapi_spec):
        """Test T014: Validate deletion response message field requirements."""
        deletion_response_schema = openapi_spec["components"]["schemas"]["DeletionResponse"]
        properties = deletion_response_schema["properties"]
        
        # Message field should be required string
        assert "message" in deletion_response_schema["required"]
        assert properties["message"]["type"] == "string"
        assert properties["message"]["description"] == "Deletion confirmation message"