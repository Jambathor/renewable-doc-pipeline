"""
Basic tests to verify shared fixtures are working correctly.

These tests validate that all fixtures can be loaded and provide expected data types.
"""

import pytest
import httpx


def test_uuid_helper_basic(uuid_helper):
    """Test UUID helper basic functionality."""
    # Generate UUIDs
    doc_id = uuid_helper.generate_document_uuid()
    job_id = uuid_helper.generate_job_uuid()
    
    # Validate they are proper UUIDs
    assert uuid_helper.is_valid_uuid_format(doc_id)
    assert uuid_helper.is_valid_uuid_format(job_id)
    
    # Test assertion methods don't raise
    uuid_helper.assert_uuid_format(doc_id)
    uuid_helper.assert_uuid_format(job_id)


def test_test_uuids_fixture(test_uuids, uuid_helper):
    """Test that test UUIDs fixture provides valid UUIDs."""
    # Check we have expected UUID categories
    assert "document_1" in test_uuids
    assert "job_1" in test_uuids
    assert "content_1" in test_uuids
    
    # Validate all UUIDs are properly formatted (except request IDs which use custom format)
    for name, uuid_val in test_uuids.items():
        if not name.startswith("request_"):  # Skip request IDs as they use custom format
            uuid_helper.assert_uuid_format(uuid_val, f"test UUID {name}")


def test_sample_data_fixtures(
    sample_document_metadata,
    sample_document_upload_data,
    sample_search_results,
    sample_question_response
):
    """Test that sample data fixtures provide expected structure."""
    # Document metadata
    assert isinstance(sample_document_metadata, dict)
    assert "title" in sample_document_metadata
    assert "tags" in sample_document_metadata
    
    # Document upload data
    assert isinstance(sample_document_upload_data, dict)
    assert "document_id" in sample_document_upload_data
    assert "job_id" in sample_document_upload_data
    assert "filename" in sample_document_upload_data
    
    # Search results
    assert isinstance(sample_search_results, dict)
    assert "query" in sample_search_results
    assert "results" in sample_search_results
    assert isinstance(sample_search_results["results"], list)
    
    # Q&A response
    assert isinstance(sample_question_response, dict)
    assert "question" in sample_question_response
    assert "answer" in sample_question_response
    assert "citations" in sample_question_response


def test_api_client_fixtures(
    base_url,
    api_key,
    auth_headers,
    test_api_client,
    api_helper
):
    """Test that API client fixtures are properly configured."""
    # Base URL
    assert isinstance(base_url, str)
    assert base_url.startswith("http")
    
    # API key
    assert isinstance(api_key, str)
    assert len(api_key) > 0
    
    # Auth headers
    assert isinstance(auth_headers, dict)
    assert "X-API-Key" in auth_headers
    assert auth_headers["X-API-Key"] == api_key
    
    # HTTP client
    assert isinstance(test_api_client, httpx.Client)
    assert test_api_client.base_url == base_url
    
    # API helper
    assert api_helper is not None
    assert hasattr(api_helper, "get_endpoint_url")
    assert hasattr(api_helper, "upload_document")


def test_openapi_fixtures(
    openapi_spec,
    openapi_validator,
    openapi_schemas
):
    """Test that OpenAPI fixtures load correctly."""
    # OpenAPI spec
    assert isinstance(openapi_spec, dict)
    assert "openapi" in openapi_spec
    assert "paths" in openapi_spec
    assert "components" in openapi_spec
    
    # Schemas
    assert isinstance(openapi_schemas, dict)
    assert "DocumentUploadResponse" in openapi_schemas
    assert "SearchResponse" in openapi_schemas
    
    # Validator
    assert openapi_validator is not None
    assert hasattr(openapi_validator, "get_schema")
    assert hasattr(openapi_validator, "validate_schema_data")


