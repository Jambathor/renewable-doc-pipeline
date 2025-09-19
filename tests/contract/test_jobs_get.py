"""
T010 Contract tests for GET /jobs/{job_id} endpoint.

This test file validates the jobs endpoint against the OpenAPI specification.
These tests are expected to FAIL until the endpoint is implemented.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from jsonschema import Draft7Validator, ValidationError
from openapi_spec_validator import validate_spec


@pytest.fixture(scope="module")
def openapi_spec() -> Dict[str, Any]:
    """Load and validate the OpenAPI specification."""
    spec_path = Path(__file__).parent.parent.parent / "specs" / "001-we-re-building" / "contracts" / "openapi.yaml"
    
    with open(spec_path, 'r') as f:
        spec = yaml.safe_load(f)
    
    # Validate the spec itself is valid OpenAPI
    validate_spec(spec)
    return spec


@pytest.fixture(scope="module")
def job_status_schema(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Extract JobStatusResponse schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["JobStatusResponse"]


@pytest.fixture(scope="module")
def error_response_schema(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Extract ErrorResponse schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["ErrorResponse"]


class TestJobsEndpointContract:
    """Contract tests for the GET /jobs/{job_id} endpoint."""

    @pytest.mark.contract
    def test_jobs_endpoint_defined_in_openapi_spec(self, openapi_spec: Dict[str, Any]):
        """Verify the jobs endpoint is properly defined in OpenAPI spec."""
        paths = openapi_spec.get("paths", {})
        job_path = "/jobs/{job_id}"
        
        assert job_path in paths, f"Path {job_path} not found in OpenAPI spec"
        assert "get" in paths[job_path], f"GET method not defined for {job_path}"
        
        get_operation = paths[job_path]["get"]
        assert get_operation["operationId"] == "getJobStatus"
        assert "job_id" in [param["name"] for param in get_operation["parameters"]]

    @pytest.mark.contract
    def test_job_id_parameter_validation(self, openapi_spec: Dict[str, Any]):
        """Verify job_id parameter follows UUID format requirement."""
        job_path = openapi_spec["paths"]["/jobs/{job_id}"]
        get_operation = job_path["get"]
        
        job_id_param = next(param for param in get_operation["parameters"] if param["name"] == "job_id")
        
        assert job_id_param["required"] is True
        assert job_id_param["in"] == "path"
        assert job_id_param["schema"]["type"] == "string"
        assert job_id_param["schema"]["format"] == "uuid"

    @pytest.mark.contract
    def test_response_schemas_defined(self, openapi_spec: Dict[str, Any]):
        """Verify all required response schemas are properly defined."""
        job_path = openapi_spec["paths"]["/jobs/{job_id}"]
        get_operation = job_path["get"]
        responses = get_operation["responses"]
        
        # Check required status codes
        assert "200" in responses, "200 success response not defined"
        assert "401" in responses, "401 unauthorized response not defined"
        assert "404" in responses, "404 not found response not defined"
        
        # Verify schema references
        success_schema = responses["200"]["content"]["application/json"]["schema"]
        assert success_schema["$ref"] == "#/components/schemas/JobStatusResponse"
        
        error_401_schema = responses["401"]["content"]["application/json"]["schema"]
        assert error_401_schema["$ref"] == "#/components/schemas/ErrorResponse"
        
        error_404_schema = responses["404"]["content"]["application/json"]["schema"]
        assert error_404_schema["$ref"] == "#/components/schemas/ErrorResponse"

    @pytest.mark.contract
    def test_job_status_response_schema_validation(self, job_status_schema: Dict[str, Any]):
        """Verify JobStatusResponse schema matches specification requirements."""
        # Required fields
        required_fields = {"job_id", "document_id", "status", "progress_percentage", "started_at", "retry_count"}
        assert set(job_status_schema["required"]) == required_fields
        
        properties = job_status_schema["properties"]
        
        # UUID format fields
        assert properties["job_id"]["format"] == "uuid"
        assert properties["document_id"]["format"] == "uuid"
        
        # Status enum validation
        status_enum = properties["status"]["enum"]
        expected_statuses = {"pending", "running", "completed", "failed", "retrying"}
        assert set(status_enum) == expected_statuses
        
        # Progress percentage validation
        progress = properties["progress_percentage"]
        assert progress["type"] == "integer"
        assert progress["minimum"] == 0
        assert progress["maximum"] == 100
        
        # Error type enum validation (when present)
        error_type = properties["error_type"]
        assert error_type["nullable"] is True
        expected_error_types = {
            "validation_error", "processing_error", "storage_error", 
            "quota_exceeded", "system_error"
        }
        assert set(error_type["enum"]) == expected_error_types

    @pytest.mark.contract
    def test_valid_job_status_response_against_schema(self, job_status_schema: Dict[str, Any]):
        """Test that a valid JobStatusResponse matches the schema."""
        # Basic valid response with only required fields
        valid_response = {
            "job_id": str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            "status": "running",
            "progress_percentage": 45,
            "started_at": "2025-09-19T10:30:00Z",
            "retry_count": 0
        }
        
        # This should not raise any validation errors
        validator = Draft7Validator(job_status_schema)
        errors = list(validator.iter_errors(valid_response))
        assert len(errors) == 0, f"Valid response failed schema validation: {errors}"
        
        # Test completed job with all fields
        completed_response = {
            "job_id": str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            "status": "completed",
            "progress_percentage": 100,
            "started_at": "2025-09-19T10:30:00Z",
            "completed_at": "2025-09-19T10:35:00Z",
            "retry_count": 0
        }
        
        errors = list(validator.iter_errors(completed_response))
        assert len(errors) == 0, f"Completed response failed schema validation: {errors}"
        
        # Test failed job with error details
        failed_response = {
            "job_id": str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            "status": "failed",
            "progress_percentage": 25,
            "started_at": "2025-09-19T10:30:00Z",
            "error_message": "Processing failed due to corrupted PDF",
            "error_type": "processing_error",
            "retry_count": 2
        }
        
        errors = list(validator.iter_errors(failed_response))
        assert len(errors) == 0, f"Failed response failed schema validation: {errors}"

    @pytest.mark.contract
    def test_invalid_job_status_responses_fail_validation(self, job_status_schema: Dict[str, Any]):
        """Test that invalid responses properly fail schema validation."""
        validator = Draft7Validator(job_status_schema)
        
        # Missing required field (missing status)
        invalid_missing_field = {
            "job_id": str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            # "status": "running",  # Missing required field
            "progress_percentage": 45,
            "started_at": "2025-09-19T10:30:00Z",
            "retry_count": 0
        }
        
        # Invalid status enum value
        invalid_status = {
            "job_id": str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            "status": "invalid_status",  # Not in enum
            "progress_percentage": 45,
            "started_at": "2025-09-19T10:30:00Z",
            "retry_count": 0
        }
        
        # Progress percentage out of range
        invalid_progress = {
            "job_id": str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            "status": "running",
            "progress_percentage": 150,  # Out of 0-100 range
            "started_at": "2025-09-19T10:30:00Z",
            "retry_count": 0
        }
        
        # Invalid UUID format
        invalid_uuid = {
            "job_id": "not-a-uuid",  # Invalid UUID
            "document_id": str(uuid.uuid4()),
            "status": "running",
            "progress_percentage": 45,
            "started_at": "2025-09-19T10:30:00Z",
            "retry_count": 0
        }
        
        test_cases = [
            ("missing_required_field", invalid_missing_field),
            ("invalid_status_enum", invalid_status),
            ("invalid_progress_range", invalid_progress),
            ("invalid_uuid_format", invalid_uuid)
        ]
        
        for test_name, invalid_data in test_cases:
            errors = list(validator.iter_errors(invalid_data))
            assert len(errors) > 0, f"Expected validation errors for {test_name}, but got none"

    @pytest.mark.contract
    def test_error_response_schema_validation(self, error_response_schema: Dict[str, Any]):
        """Verify ErrorResponse schema structure."""
        properties = error_response_schema["properties"]
        
        # Check error object structure
        assert "error" in properties
        error_props = properties["error"]["properties"]
        
        required_error_fields = {"code", "message"}
        assert set(error_props.keys()) >= required_error_fields
        
        # Validate required fields
        assert set(properties["error"]["required"]) == required_error_fields

    @pytest.mark.contract 
    def test_error_responses_against_schema(self, error_response_schema: Dict[str, Any]):
        """Test that error responses match the ErrorResponse schema."""
        validator = Draft7Validator(error_response_schema)
        
        # 404 Not Found response
        not_found_response = {
            "error": {
                "code": "job_not_found",
                "message": "Job with the specified ID was not found",
                "request_id": str(uuid.uuid4())
            }
        }
        
        # 401 Unauthorized response
        unauthorized_response = {
            "error": {
                "code": "unauthorized",
                "message": "Invalid or missing API key",
                "details": {"header": "X-API-Key"},
                "request_id": str(uuid.uuid4())
            }
        }
        
        for response_name, response_data in [
            ("not_found", not_found_response),
            ("unauthorized", unauthorized_response)
        ]:
            errors = list(validator.iter_errors(response_data))
            assert len(errors) == 0, f"Error response {response_name} failed validation: {errors}"


class TestJobsEndpointImplementation:
    """
    Tests that will fail until the endpoint is implemented.
    These demonstrate TDD approach - tests exist before implementation.
    """

    @pytest.mark.contract
    def test_jobs_endpoint_returns_job_status(self):
        """
        Test GET /jobs/{job_id} endpoint returns proper job status.
        
        This test will FAIL until the endpoint is implemented.
        Expected to fail with 404 or connection error.
        """
        job_id = uuid.uuid4()
        
        # This will fail since endpoint doesn't exist yet
        # In a real test, we would use httpx or similar to call:
        # response = client.get(f"/jobs/{job_id}", headers={"X-API-Key": "test-key"})
        # assert response.status_code == 200
        # validate_response_schema(response.json(), job_status_schema)
        
        pytest.fail(
            f"Endpoint GET /jobs/{job_id} not implemented yet. "
            "This is expected failure for TDD approach."
        )

    @pytest.mark.contract
    def test_jobs_endpoint_handles_not_found(self):
        """
        Test GET /jobs/{job_id} returns 404 for non-existent job.
        
        This test will FAIL until the endpoint is implemented.
        """
        non_existent_job_id = uuid.uuid4()
        
        # This will fail since endpoint doesn't exist yet
        pytest.fail(
            f"Endpoint GET /jobs/{non_existent_job_id} not implemented yet. "
            "Expected to return 404 for non-existent job. "
            "This is expected failure for TDD approach."
        )

    @pytest.mark.contract
    def test_jobs_endpoint_requires_authentication(self):
        """
        Test GET /jobs/{job_id} returns 401 without proper API key.
        
        This test will FAIL until the endpoint is implemented.
        """
        job_id = uuid.uuid4()
        
        # This will fail since endpoint doesn't exist yet
        pytest.fail(
            f"Endpoint GET /jobs/{job_id} not implemented yet. "
            "Expected to return 401 without X-API-Key header. "
            "This is expected failure for TDD approach."
        )

    @pytest.mark.contract
    def test_jobs_endpoint_validates_uuid_format(self):
        """
        Test GET /jobs/{job_id} validates UUID format in path parameter.
        
        This test will FAIL until the endpoint is implemented.
        """
        invalid_job_id = "not-a-uuid"
        
        # This will fail since endpoint doesn't exist yet
        pytest.fail(
            f"Endpoint GET /jobs/{invalid_job_id} not implemented yet. "
            "Expected to return 400 for invalid UUID format. "
            "This is expected failure for TDD approach."
        )