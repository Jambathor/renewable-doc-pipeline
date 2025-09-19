"""
T016 Contract test for metrics endpoint.

This test is designed to FAIL initially (TDD approach) by testing against
a non-existent endpoint, then will be updated once the endpoint is implemented.
"""

from typing import Any, Dict

import httpx
import pytest
import yaml
from jsonschema import ValidationError
from jsonschema import validate as json_validate
from openapi_spec_validator import validate


@pytest.fixture
def openapi_spec() -> dict[str, Any]:
    """Load and validate the OpenAPI specification."""
    with open("/home/jambapro/projects/Yassine/renewable-doc-pipeline/specs/001-we-re-building/contracts/openapi.yaml") as f:
        spec = yaml.safe_load(f)

    # Validate the OpenAPI spec itself
    validate(spec)
    return spec


@pytest.fixture
def metrics_endpoint_spec(openapi_spec: dict[str, Any]) -> dict[str, Any]:
    """Extract metrics endpoint specification from OpenAPI spec."""
    return openapi_spec["paths"]["/metrics"]["get"]


@pytest.fixture
def error_response_schema(openapi_spec: dict[str, Any]) -> dict[str, Any]:
    """Extract error response schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["ErrorResponse"]


class TestMetricsEndpointContract:
    """Contract tests for the /metrics endpoint."""

    @pytest.mark.contract
    def test_metrics_endpoint_unauthenticated_request_fails(
        self,
        metrics_endpoint_spec: dict[str, Any],
        error_response_schema: dict[str, Any]
    ):
        """
        Test that unauthenticated request to metrics endpoint returns 401.

        This test will FAIL initially because the endpoint doesn't exist yet.
        """
        # Target non-existent endpoint to ensure test fails (TDD approach)
        base_url = "http://localhost:8000"

        with httpx.Client() as client:
            # Test without X-API-Key header
            response = client.get(f"{base_url}/metrics")

            # Validate response follows OpenAPI spec
            assert response.status_code == 401, (
                f"Expected 401 Unauthorized, got {response.status_code}. "
                f"Response: {response.text}"
            )

            # Response should be JSON for error case
            assert response.headers.get("content-type", "").startswith("application/json"), (
                f"Expected JSON content-type for error response, got {response.headers.get('content-type')}"
            )

            # Validate error response against schema
            error_response = response.json()
            json_validate(instance=error_response, schema=error_response_schema)

            # Verify error structure
            assert "error" in error_response
            assert "code" in error_response["error"]
            assert "message" in error_response["error"]
            assert error_response["error"]["code"] in ["unauthorized", "missing_api_key"]

    @pytest.mark.contract
    def test_metrics_endpoint_authenticated_request_success(
        self,
        metrics_endpoint_spec: dict[str, Any]
    ):
        """
        Test that authenticated request to metrics endpoint returns 200 with text/plain.

        This test will FAIL initially because the endpoint doesn't exist yet.
        """
        # Target non-existent endpoint to ensure test fails (TDD approach)
        base_url = "http://localhost:8000"
        headers = {"X-API-Key": "test-api-key-123"}

        with httpx.Client() as client:
            response = client.get(f"{base_url}/metrics", headers=headers)

            # Validate response follows OpenAPI spec
            assert response.status_code == 200, (
                f"Expected 200 OK with valid API key, got {response.status_code}. "
                f"Response: {response.text}"
            )

            # Response should be text/plain for success case (Prometheus format)
            content_type = response.headers.get("content-type", "")
            assert content_type.startswith("text/plain"), (
                f"Expected text/plain content-type for metrics response, got {content_type}"
            )

            # Validate that response is non-empty string
            response_text = response.text
            assert isinstance(response_text, str), "Response should be a string"
            assert len(response_text) > 0, "Response should not be empty"

            # Basic validation that it looks like Prometheus metrics format
            # Prometheus metrics typically contain lines with metric names and values
            lines = response_text.strip().split('\n')
            assert len(lines) > 0, "Should have at least one line of metrics"

            # Look for typical Prometheus metric patterns (at least one metric should exist)
            metric_lines = [line for line in lines if line and not line.startswith('#')]
            assert len(metric_lines) > 0, "Should have at least one metric line"

    @pytest.mark.contract
    def test_metrics_endpoint_with_invalid_api_key_fails(
        self,
        metrics_endpoint_spec: dict[str, Any],
        error_response_schema: dict[str, Any]
    ):
        """
        Test that request with invalid API key returns 401.

        This test will FAIL initially because the endpoint doesn't exist yet.
        """
        # Target non-existent endpoint to ensure test fails (TDD approach)
        base_url = "http://localhost:8000"
        headers = {"X-API-Key": "invalid-key"}

        with httpx.Client() as client:
            response = client.get(f"{base_url}/metrics", headers=headers)

            # Validate response follows OpenAPI spec
            assert response.status_code == 401, (
                f"Expected 401 Unauthorized with invalid API key, got {response.status_code}. "
                f"Response: {response.text}"
            )

            # Response should be JSON for error case
            assert response.headers.get("content-type", "").startswith("application/json"), (
                f"Expected JSON content-type for error response, got {response.headers.get('content-type')}"
            )

            # Validate error response against schema
            error_response = response.json()
            json_validate(instance=error_response, schema=error_response_schema)

            # Verify error structure
            assert "error" in error_response
            assert "code" in error_response["error"]
            assert "message" in error_response["error"]
            assert error_response["error"]["code"] in ["unauthorized", "invalid_api_key"]

    @pytest.mark.contract
    def test_openapi_spec_defines_metrics_endpoint_correctly(
        self,
        openapi_spec: dict[str, Any],
        metrics_endpoint_spec: dict[str, Any]
    ):
        """
        Test that OpenAPI spec correctly defines the metrics endpoint.

        This validates the contract specification itself.
        """
        # Verify endpoint exists in spec
        assert "/metrics" in openapi_spec["paths"], "Metrics endpoint should be defined in OpenAPI spec"
        assert "get" in openapi_spec["paths"]["/metrics"], "GET method should be defined for metrics endpoint"

        # Verify response definitions
        responses = metrics_endpoint_spec["responses"]

        # Check 200 response
        assert "200" in responses, "200 response should be defined"
        success_response = responses["200"]
        assert "content" in success_response, "200 response should have content definition"
        assert "text/plain" in success_response["content"], "200 response should define text/plain content type"

        # Check 401 response
        assert "401" in responses, "401 response should be defined"
        error_response = responses["401"]
        assert "content" in error_response, "401 response should have content definition"
        assert "application/json" in error_response["content"], "401 response should define JSON content type"

        # Verify security requirements (should inherit from global security)
        global_security = openapi_spec.get("security", [])
        assert len(global_security) > 0, "Global security should be defined"
        assert {"ApiKeyAuth": []} in global_security, "ApiKeyAuth should be in global security"

        # Verify operation ID and description
        assert "operationId" in metrics_endpoint_spec, "Operation ID should be defined"
        assert metrics_endpoint_spec["operationId"] == "getMetrics", "Operation ID should be 'getMetrics'"
        assert "description" in metrics_endpoint_spec, "Description should be defined"
        assert "prometheus" in metrics_endpoint_spec["description"].lower(), "Description should mention Prometheus"
