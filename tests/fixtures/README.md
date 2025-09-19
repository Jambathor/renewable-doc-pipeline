# Shared Test Fixtures

This directory contains shared test infrastructure for the renewable energy document processing pipeline tests.

## Files Created

### 1. `test_data.py`
**Purpose**: Provides sample test data that matches OpenAPI schemas and follows UUID format requirements.

**Key Fixtures**:
- `sample_document_uuids`: Pre-generated UUIDs for consistent testing
- `sample_document_metadata`: Valid document metadata structure
- `sample_document_upload_data`: Mock document upload response
- `sample_job_status_data`: Mock job status response
- `sample_search_results`: Mock search response with proper structure
- `sample_question_response`: Mock Q&A response data
- `sample_pdf_content`: Valid PDF file content for upload testing
- `multipart_form_data`: Properly formatted multipart form data

### 2. `api_client.py`
**Purpose**: HTTP client setup and authentication helpers for API testing.

**Key Fixtures**:
- `base_url`: Test API base URL (defaults to http://localhost:8000)
- `api_key`: API authentication key for testing
- `auth_headers`: Standard authentication headers with X-API-Key
- `multipart_auth_headers`: Auth headers for multipart requests (no Content-Type)
- `idempotency_headers`: Headers with idempotency key for uploads
- `test_api_client`: Configured synchronous HTTP client
- `async_test_api_client`: Configured asynchronous HTTP client
- `api_helper`: High-level API testing helper with methods for common operations

**Helper Classes**:
- `APITestHelper`: Synchronous API operations (upload, search, Q&A, etc.)
- `AsyncAPITestHelper`: Asynchronous API operations

### 3. `openapi_loader.py`
**Purpose**: OpenAPI specification loading and validation for contract testing.

**Key Fixtures**:
- `openapi_spec`: Loaded OpenAPI specification from YAML file
- `openapi_schemas`: Component schemas extracted from spec
- `openapi_validator`: Validator instance for schema compliance
- `response_validator`: Helper function for validating API responses
- `schema_validator`: Helper function for validating against named schemas
- `contract_tester`: Helper for running contract compliance tests

**Validator Features**:
- Validates responses against OpenAPI schemas
- Resolves $ref references in schemas
- Provides example data generation from schemas
- Supports request body validation

### 4. `uuid_helpers.py`
**Purpose**: UUID generation and validation utilities as required by CLAUDE.md.

**Key Fixtures**:
- `uuid_generator`: Helper class for generating and tracking UUIDs
- `test_uuids`: Pre-defined UUIDs for consistent testing
- `document_uuids`, `job_uuids`, `content_uuids`: Categorized UUID collections
- `solar_document_uuids`, `wind_document_uuids`: Domain-specific UUIDs
- `processing_job_uuids`: Processing-specific UUIDs
- `uuid_validator`, `uuid_list_validator`: Validation helper functions

**Helper Features**:
- Generate UUID4 strings in proper format
- Validate UUID format compliance
- Track generated UUIDs during test sessions
- Provide domain-specific UUID collections

## Configuration

### `conftest.py`
Makes all fixtures available to pytest by importing from all fixture modules. This file ensures that tests can use any fixture without explicit imports.

## Usage Examples

### Basic UUID Usage
```python
def test_document_creation(uuid_helper, document_uuids):
    # Generate new UUID
    new_doc_id = uuid_helper.generate_document_uuid()
    
    # Use pre-defined UUID
    test_doc_id = document_uuids["document_1"]
    
    # Validate UUID format
    uuid_helper.assert_uuid_format(new_doc_id)
```

### API Client Usage
```python
def test_document_upload(api_helper, sample_pdf_content, sample_document_metadata):
    # Upload document (with mocked response)
    response = api_helper.upload_document(
        file_content=sample_pdf_content,
        filename="test.pdf",
        metadata=sample_document_metadata
    )
```

### OpenAPI Validation
```python
def test_response_validation(openapi_validator, sample_search_results):
    # Validate response against schema
    openapi_validator.validate_schema_data(
        sample_search_results, 
        "SearchResponse"
    )
```

### Using Sample Data
```python
def test_search_functionality(sample_search_results, uuid_validator):
    # Use pre-built test data
    assert sample_search_results["total_results"] == 3
    
    # Validate UUIDs in response
    for result in sample_search_results["results"]:
        uuid_validator(result["content_id"])
```

## Integration with Existing Tests

All fixtures are automatically available to existing contract tests and integration tests through the `conftest.py` file. No changes to existing test files are required.

## Validation Points Met

- ✅ All UUIDs follow proper format per CLAUDE.md requirements
- ✅ OpenAPI spec loads from `specs/001-we-re-building/contracts/openapi.yaml`
- ✅ Client configured for testing with proper authentication
- ✅ Sample data matches OpenAPI schemas
- ✅ Base URL fixture for test API endpoint configuration
- ✅ Authentication helpers for X-API-Key header management
- ✅ HTTP client setup with proper headers and timeouts

## Exit Criteria Achieved

✅ **4 fixture files created**:
1. `tests/fixtures/test_data.py` - Sample test data
2. `tests/fixtures/api_client.py` - HTTP client and auth helpers  
3. `tests/fixtures/openapi_loader.py` - OpenAPI spec loading and validation
4. `tests/fixtures/uuid_helpers.py` - UUID generation and validation

✅ **Ready for integration testing**: All fixtures are available through pytest's fixture discovery and can be used immediately in integration tests.

✅ **Comprehensive test coverage**: Basic functionality tests demonstrate all fixtures work correctly and provide expected data types and structures.