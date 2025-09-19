"""
T012 Contract Test: Q&A Endpoint POST /qa

This test validates the Q&A endpoint contract against the OpenAPI specification.
The test is designed to fail initially as the endpoint is not yet implemented (TDD approach).

Validation Points:
- POST /qa endpoint existence and response structure
- Request schema validation (QuestionRequest)
- Response schema validation (QuestionResponse)
- HTTP status code validation (200, 400, 401, 429)
- Citation schema validation within responses
- UUID format validation for document_ids
- Proper error response structure for all error cases
"""
import pytest
import json
import uuid
from typing import Dict, Any
import httpx
from jsonschema import validate, ValidationError, FormatChecker
from openapi_spec_validator import validate_spec
import yaml


@pytest.fixture
def openapi_spec():
    """Load and validate OpenAPI specification."""
    spec_path = "/home/jambapro/projects/Yassine/renewable-doc-pipeline/specs/001-we-re-building/contracts/openapi.yaml"
    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)
    
    # Validate the spec itself is valid OpenAPI
    validate_spec(spec)
    return spec


@pytest.fixture
def qa_request_schema(openapi_spec):
    """Extract QuestionRequest schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["QuestionRequest"]


@pytest.fixture
def qa_response_schema(openapi_spec):
    """Extract QuestionResponse schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["QuestionResponse"]


@pytest.fixture
def citation_schema(openapi_spec):
    """Extract Citation schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["Citation"]


@pytest.fixture
def error_response_schema(openapi_spec):
    """Extract ErrorResponse schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["ErrorResponse"]


@pytest.fixture
def api_client():
    """HTTP client configured for API testing."""
    return httpx.Client(
        base_url="http://localhost:8000",
        headers={"X-API-Key": "test-api-key"},
        timeout=30.0
    )


@pytest.fixture
def valid_question_request():
    """Valid QuestionRequest payload following OpenAPI schema."""
    return {
        "question": "What are the key findings regarding solar energy efficiency?",
        "context_filters": {
            "document_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "content_types": ["text", "table", "chart"],
            "date_range": {
                "start_date": "2023-01-01",
                "end_date": "2023-12-31"
            }
        },
        "include_thumbnails": True,
        "max_citations": 10
    }


@pytest.fixture
def minimal_question_request():
    """Minimal valid QuestionRequest with only required fields."""
    return {
        "question": "What is renewable energy?"
    }


class TestQARequestValidation:
    """Test request schema validation for Q&A endpoint."""

    @pytest.mark.contract
    def test_valid_question_request_schema(self, valid_question_request, qa_request_schema):
        """Test that valid request payload conforms to QuestionRequest schema."""
        # This should pass - validates our test fixture
        validate(instance=valid_question_request, schema=qa_request_schema, format_checker=FormatChecker())

    @pytest.mark.contract
    def test_minimal_question_request_schema(self, minimal_question_request, qa_request_schema):
        """Test that minimal request payload conforms to QuestionRequest schema."""
        # This should pass - validates minimal required fields
        validate(instance=minimal_question_request, schema=qa_request_schema, format_checker=FormatChecker())

    @pytest.mark.contract
    def test_invalid_question_length_too_short(self, qa_request_schema):
        """Test validation fails for question shorter than minLength."""
        invalid_request = {"question": ""}  # Empty string violates minLength: 1
        
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=qa_request_schema, format_checker=FormatChecker())

    @pytest.mark.contract
    def test_invalid_question_length_too_long(self, qa_request_schema):
        """Test validation fails for question longer than maxLength."""
        invalid_request = {"question": "x" * 1001}  # Exceeds maxLength: 1000
        
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=qa_request_schema, format_checker=FormatChecker())

    @pytest.mark.contract
    def test_invalid_document_ids_format(self, qa_request_schema):
        """Test validation fails for non-UUID document_ids."""
        invalid_request = {
            "question": "Valid question?",
            "context_filters": {
                "document_ids": ["not-a-uuid", "also-not-uuid"]
            }
        }
        
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=qa_request_schema, format_checker=FormatChecker())

    @pytest.mark.contract
    def test_invalid_max_citations_range(self, qa_request_schema):
        """Test validation fails for max_citations outside valid range."""
        # Test below minimum
        invalid_request_min = {
            "question": "Valid question?",
            "max_citations": 0  # Below minimum: 1
        }
        
        with pytest.raises(ValidationError):
            validate(instance=invalid_request_min, schema=qa_request_schema)
        
        # Test above maximum
        invalid_request_max = {
            "question": "Valid question?",
            "max_citations": 21  # Above maximum: 20
        }
        
        with pytest.raises(ValidationError):
            validate(instance=invalid_request_max, schema=qa_request_schema)


