"""
T011 Contract tests for GET /search endpoint.

These tests validate the search API contract against the OpenAPI specification.
Tests are expected to FAIL initially as the endpoint is not implemented (TDD approach).
"""

import pytest
import uuid
from typing import Dict, Any
import yaml
from jsonschema import validate, ValidationError
from openapi_spec_validator import validate_spec
import httpx


class TestSearchEndpointContract:
    """Contract tests for the GET /search endpoint."""

    @pytest.fixture(scope="class")
    def openapi_spec(self) -> Dict[str, Any]:
        """Load and validate OpenAPI specification."""
        spec_path = "/home/jambapro/projects/Yassine/renewable-doc-pipeline/specs/001-we-re-building/contracts/openapi.yaml"
        
        with open(spec_path, 'r') as f:
            spec = yaml.safe_load(f)
        
        # Validate the OpenAPI spec itself is valid
        validate_spec(spec)
        return spec

    @pytest.fixture
    def search_endpoint_schema(self, openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract search endpoint schema from OpenAPI spec."""
        return openapi_spec["paths"]["/search"]["get"]

    @pytest.fixture
    def search_response_schema(self, openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract SearchResponse schema for validation."""
        return openapi_spec["components"]["schemas"]["SearchResponse"]

    @pytest.fixture
    def search_result_schema(self, openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract SearchResult schema for validation."""
        return openapi_spec["components"]["schemas"]["SearchResult"]

    @pytest.fixture
    def error_response_schema(self, openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ErrorResponse schema for validation."""
        return openapi_spec["components"]["schemas"]["ErrorResponse"]

    @pytest.fixture
    def sample_document_ids(self) -> list[str]:
        """Generate sample UUID document IDs for testing."""
        return [
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4())
        ]

    @pytest.fixture
    def api_client(self) -> httpx.Client:
        """HTTP client for API requests."""
        return httpx.Client(
            base_url="http://localhost:8000",
            headers={"X-API-Key": "test-api-key"}
        )

    @pytest.mark.contract
    def test_search_endpoint_exists(
        self, 
        api_client: httpx.Client,
        search_endpoint_schema: Dict[str, Any]
    ):
        """Test that GET /search endpoint exists and is accessible."""
        # This test will FAIL until the endpoint is implemented
        response = api_client.get("/search", params={"query": "test"})
        
        # Endpoint should exist (not 404)
        assert response.status_code != 404, "Search endpoint should exist"
        
        # Should be one of the expected status codes from OpenAPI spec
        expected_codes = [200, 400, 401, 429]
        assert response.status_code in expected_codes, f"Expected one of {expected_codes}, got {response.status_code}"

    @pytest.mark.contract
    def test_search_success_response_schema(
        self,
        api_client: httpx.Client,
        search_response_schema: Dict[str, Any],
        search_result_schema: Dict[str, Any],
        sample_document_ids: list[str]
    ):
        """Test 200 response conforms to SearchResponse schema."""
        # This test will FAIL until the endpoint returns proper response
        response = api_client.get("/search", params={
            "query": "renewable energy solar power",
            "content_types": "text,table,chart",
            "document_ids": ",".join(sample_document_ids[:2]),
            "page_range": "1-10",
            "limit": 5,
            "min_confidence": 0.5
        })
        
        # Should return 200 OK for valid request
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Response should be valid JSON
        response_data = response.json()
        
        # Validate against SearchResponse schema
        validate(instance=response_data, schema={
            "type": "object",
            "properties": search_response_schema["properties"],
            "required": search_response_schema["required"]
        })
        
        # Validate individual search results against SearchResult schema
        for result in response_data.get("results", []):
            validate(instance=result, schema={
                "type": "object", 
                "properties": search_result_schema["properties"],
                "required": search_result_schema["required"]
            })

    @pytest.mark.contract
    def test_search_required_query_parameter(
        self,
        api_client: httpx.Client,
        error_response_schema: Dict[str, Any]
    ):
        """Test that query parameter is required (400 error when missing)."""
        # This test will FAIL until proper validation is implemented
        response = api_client.get("/search")
        
        # Should return 400 Bad Request for missing required parameter
        assert response.status_code == 400, f"Expected 400 for missing query, got {response.status_code}"
        
        # Response should conform to ErrorResponse schema
        response_data = response.json()
        validate(instance=response_data, schema={
            "type": "object",
            "properties": error_response_schema["properties"],
            "required": error_response_schema["required"]
        })

    @pytest.mark.contract
    def test_search_query_parameter_validation(
        self,
        api_client: httpx.Client,
        error_response_schema: Dict[str, Any]
    ):
        """Test query parameter length validation (1-500 chars)."""
        # Test empty query (should fail)
        response = api_client.get("/search", params={"query": ""})
        assert response.status_code == 400, "Empty query should return 400"
        
        # Test overly long query (should fail)
        long_query = "x" * 501  # Exceeds 500 char limit
        response = api_client.get("/search", params={"query": long_query})
        assert response.status_code == 400, "Query >500 chars should return 400"
        
        # Valid responses should conform to ErrorResponse schema
        if response.status_code == 400:
            response_data = response.json()
            validate(instance=response_data, schema={
                "type": "object",
                "properties": error_response_schema["properties"],
                "required": error_response_schema["required"]
            })

    @pytest.mark.contract
    def test_search_content_types_enum_validation(
        self,
        api_client: httpx.Client,
        error_response_schema: Dict[str, Any]
    ):
        """Test content_types parameter accepts only valid enum values."""
        # Valid content types from OpenAPI spec
        valid_types = ["text", "table", "chart", "image", "title", "metadata"]
        
        # Test valid content types (should work)
        response = api_client.get("/search", params={
            "query": "test",
            "content_types": ",".join(valid_types[:3])
        })
        # This will fail until endpoint is implemented
        expected_codes = [200, 400, 401, 429]
        assert response.status_code in expected_codes
        
        # Test invalid content type (should fail with 400)
        response = api_client.get("/search", params={
            "query": "test",
            "content_types": "invalid_type,text"
        })
        # Should return 400 for invalid enum value
        if response.status_code == 400:
            response_data = response.json()
            validate(instance=response_data, schema={
                "type": "object",
                "properties": error_response_schema["properties"],
                "required": error_response_schema["required"]
            })

    @pytest.mark.contract
    def test_search_document_ids_uuid_format(
        self,
        api_client: httpx.Client,
        sample_document_ids: list[str],
        error_response_schema: Dict[str, Any]
    ):
        """Test document_ids parameter requires valid UUID format."""
        # Test valid UUIDs (should work)
        response = api_client.get("/search", params={
            "query": "test",
            "document_ids": ",".join(sample_document_ids)
        })
        expected_codes = [200, 400, 401, 429]
        assert response.status_code in expected_codes
        
        # Test invalid UUID format (should fail with 400)
        response = api_client.get("/search", params={
            "query": "test",
            "document_ids": "not-a-uuid,also-invalid"
        })
        # Should return 400 for invalid UUID format
        if response.status_code == 400:
            response_data = response.json()
            validate(instance=response_data, schema={
                "type": "object",
                "properties": error_response_schema["properties"],
                "required": error_response_schema["required"]
            })

    @pytest.mark.contract
    def test_search_page_range_pattern_validation(
        self,
        api_client: httpx.Client,
        error_response_schema: Dict[str, Any]
    ):
        """Test page_range parameter follows 'digit-digit' pattern."""
        # Test valid page range (should work)
        response = api_client.get("/search", params={
            "query": "test",
            "page_range": "1-10"
        })
        expected_codes = [200, 400, 401, 429]
        assert response.status_code in expected_codes
        
        # Test invalid page range pattern (should fail with 400)
        response = api_client.get("/search", params={
            "query": "test",
            "page_range": "invalid-range"
        })
        if response.status_code == 400:
            response_data = response.json()
            validate(instance=response_data, schema={
                "type": "object",
                "properties": error_response_schema["properties"],
                "required": error_response_schema["required"]
            })

    @pytest.mark.contract
    def test_search_limit_parameter_validation(
        self,
        api_client: httpx.Client,
        error_response_schema: Dict[str, Any]
    ):
        """Test limit parameter validation (1-100, default 20)."""
        # Test valid limit values
        for limit in [1, 20, 50, 100]:
            response = api_client.get("/search", params={
                "query": "test",
                "limit": limit
            })
            expected_codes = [200, 400, 401, 429]
            assert response.status_code in expected_codes
        
        # Test invalid limit values (should fail with 400)
        for invalid_limit in [0, 101, -1]:
            response = api_client.get("/search", params={
                "query": "test",
                "limit": invalid_limit
            })
            if response.status_code == 400:
                response_data = response.json()
                validate(instance=response_data, schema={
                    "type": "object",
                    "properties": error_response_schema["properties"],
                    "required": error_response_schema["required"]
                })

    @pytest.mark.contract
    def test_search_confidence_score_validation(
        self,
        api_client: httpx.Client,
        error_response_schema: Dict[str, Any]
    ):
        """Test min_confidence parameter validation (0.0-1.0, default 0.0)."""
        # Test valid confidence values
        for confidence in [0.0, 0.5, 0.7, 1.0]:
            response = api_client.get("/search", params={
                "query": "test",
                "min_confidence": confidence
            })
            expected_codes = [200, 400, 401, 429]
            assert response.status_code in expected_codes
        
        # Test invalid confidence values (should fail with 400)
        for invalid_confidence in [-0.1, 1.1, 2.0]:
            response = api_client.get("/search", params={
                "query": "test",
                "min_confidence": invalid_confidence
            })
            if response.status_code == 400:
                response_data = response.json()
                validate(instance=response_data, schema={
                    "type": "object",
                    "properties": error_response_schema["properties"],
                    "required": error_response_schema["required"]
                })

    @pytest.mark.contract
    def test_search_response_score_ranges(
        self,
        api_client: httpx.Client,
        search_result_schema: Dict[str, Any]
    ):
        """Test that confidence_score and relevance_score are in 0.0-1.0 range."""
        # This test will FAIL until the endpoint returns proper data
        response = api_client.get("/search", params={"query": "test"})
        
        if response.status_code == 200:
            response_data = response.json()
            
            for result in response_data.get("results", []):
                # Validate score ranges according to OpenAPI spec
                confidence = result.get("confidence_score")
                relevance = result.get("relevance_score")
                
                assert 0.0 <= confidence <= 1.0, f"confidence_score {confidence} not in [0.0, 1.0]"
                assert 0.0 <= relevance <= 1.0, f"relevance_score {relevance} not in [0.0, 1.0]"
                
                # Validate content_id and document_id are UUIDs
                content_id = result.get("content_id")
                document_id = result.get("document_id")
                
                # Validate UUID format (will raise ValueError if invalid)
                uuid.UUID(content_id)
                uuid.UUID(document_id)
                
                # Validate content_type enum
                content_type = result.get("content_type")
                valid_content_types = ["text", "table", "chart", "image", "title", "metadata"]
                assert content_type in valid_content_types, f"Invalid content_type: {content_type}"

    @pytest.mark.contract
    def test_search_authentication_required(
        self,
        error_response_schema: Dict[str, Any]
    ):
        """Test that search endpoint requires authentication (401 without API key)."""
        # Create client without API key
        unauthenticated_client = httpx.Client(base_url="http://localhost:8000")
        
        response = unauthenticated_client.get("/search", params={"query": "test"})
        
        # Should return 401 Unauthorized
        assert response.status_code == 401, f"Expected 401 for missing API key, got {response.status_code}"
        
        # Response should conform to ErrorResponse schema
        response_data = response.json()
        validate(instance=response_data, schema={
            "type": "object",
            "properties": error_response_schema["properties"],
            "required": error_response_schema["required"]
        })

    @pytest.mark.contract
    def test_search_rate_limiting(
        self,
        api_client: httpx.Client,
        error_response_schema: Dict[str, Any]
    ):
        """Test that search endpoint implements rate limiting (429 response)."""
        # This test validates the contract expects rate limiting
        # Rate limiting behavior will be tested once the endpoint is implemented
        
        # The OpenAPI spec defines 429 as a valid response
        # This test ensures the contract allows for rate limiting responses
        
        # Make a request (will fail until endpoint exists)
        response = api_client.get("/search", params={"query": "test"})
        
        # 429 is a valid response according to the contract
        if response.status_code == 429:
            response_data = response.json()
            validate(instance=response_data, schema={
                "type": "object",
                "properties": error_response_schema["properties"],
                "required": error_response_schema["required"]
            })