def test_specialized_uuid_fixtures(
    solar_document_uuids,
    wind_document_uuids,
    processing_job_uuids,
    uuid_helper
):
    """Test specialized UUID fixtures."""
    # Solar document UUIDs
    assert isinstance(solar_document_uuids, dict)
    assert len(solar_document_uuids) > 0
    for uuid_val in solar_document_uuids.values():
        uuid_helper.assert_uuid_format(uuid_val)
    
    # Wind document UUIDs
    assert isinstance(wind_document_uuids, dict)
    assert len(wind_document_uuids) > 0
    for uuid_val in wind_document_uuids.values():
        uuid_helper.assert_uuid_format(uuid_val)
    
    # Processing job UUIDs
    assert isinstance(processing_job_uuids, dict)
    assert len(processing_job_uuids) > 0
    for uuid_val in processing_job_uuids.values():
        uuid_helper.assert_uuid_format(uuid_val)


def test_sample_pdf_content_fixture(sample_pdf_content):
    """Test that PDF content fixture provides valid data."""
    assert isinstance(sample_pdf_content, bytes)
    assert len(sample_pdf_content) > 0
    assert sample_pdf_content.startswith(b"%PDF")
    assert sample_pdf_content.endswith(b"%%EOF")


def test_auth_header_variations(
    auth_headers,
    multipart_auth_headers,
    idempotency_headers,
    api_key
):
    """Test different authentication header fixtures."""
    # Standard auth headers
    assert "X-API-Key" in auth_headers
    assert auth_headers["X-API-Key"] == api_key
    assert "Content-Type" in auth_headers
    
    # Multipart headers (no Content-Type)
    assert "X-API-Key" in multipart_auth_headers
    assert multipart_auth_headers["X-API-Key"] == api_key
    assert "Content-Type" not in multipart_auth_headers
    
    # Idempotency headers
    assert "X-API-Key" in idempotency_headers
    assert "Idempotency-Key" in idempotency_headers


def test_validation_helpers(
    uuid_validator,
    uuid_list_validator,
    response_uuid_validator,
    test_uuids
):
    """Test validation helper functions."""
    # UUID validator
    uuid_validator(test_uuids["document_1"], "test document")
    
    # UUID list validator
    uuid_list = [test_uuids["document_1"], test_uuids["job_1"]]
    uuid_list_validator(uuid_list, "test UUID list")
    
    # Response UUID validator
    response_data = {
        "document_id": test_uuids["document_1"],
        "job_id": test_uuids["job_1"]
    }
    response_uuid_validator(response_data, ["document_id", "job_id"])


@pytest.mark.asyncio
async def test_async_fixture_works(async_api_helper):
    """Test that async fixture can be used."""
    # Just verify we can access the async helper
    helper = await async_api_helper.__anext__()
    assert helper is not None
    assert hasattr(helper, "check_health")
    assert hasattr(helper, "upload_document")


def test_mock_response_fixtures(
    mock_document_response_with_uuids,
    mock_search_results_with_uuids,
    uuid_helper
):
    """Test mock response fixtures with UUIDs."""
    # Mock document response
    doc_response = mock_document_response_with_uuids
    assert "document_id" in doc_response
    assert "job_id" in doc_response
    uuid_helper.assert_uuid_format(doc_response["document_id"])
    uuid_helper.assert_uuid_format(doc_response["job_id"])
    
    # Mock search results
    search_response = mock_search_results_with_uuids
    assert "results" in search_response
    for result in search_response["results"]:
        uuid_helper.assert_uuid_format(result["content_id"])
        uuid_helper.assert_uuid_format(result["document_id"])


def test_multipart_form_data_fixture(multipart_form_data, sample_pdf_content):
    """Test multipart form data fixture."""
    assert "files" in multipart_form_data
    assert "data" in multipart_form_data
    
    # Check file data
    files = multipart_form_data["files"]
    assert "file" in files
    filename, content, content_type = files["file"]
    assert filename.endswith(".pdf")
    assert content == sample_pdf_content
    assert content_type == "application/pdf"
    
    # Check metadata
    data = multipart_form_data["data"]
    assert "metadata" in data
    import json
    metadata = json.loads(data["metadata"])
    assert isinstance(metadata, dict)