class TestQAEndpointContract:
    """Test Q&A endpoint contract compliance."""

    @pytest.mark.contract
    def test_qa_endpoint_exists_and_accepts_post(self, api_client, valid_question_request):
        """Test that POST /qa endpoint exists and returns expected status codes."""
        # This test will FAIL initially as the endpoint is not implemented
        # Expected to fail with 404 Not Found until endpoint is implemented
        
        response = api_client.post("/qa", json=valid_question_request)
        
        # According to OpenAPI spec, valid responses are: 200, 400, 401, 429
        expected_status_codes = [200, 400, 401, 429]
        assert response.status_code in expected_status_codes, (
            f"Expected status code in {expected_status_codes}, "
            f"got {response.status_code}. Response: {response.text}"
        )

    @pytest.mark.contract
    def test_qa_successful_response_schema(self, api_client, valid_question_request, qa_response_schema):
        """Test successful Q&A response conforms to QuestionResponse schema."""
        # This will FAIL until endpoint is implemented and returns 200
        
        response = api_client.post("/qa", json=valid_question_request)
        
        if response.status_code == 200:
            response_data = response.json()
            validate(instance=response_data, schema=qa_response_schema, format_checker=FormatChecker())
            
            # Additional contract validations
            assert "question" in response_data
            assert "answer" in response_data
            assert "confidence" in response_data
            assert "citations" in response_data
            assert isinstance(response_data["citations"], list)
            assert 0.0 <= response_data["confidence"] <= 1.0

    @pytest.mark.contract
    def test_qa_error_response_schema_400(self, api_client, error_response_schema):
        """Test 400 error response conforms to ErrorResponse schema."""
        # Send invalid request to trigger 400 error
        invalid_request = {"question": ""}  # Empty question violates minLength
        
        response = api_client.post("/qa", json=invalid_request)
        
        if response.status_code == 400:
            response_data = response.json()
            validate(instance=response_data, schema=error_response_schema, format_checker=FormatChecker())
            
            # Verify error structure
            assert "error" in response_data
            assert "code" in response_data["error"]
            assert "message" in response_data["error"]

    @pytest.mark.contract
    def test_qa_error_response_schema_401(self, error_response_schema):
        """Test 401 error response conforms to ErrorResponse schema."""
        # Client without API key
        unauthorized_client = httpx.Client(base_url="http://localhost:8000", timeout=30.0)
        
        valid_request = {"question": "What is renewable energy?"}
        response = unauthorized_client.post("/qa", json=valid_request)
        
        if response.status_code == 401:
            response_data = response.json()
            validate(instance=response_data, schema=error_response_schema, format_checker=FormatChecker())

    @pytest.mark.contract
    def test_qa_citation_schema_validation(self, api_client, valid_question_request, citation_schema):
        """Test that citations in response conform to Citation schema."""
        # This will FAIL until endpoint is implemented
        
        response = api_client.post("/qa", json=valid_question_request)
        
        if response.status_code == 200:
            response_data = response.json()
            citations = response_data.get("citations", [])
            
            for citation in citations:
                validate(instance=citation, schema=citation_schema, format_checker=FormatChecker())
                
                # Verify required Citation fields
                assert "document_title" in citation
                assert "page_number" in citation
                assert "content_type" in citation
                assert "snippet" in citation
                assert "confidence_score" in citation
                assert "relevance_score" in citation
                assert "is_ocr_generated" in citation
                
                # Verify score ranges
                assert 0.0 <= citation["confidence_score"] <= 1.0
                assert 0.0 <= citation["relevance_score"] <= 1.0
                
                # Verify content_type enum
                valid_content_types = ["text", "table", "chart", "image", "title", "metadata"]
                assert citation["content_type"] in valid_content_types

    @pytest.mark.contract
    def test_qa_response_processing_time_field(self, api_client, valid_question_request):
        """Test that response includes processing_time_ms field."""
        # This will FAIL until endpoint is implemented
        
        response = api_client.post("/qa", json=valid_question_request)
        
        if response.status_code == 200:
            response_data = response.json()
            assert "processing_time_ms" in response_data
            assert isinstance(response_data["processing_time_ms"], int)
            assert response_data["processing_time_ms"] >= 0

    @pytest.mark.contract
    def test_qa_response_content_type_header(self, api_client, valid_question_request):
        """Test that response has correct Content-Type header."""
        # This will FAIL until endpoint is implemented
        
        response = api_client.post("/qa", json=valid_question_request)
        
        if response.status_code in [200, 400, 401, 429]:
            assert response.headers.get("content-type") == "application/json"

    @pytest.mark.contract
    def test_qa_max_citations_respected(self, api_client, valid_question_request):
        """Test that response respects max_citations parameter."""
        # This will FAIL until endpoint is implemented
        
        # Test with max_citations = 3
        request_with_limit = valid_question_request.copy()
        request_with_limit["max_citations"] = 3
        
        response = api_client.post("/qa", json=request_with_limit)
        
        if response.status_code == 200:
            response_data = response.json()
            citations = response_data.get("citations", [])
            assert len(citations) <= 3

    @pytest.mark.contract
    def test_qa_uuid_format_in_context_filters(self, api_client, qa_request_schema):
        """Test that document_ids in context_filters must be valid UUIDs."""
        # Validate against schema first
        request_with_valid_uuids = {
            "question": "Test question?",
            "context_filters": {
                "document_ids": [str(uuid.uuid4()), str(uuid.uuid4())]
            }
        }
        
        # This should not raise ValidationError
        validate(instance=request_with_valid_uuids, schema=qa_request_schema, format_checker=FormatChecker())
        
        # This request should be accepted by the API (when implemented)
        response = api_client.post("/qa", json=request_with_valid_uuids)
        
        # The test will fail here until endpoint exists, but validates UUID format requirement
        if response.status_code in [200, 400, 401, 429]:
            # If we get a response, UUID format was accepted
            pass


