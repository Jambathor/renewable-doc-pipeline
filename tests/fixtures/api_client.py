"""
API client fixtures for renewable energy document processing pipeline tests.

Provides configured HTTP clients, authentication helpers, and request utilities
for testing API endpoints against OpenAPI specifications.
"""

import os
from typing import Dict, Any, Optional
from urllib.parse import urljoin

import httpx
import pytest


@pytest.fixture
def base_url() -> str:
    """Base URL for API testing."""
    # Use environment variable if set, otherwise default for local testing
    return os.getenv("TEST_API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def api_key() -> str:
    """API key for authentication in tests."""
    # Use environment variable if set, otherwise test key
    return os.getenv("TEST_API_KEY", "test-api-key-12345")


@pytest.fixture
def auth_headers(api_key: str) -> Dict[str, str]:
    """Authentication headers for API requests."""
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }


@pytest.fixture
def multipart_auth_headers(api_key: str) -> Dict[str, str]:
    """Authentication headers for multipart requests (without Content-Type)."""
    return {
        "X-API-Key": api_key,
    }


@pytest.fixture
def idempotency_headers(api_key: str) -> Dict[str, str]:
    """Headers with idempotency key for upload requests."""
    return {
        "X-API-Key": api_key,
        "Idempotency-Key": "550e8400-e29b-41d4-a716-446655440000",
    }


@pytest.fixture
def test_api_client(base_url: str) -> httpx.Client:
    """Configured HTTP client for API testing."""
    return httpx.Client(
        base_url=base_url,
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "renewable-pipeline-test-client/1.0.0",
        },
    )


@pytest.fixture
async def async_test_api_client(base_url: str) -> httpx.AsyncClient:
    """Configured async HTTP client for API testing."""
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "renewable-pipeline-test-client/1.0.0",
        },
    ) as client:
        yield client


@pytest.fixture
def authenticated_client(test_api_client: httpx.Client, auth_headers: Dict[str, str]) -> httpx.Client:
    """HTTP client pre-configured with authentication headers."""
    test_api_client.headers.update(auth_headers)
    return test_api_client


@pytest.fixture
async def async_authenticated_client(base_url: str, auth_headers: Dict[str, str]) -> httpx.AsyncClient:
    """Async HTTP client pre-configured with authentication headers."""
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "renewable-pipeline-test-client/1.0.0",
            **auth_headers,
        },
    ) as client:
        yield client


