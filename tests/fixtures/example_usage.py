"""
Example usage of shared fixtures for renewable energy pipeline tests.

This file demonstrates how to use the shared fixtures in actual test implementations.
"""

import pytest


def test_example_uuid_usage(uuid_helper, test_uuids):
    """Example of using UUID helpers in tests."""
    # Generate new UUIDs
    doc_id = uuid_helper.generate_document_uuid()
    job_id = uuid_helper.generate_job_uuid()
    
    # Validate UUID formats
    uuid_helper.assert_uuid_format(doc_id, "generated document ID")
    uuid_helper.assert_uuid_format(job_id, "generated job ID")
    
    # Use pre-defined test UUIDs
    assert test_uuids["document_1"] == "550e8400-e29b-41d4-a716-446655440000"
    uuid_helper.assert_uuid_format(test_uuids["document_1"])


def test_example_api_client_usage(api_helper, sample_pdf_content, sample_document_metadata):
    """Example of using API client helpers in tests."""
    # Note: This is a mock test - in real tests you'd mock the HTTP responses
    
    # Test URL generation
    upload_url = api_helper.get_endpoint_url("/documents")
    assert upload_url == "http://localhost:8000/documents"
    
    # Example of how you would use upload helper (with mocked responses)
    # response = api_helper.upload_document(
    #     file_content=sample_pdf_content,
    #     filename="test_report.pdf",
    #     metadata=sample_document_metadata,
    #     idempotency_key="550e8400-e29b-41d4-a716-446655440000"
    # )


def test_example_openapi_validation(openapi_validator, sample_document_upload_data):
    """Example of using OpenAPI validation in tests."""
    # Validate response data against schema
    openapi_validator.validate_schema_data(
        sample_document_upload_data, 
        "DocumentUploadResponse"
    )
    
    # Validate specific response fields
    required_fields = ["document_id", "job_id", "filename", "file_size", "status", "upload_time"]
    for field in required_fields:
        assert field in sample_document_upload_data


def test_example_response_validation(
    response_validator, 
    sample_search_results,
    uuid_validator,
    response_uuid_validator
):
    """Example of using response validation helpers."""
    # Validate entire response against OpenAPI schema
    response_validator(sample_search_results, "/search", "GET", "200")
    
    # Validate UUIDs in response
    for result in sample_search_results["results"]:
        uuid_validator(result["content_id"], "search result content_id")
        uuid_validator(result["document_id"], "search result document_id")
    
    # Validate UUID fields in bulk
    for result in sample_search_results["results"]:
        response_uuid_validator(result, ["content_id", "document_id"])


def test_example_contract_testing(contract_tester, sample_job_status_data):
    """Example of using contract testing helpers."""
    # Test that job status response matches OpenAPI contract
    contract_tester(sample_job_status_data, "/jobs/{job_id}", "GET", 200)


def test_example_test_data_usage(
    sample_document_uuids,
    sample_search_results,
    sample_question_response,
    multipart_form_data
):
    """Example of using pre-built test data."""
    # Use sample UUIDs in tests
    doc_id = sample_document_uuids["document_1"]
    assert doc_id == "550e8400-e29b-41d4-a716-446655440000"
    
    # Use sample search results
    assert sample_search_results["total_results"] == 3
    assert len(sample_search_results["results"]) == 3
    
    # Use sample Q&A response
    assert sample_question_response["confidence"] > 0.8
    assert len(sample_question_response["citations"]) >= 1
    
    # Use multipart form data for upload tests
    assert "file" in multipart_form_data["files"]
    assert "metadata" in multipart_form_data["data"]


def test_example_auth_headers(auth_headers, multipart_auth_headers, idempotency_headers):
    """Example of using authentication headers."""
    # Standard auth headers
    assert "X-API-Key" in auth_headers
    assert "Content-Type" in auth_headers
    
    # Multipart auth headers (no Content-Type)
    assert "X-API-Key" in multipart_auth_headers
    assert "Content-Type" not in multipart_auth_headers
    
    # Headers with idempotency key
    assert "X-API-Key" in idempotency_headers
    assert "Idempotency-Key" in idempotency_headers


def test_example_error_scenarios(sample_error_response, schema_validator):
    """Example of testing error responses."""
    # Validate error response structure
    schema_validator(sample_error_response, "ErrorResponse")
    
    # Check error details
    error = sample_error_response["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "message" in error
    assert "details" in error


@pytest.mark.asyncio
async def test_example_async_usage(async_api_helper):
    """Example of using async API helpers."""
    # Note: This would be used with mocked responses in real tests
    
    # Example of async health check
    # response = await async_api_helper.check_health()
    # assert response.status_code == 200
    
    # For testing purposes, just verify the helper is available
    assert async_api_helper is not None
    assert hasattr(async_api_helper, "check_health")
    assert hasattr(async_api_helper, "upload_document")


def test_example_specialized_uuids(
    solar_document_uuids,
    wind_document_uuids, 
    processing_job_uuids,
    uuid_validator
):
    """Example of using specialized UUID collections."""
    # Solar energy document UUIDs
    solar_report_id = solar_document_uuids["solar_efficiency_report"]
    uuid_validator(solar_report_id, "solar efficiency report")
    
    # Wind energy document UUIDs  
    wind_report_id = wind_document_uuids["wind_turbine_report"]
    uuid_validator(wind_report_id, "wind turbine report")
    
    # Processing job UUIDs
    ocr_job_id = processing_job_uuids["ocr_job"]
    uuid_validator(ocr_job_id, "OCR job")


def test_example_mock_responses(
    mock_document_response_with_uuids,
    mock_search_results_with_uuids,
    uuid_list_validator
):
    """Example of using mock response data with proper UUIDs."""
    # Mock document response
    doc_response = mock_document_response_with_uuids
    assert doc_response["status"] == "uploaded"
    uuid_list_validator([doc_response["document_id"], doc_response["job_id"]])
    
    # Mock search results
    search_response = mock_search_results_with_uuids
    content_ids = [r["content_id"] for r in search_response["results"]]
    document_ids = [r["document_id"] for r in search_response["results"]]
    
    uuid_list_validator(content_ids, "search result content IDs")
    uuid_list_validator(document_ids, "search result document IDs")