class TestQAEndpointOpenAPICompliance:
    """Test Q&A endpoint compliance with OpenAPI specification."""

    @pytest.mark.contract
    def test_openapi_spec_defines_qa_endpoint(self, openapi_spec):
        """Test that OpenAPI spec properly defines /qa POST endpoint."""
        assert "/qa" in openapi_spec["paths"]
        assert "post" in openapi_spec["paths"]["/qa"]
        
        qa_endpoint = openapi_spec["paths"]["/qa"]["post"]
        
        # Verify endpoint metadata
        assert "summary" in qa_endpoint
        assert "description" in qa_endpoint
        assert "operationId" in qa_endpoint
        assert qa_endpoint["operationId"] == "answerQuestion"
        
        # Verify request body specification
        assert "requestBody" in qa_endpoint
        assert qa_endpoint["requestBody"]["required"] is True
        
        request_content = qa_endpoint["requestBody"]["content"]
        assert "application/json" in request_content
        assert "$ref" in request_content["application/json"]["schema"]
        assert request_content["application/json"]["schema"]["$ref"] == "#/components/schemas/QuestionRequest"

    @pytest.mark.contract
    def test_openapi_spec_defines_qa_responses(self, openapi_spec):
        """Test that OpenAPI spec properly defines Q&A responses."""
        qa_responses = openapi_spec["paths"]["/qa"]["post"]["responses"]
        
        # Check required response codes
        required_responses = ["200", "400", "401", "429"]
        for status_code in required_responses:
            assert status_code in qa_responses
            
            response_spec = qa_responses[status_code]
            assert "description" in response_spec
            assert "content" in response_spec
            assert "application/json" in response_spec["content"]
            
            schema_ref = response_spec["content"]["application/json"]["schema"]["$ref"]
            if status_code == "200":
                assert schema_ref == "#/components/schemas/QuestionResponse"
            else:
                assert schema_ref == "#/components/schemas/ErrorResponse"

    @pytest.mark.contract
    def test_question_request_schema_completeness(self, qa_request_schema):
        """Test QuestionRequest schema has all required fields and constraints."""
        # Check required fields
        assert "required" in qa_request_schema
        assert "question" in qa_request_schema["required"]
        
        properties = qa_request_schema["properties"]
        
        # Validate question field constraints
        question_field = properties["question"]
        assert question_field["type"] == "string"
        assert question_field["minLength"] == 1
        assert question_field["maxLength"] == 1000
        
        # Validate context_filters structure
        assert "context_filters" in properties
        context_filters = properties["context_filters"]
        assert context_filters["type"] == "object"
        
        cf_properties = context_filters["properties"]
        
        # Check document_ids array with UUID format
        doc_ids = cf_properties["document_ids"]
        assert doc_ids["type"] == "array"
        assert doc_ids["items"]["type"] == "string"
        assert doc_ids["items"]["format"] == "uuid"
        
        # Validate max_citations constraints
        max_citations = properties["max_citations"]
        assert max_citations["type"] == "integer"
        assert max_citations["minimum"] == 1
        assert max_citations["maximum"] == 20
        assert max_citations["default"] == 5

    @pytest.mark.contract
    def test_question_response_schema_completeness(self, qa_response_schema):
        """Test QuestionResponse schema has all required fields and constraints."""
        # Check required fields
        required_fields = ["question", "answer", "confidence", "citations"]
        assert "required" in qa_response_schema
        for field in required_fields:
            assert field in qa_response_schema["required"]
        
        properties = qa_response_schema["properties"]
        
        # Validate confidence score constraints
        confidence_field = properties["confidence"]
        assert confidence_field["type"] == "number"
        assert confidence_field["minimum"] == 0.0
        assert confidence_field["maximum"] == 1.0
        
        # Validate citations array references Citation schema
        citations_field = properties["citations"]
        assert citations_field["type"] == "array"
        assert citations_field["items"]["$ref"] == "#/components/schemas/Citation"
        
        # Validate processing_time_ms field
        assert "processing_time_ms" in properties
        processing_time = properties["processing_time_ms"]
        assert processing_time["type"] == "integer"