class APITestHelper:
    """Helper class for API testing operations."""
    
    def __init__(self, client: httpx.Client, base_url: str, api_key: str):
        self.client = client
        self.base_url = base_url
        self.api_key = api_key
    
    def get_endpoint_url(self, path: str) -> str:
        """Get full URL for an API endpoint."""
        return urljoin(self.base_url, path.lstrip("/"))
    
    def make_authenticated_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make an authenticated request to the API."""
        request_headers = {"X-API-Key": self.api_key}
        if headers:
            request_headers.update(headers)
        
        return self.client.request(
            method=method,
            url=self.get_endpoint_url(path),
            headers=request_headers,
            **kwargs
        )
    
    def upload_document(
        self,
        file_content: bytes,
        filename: str = "test.pdf",
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> httpx.Response:
        """Upload a document via the API."""
        import json
        
        headers = {"X-API-Key": self.api_key}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        
        files = {
            "file": (filename, file_content, "application/pdf")
        }
        
        data = {}
        if metadata:
            data["metadata"] = json.dumps(metadata)
        
        return self.client.post(
            url=self.get_endpoint_url("/documents"),
            headers=headers,
            files=files,
            data=data,
        )
    
    def get_job_status(self, job_id: str) -> httpx.Response:
        """Get job status via the API."""
        return self.make_authenticated_request(
            "GET",
            f"/jobs/{job_id}"
        )
    
    def search_documents(
        self,
        query: str,
        content_types: Optional[list] = None,
        document_ids: Optional[list] = None,
        **params
    ) -> httpx.Response:
        """Search documents via the API."""
        search_params = {"query": query}
        
        if content_types:
            search_params["content_types"] = ",".join(content_types)
        
        if document_ids:
            search_params["document_ids"] = ",".join(document_ids)
        
        search_params.update(params)
        
        return self.make_authenticated_request(
            "GET",
            "/search",
            params=search_params,
        )
    
    def ask_question(
        self,
        question: str,
        context_filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """Ask a question via the Q&A API."""
        payload = {"question": question}
        
        if context_filters:
            payload["context_filters"] = context_filters
        
        payload.update(kwargs)
        
        return self.make_authenticated_request(
            "POST",
            "/qa",
            json=payload,
        )
    
    def get_document(self, document_id: str) -> httpx.Response:
        """Get document metadata via the API."""
        return self.make_authenticated_request(
            "GET",
            f"/documents/{document_id}"
        )
    
    def delete_document(self, document_id: str) -> httpx.Response:
        """Delete a document via the API."""
        return self.make_authenticated_request(
            "DELETE",
            f"/documents/{document_id}"
        )
    
    def check_health(self) -> httpx.Response:
        """Check API health status (no authentication required)."""
        return self.client.get(self.get_endpoint_url("/healthz"))
    
    def get_metrics(self) -> httpx.Response:
        """Get metrics endpoint (requires authentication)."""
        return self.make_authenticated_request("GET", "/metrics")


@pytest.fixture
def api_helper(test_api_client: httpx.Client, base_url: str, api_key: str) -> APITestHelper:
    """API test helper with pre-configured client."""
    return APITestHelper(test_api_client, base_url, api_key)


class AsyncAPITestHelper:
    """Async helper class for API testing operations."""
    
    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str):
        self.client = client
        self.base_url = base_url
        self.api_key = api_key
    
    def get_endpoint_url(self, path: str) -> str:
        """Get full URL for an API endpoint."""
        return urljoin(self.base_url, path.lstrip("/"))
    
    async def make_authenticated_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """Make an authenticated request to the API."""
        request_headers = {"X-API-Key": self.api_key}
        if headers:
            request_headers.update(headers)
        
        return await self.client.request(
            method=method,
            url=self.get_endpoint_url(path),
            headers=request_headers,
            **kwargs
        )
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str = "test.pdf",
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> httpx.Response:
        """Upload a document via the API."""
        import json
        
        headers = {"X-API-Key": self.api_key}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        
        files = {
            "file": (filename, file_content, "application/pdf")
        }
        
        data = {}
        if metadata:
            data["metadata"] = json.dumps(metadata)
        
        return await self.client.post(
            url=self.get_endpoint_url("/documents"),
            headers=headers,
            files=files,
            data=data,
        )
    
    async def search_documents(
        self,
        query: str,
        content_types: Optional[list] = None,
        document_ids: Optional[list] = None,
        **params
    ) -> httpx.Response:
        """Search documents via the API."""
        search_params = {"query": query}
        
        if content_types:
            search_params["content_types"] = ",".join(content_types)
        
        if document_ids:
            search_params["document_ids"] = ",".join(document_ids)
        
        search_params.update(params)
        
        return await self.make_authenticated_request(
            "GET",
            "/search",
            params=search_params,
        )
    
    async def check_health(self) -> httpx.Response:
        """Check API health status (no authentication required)."""
        return await self.client.get(self.get_endpoint_url("/healthz"))


@pytest.fixture
async def async_api_helper(base_url: str, api_key: str):
    """Async API test helper with pre-configured client."""
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "renewable-pipeline-test-client/1.0.0",
        },
    ) as client:
        yield AsyncAPITestHelper(client, base_url, api_key)


@pytest.fixture
def no_auth_client(test_api_client: httpx.Client) -> httpx.Client:
    """HTTP client without authentication for testing unauthorized access."""
    return test_api_client


@pytest.fixture
def invalid_auth_client(test_api_client: httpx.Client) -> httpx.Client:
    """HTTP client with invalid authentication for testing auth failures."""
    test_api_client.headers.update({
        "X-API-Key": "invalid-key-12345",
    })
    return test_api_client


@pytest.fixture
def rate_limit_headers() -> Dict[str, str]:
    """Headers for testing rate limiting scenarios."""
    return {
        "X-Rate-Limit-Burst": "true",  # Custom header to trigger rate limiting in tests
    }


# Response validation helpers

def assert_response_structure(response: httpx.Response, expected_fields: list[str]) -> None:
    """Assert that response JSON contains expected fields."""
    assert response.headers.get("content-type", "").startswith("application/json")
    response_data = response.json()
    
    for field in expected_fields:
        assert field in response_data, f"Missing field '{field}' in response"


def assert_error_response(response: httpx.Response, expected_code: str) -> None:
    """Assert that response is a valid error response with expected code."""
    assert response.headers.get("content-type", "").startswith("application/json")
    response_data = response.json()
    
    assert "error" in response_data
    assert "code" in response_data["error"]
    assert "message" in response_data["error"]
    assert response_data["error"]["code"] == expected_code


def assert_uuid_format(uuid_string: str) -> None:
    """Assert that string is a valid UUID format."""
    import uuid as uuid_module
    try:
        uuid_module.UUID(uuid_string)
    except ValueError:
        pytest.fail(f"Invalid UUID format: {uuid_string}")


def assert_datetime_format(datetime_string: str) -> None:
    """Assert that string is a valid ISO datetime format."""
    from datetime import datetime
    try:
        datetime.fromisoformat(datetime_string.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Invalid datetime format: {datetime_string}")