"""
T015 Contract test for health endpoint - MUST FAIL for TDD

This test validates the health endpoint contract against the OpenAPI specification.
It targets a non-existent endpoint to ensure the test fails as expected during TDD.
"""

import json
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest
import yaml
from jsonschema import ValidationError, validate
from openapi_spec_validator import validate_spec

# Load OpenAPI specification
SPEC_PATH = Path(__file__).parent.parent.parent / "specs" / "001-we-re-building" / "contracts" / "openapi.yaml"


@pytest.fixture
def openapi_spec() -> dict[str, Any]:
    """Load and validate OpenAPI specification."""
    with open(SPEC_PATH) as f:
        spec = yaml.safe_load(f)

    # Validate the spec itself is valid OpenAPI
    validate_spec(spec)
    return spec


@pytest.fixture
def health_schema(openapi_spec: dict[str, Any]) -> dict[str, Any]:
    """Extract HealthResponse schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["HealthResponse"]


@pytest.mark.contract
class TestHealthEndpointContract:
    """Contract tests for health endpoint validation."""

    BASE_URL = "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_health_endpoint_200_response_schema(self, health_schema: dict[str, Any]):
        """
        Test GET /healthz returns 200 with valid HealthResponse schema.

        This test WILL FAIL because the endpoint doesn't exist yet (TDD).
        Validates:
        - HTTP 200 status code
        - HealthResponse schema compliance
        - Required fields: status, timestamp, version
        - status enum: [healthy, unhealthy]
        - dependencies object with proper enum values
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/healthz")

            # Validate HTTP status code from OpenAPI spec
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Validate content type
            assert response.headers.get("content-type") == "application/json", \
                f"Expected application/json, got {response.headers.get('content-type')}"

            # Parse response body
            response_data = response.json()

            # Validate against HealthResponse schema
            validate(instance=response_data, schema=health_schema)

            # Additional contract validations
            assert "status" in response_data
            assert response_data["status"] in ["healthy", "unhealthy"]
            assert "timestamp" in response_data
            assert "version" in response_data

            # Validate dependencies if present (not required in schema)
            if "dependencies" in response_data:
                deps = response_data["dependencies"]
                valid_dependency_statuses = ["healthy", "unhealthy"]

                for dep_name in ["database", "vector_store", "storage", "queue"]:
                    if dep_name in deps:
                        assert deps[dep_name] in valid_dependency_statuses, \
                            f"Invalid dependency status for {dep_name}: {deps[dep_name]}"

    @pytest.mark.asyncio
    async def test_health_endpoint_503_response_schema(self, health_schema: dict[str, Any]):
        """
        Test GET /healthz can return 503 with valid HealthResponse schema.

        This test WILL FAIL because the endpoint doesn't exist yet (TDD).
        Validates:
        - HTTP 503 status code is valid per OpenAPI spec
        - HealthResponse schema compliance for unhealthy state
        - Same schema applies for both 200 and 503 responses
        """
        # This test will fail because endpoint doesn't exist
        # When implemented, this should handle cases where dependencies are unhealthy
        async with httpx.AsyncClient() as client:
            # This will fail with connection error or 404
            response = await client.get(f"{self.BASE_URL}/healthz")

            # If we somehow get a response, validate it could be 503
            if response.status_code == 503:
                response_data = response.json()
                validate(instance=response_data, schema=health_schema)
                assert response_data["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_endpoint_no_authentication_required(self, openapi_spec: dict[str, Any]):
        """
        Test GET /healthz endpoint requires no authentication.

        This test WILL FAIL because the endpoint doesn't exist yet (TDD).
        Validates:
        - Endpoint is marked with security: [] in OpenAPI spec
        - No X-API-Key header required
        - Public endpoint accessible without authentication
        """
        # Verify OpenAPI spec shows no security required
        health_endpoint = openapi_spec["paths"]["/healthz"]["get"]
        assert "security" in health_endpoint, "Health endpoint should specify security settings"
        assert health_endpoint["security"] == [], "Health endpoint should have empty security array"

        # Test actual endpoint without auth
        async with httpx.AsyncClient() as client:
            # Don't include X-API-Key header
            response = await client.get(f"{self.BASE_URL}/healthz")

            # This will fail because endpoint doesn't exist yet
            assert response.status_code in [200, 503], \
                f"Health endpoint should return 200 or 503, not {response.status_code}"

    def test_openapi_spec_health_endpoint_definition(self, openapi_spec: dict[str, Any]):
        """
        Test OpenAPI specification correctly defines health endpoint.

        This test validates the OpenAPI spec structure itself and should PASS.
        Validates:
        - /healthz path exists in OpenAPI spec
        - GET operation defined
        - Correct response schemas
        - Security configuration
        """
        # Validate path exists
        assert "/healthz" in openapi_spec["paths"], "Health endpoint path missing from OpenAPI spec"

        health_path = openapi_spec["paths"]["/healthz"]
        assert "get" in health_path, "GET operation missing for health endpoint"

        get_operation = health_path["get"]

        # Validate operation details
        assert get_operation["operationId"] == "healthCheck"
        assert get_operation["summary"] == "Health check endpoint"
        assert get_operation["security"] == [], "Health endpoint should not require authentication"

        # Validate responses
        responses = get_operation["responses"]
        assert "200" in responses, "200 response missing"
        assert "503" in responses, "503 response missing"

        # Validate response schemas reference HealthResponse
        for status_code in ["200", "503"]:
            response_def = responses[status_code]
            content = response_def["content"]["application/json"]
            schema_ref = content["schema"]["$ref"]
            assert schema_ref == "#/components/schemas/HealthResponse", \
                f"Response {status_code} should reference HealthResponse schema"

    def test_health_response_schema_structure(self, openapi_spec: dict[str, Any]):
        """
        Test HealthResponse schema has correct structure.

        This test validates the schema definition and should PASS.
        Validates:
        - Required fields are properly defined
        - Enum values are correct
        - Schema structure matches requirements
        """
        health_schema = openapi_spec["components"]["schemas"]["HealthResponse"]

        # Validate required fields
        required_fields = health_schema["required"]
        assert "status" in required_fields
        assert "timestamp" in required_fields
        assert "version" in required_fields
        assert "dependencies" not in required_fields, "dependencies should be optional"

        # Validate status enum
        status_property = health_schema["properties"]["status"]
        assert status_property["enum"] == ["healthy", "unhealthy"]

        # Validate timestamp format
        timestamp_property = health_schema["properties"]["timestamp"]
        assert timestamp_property["format"] == "date-time"

        # Validate dependencies structure if present
        if "dependencies" in health_schema["properties"]:
            deps_schema = health_schema["properties"]["dependencies"]
            deps_properties = deps_schema["properties"]

            for dep_name in ["database", "vector_store", "storage", "queue"]:
                if dep_name in deps_properties:
                    dep_schema = deps_properties[dep_name]
                    assert dep_schema["enum"] == ["healthy", "unhealthy"], \
                        f"Dependency {dep_name} should have correct enum values"


@pytest.mark.contract
class TestHealthEndpointFailureScenarios:
    """Test scenarios that should cause the contract tests to fail during TDD."""

    BASE_URL = "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_non_existent_endpoint_fails(self):
        """
        Test that hitting non-existent endpoint fails as expected.

        This test WILL FAIL and demonstrates TDD approach.
        When the health endpoint is implemented, the previous tests will pass.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/healthz")
                # If we get here, either:
                # 1. The endpoint exists (unexpected during initial TDD)
                # 2. We got a different error response

                # For TDD, we expect this to fail with connection error or 404
                if response.status_code == 404:
                    pytest.fail("Endpoint returned 404 - expected during TDD phase")
                elif response.status_code in [200, 503]:
                    pytest.fail("Endpoint unexpectedly exists and returns valid response")
                else:
                    pytest.fail(f"Unexpected response code: {response.status_code}")

            except httpx.ConnectError:
                # Expected during TDD - service not running
                pytest.fail("Connection failed - expected during TDD when service not implemented")
            except Exception as e:
                # Any other exception is expected during TDD
                pytest.fail(f"Expected failure during TDD: {type(e).__name__}: {e}")
