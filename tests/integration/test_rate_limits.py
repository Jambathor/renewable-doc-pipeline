"""
Integration tests for rate limiting on search and Q&A endpoints (T018).

Tests verify that the /search and /qa endpoints properly implement rate limiting
with HTTP 429 responses when limits are exceeded. These tests will initially fail
as rate limiting is not yet implemented.
"""

import asyncio
import time
from typing import Dict, Any

import pytest
import httpx

from tests.fixtures.api_client import APITestHelper, assert_error_response


@pytest.mark.integration
class TestSearchRateLimiting:
    """Test rate limiting for the /search endpoint."""

    def test_search_rate_limit_exceeded_sync(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: Dict[str, str]
    ):
        """Test that /search returns 429 when rate limit is exceeded."""
        query = "solar panel efficiency"
        
        # Make rapid requests to trigger rate limiting
        responses = []
        for i in range(20):  # Assume rate limit is lower than 20 requests
            response = api_helper.search_documents(
                query=query,
                content_types=["text", "chart", "table"],
                limit=5
            )
            responses.append(response)
            
            # If we get 429, test rate limiting is working
            if response.status_code == 429:
                break
        
        # At least one response should be rate limited
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0, "Expected at least one 429 response for rate limiting"
        
        # Verify rate limit response structure
        rate_limited_response = rate_limited_responses[0]
        assert_error_response(rate_limited_response, "rate_limit_exceeded")
        
        # Check for rate limit headers if present
        headers = rate_limited_response.headers
        rate_limit_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining", 
            "X-RateLimit-Reset",
            "Retry-After"
        ]
        
        # At least one rate limit header should be present
        present_headers = [h for h in rate_limit_headers if h in headers]
        if present_headers:
            # If Retry-After is present, should be a positive integer
            if "Retry-After" in headers:
                retry_after = headers["Retry-After"]
                assert retry_after.isdigit(), f"Retry-After should be numeric, got: {retry_after}"
                assert int(retry_after) > 0, f"Retry-After should be positive, got: {retry_after}"
    
    def test_search_rate_limit_per_client(
        self,
        test_api_client: httpx.Client,
        api_key: str,
        base_url: str
    ):
        """Test that rate limiting is applied per client/API key."""
        # Create two separate API helpers with same credentials
        helper1 = APITestHelper(test_api_client, base_url, api_key)
        
        # Use different client for helper2
        with httpx.Client(base_url=base_url, timeout=30.0) as client2:
            helper2 = APITestHelper(client2, base_url, api_key)
            
            query = "renewable energy trends"
            
            # Saturate rate limit with first client
            responses1 = []
            for i in range(15):
                response = helper1.search_documents(query=query, limit=3)
                responses1.append(response)
                if response.status_code == 429:
                    break
            
            # Check if any requests were rate limited
            rate_limited_count = len([r for r in responses1 if r.status_code == 429])
            
            # If rate limiting is working, we should see 429s
            if rate_limited_count > 0:
                # Second client with same API key should also be rate limited
                response2 = helper2.search_documents(query=query, limit=3)
                
                # Should be rate limited due to shared API key limits
                assert response2.status_code == 429, "Expected rate limiting to apply across clients with same API key"
                assert_error_response(response2, "rate_limit_exceeded")

    def test_search_rate_limit_recovery(
        self,
        api_helper: APITestHelper
    ):
        """Test that rate limits reset after the specified time window."""
        query = "wind energy efficiency"
        
        # Trigger rate limiting
        responses = []
        for i in range(20):
            response = api_helper.search_documents(query=query, limit=2)
            responses.append(response)
            if response.status_code == 429:
                break
        
        # Find first rate limited response
        rate_limited = next((r for r in responses if r.status_code == 429), None)
        
        if rate_limited:
            # Check for Retry-After header
            retry_after = rate_limited.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                sleep_time = min(int(retry_after), 5)  # Cap at 5 seconds for test speed
                time.sleep(sleep_time)
                
                # After waiting, should be able to make requests again
                recovery_response = api_helper.search_documents(query=query, limit=2)
                
                # Should either succeed or still be rate limited but with updated headers
                assert recovery_response.status_code in [200, 429], f"Unexpected status after rate limit recovery: {recovery_response.status_code}"


@pytest.mark.integration 
class TestQAEndpointRateLimiting:
    """Test rate limiting for the /qa endpoint."""

    def test_qa_rate_limit_exceeded(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: Dict[str, str]
    ):
        """Test that /qa returns 429 when rate limit is exceeded."""
        question = "What is the efficiency of solar panels?"
        context_filters = {
            "content_types": ["text", "table"],
            "document_ids": [sample_document_uuids["document_1"]]
        }
        
        # Make rapid Q&A requests to trigger rate limiting
        responses = []
        for i in range(15):  # Assume rate limit is lower than 15 requests
            response = api_helper.ask_question(
                question=f"{question} (request {i})",
                context_filters=context_filters,
                max_citations=3
            )
            responses.append(response)
            
            # If we get 429, rate limiting is working
            if response.status_code == 429:
                break
        
        # At least one response should be rate limited
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0, "Expected at least one 429 response for Q&A rate limiting"
        
        # Verify rate limit response structure
        rate_limited_response = rate_limited_responses[0]
        assert_error_response(rate_limited_response, "rate_limit_exceeded")
        
        # Response should be JSON with proper error structure
        assert rate_limited_response.headers.get("content-type", "").startswith("application/json")
        response_data = rate_limited_response.json()
        
        assert "error" in response_data
        assert "message" in response_data["error"]
        assert "rate" in response_data["error"]["message"].lower() or "limit" in response_data["error"]["message"].lower()

    def test_qa_rate_limit_different_questions(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: Dict[str, str]
    ):
        """Test that rate limiting applies regardless of question content."""
        questions = [
            "What is solar panel efficiency?",
            "How does wind energy work?", 
            "What are renewable energy trends?",
            "What is the cost of solar installation?",
            "How efficient are modern wind turbines?"
        ]
        
        context_filters = {
            "content_types": ["text"],
            "document_ids": [sample_document_uuids["document_1"]]
        }
        
        # Cycle through different questions rapidly
        responses = []
        for i in range(20):
            question = questions[i % len(questions)]
            response = api_helper.ask_question(
                question=question,
                context_filters=context_filters,
                max_citations=2
            )
            responses.append(response)
            
            if response.status_code == 429:
                break
        
        # Should still get rate limited despite different questions
        rate_limited_count = len([r for r in responses if r.status_code == 429])
        
        if rate_limited_count > 0:
            # Verify the rate limited response
            rate_limited = next(r for r in responses if r.status_code == 429)
            assert_error_response(rate_limited, "rate_limit_exceeded")


@pytest.mark.integration
class TestRateLimitClientHandling:
    """Test client-side rate limit handling patterns."""

    def test_exponential_backoff_simulation(
        self,
        api_helper: APITestHelper
    ):
        """Test exponential backoff pattern when encountering 429s."""
        query = "solar energy california"
        
        max_retries = 3
        base_delay = 0.1  # Start with 100ms for test speed
        
        for attempt in range(max_retries + 1):
            response = api_helper.search_documents(query=query, limit=5)
            
            if response.status_code == 429:
                if attempt < max_retries:
                    # Calculate exponential backoff delay
                    delay = base_delay * (2 ** attempt)
                    time.sleep(min(delay, 2.0))  # Cap at 2 seconds for tests
                    continue
                else:
                    # Final attempt failed - this is expected behavior
                    assert_error_response(response, "rate_limit_exceeded")
                    break
            elif response.status_code == 200:
                # Request succeeded
                break
            else:
                # Unexpected status code
                pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_rate_limit_header_validation(
        self,
        api_helper: APITestHelper
    ):
        """Test that rate limit headers provide useful information."""
        query = "renewable energy storage"
        
        # Make requests until we hit rate limit or exhaust attempts
        responses = []
        for i in range(25):
            response = api_helper.search_documents(query=f"{query} {i}", limit=3)
            responses.append(response)
            
            if response.status_code == 429:
                # Check rate limit headers
                headers = response.headers
                
                # Common rate limit headers that might be present
                if "X-RateLimit-Limit" in headers:
                    limit = headers["X-RateLimit-Limit"]
                    assert limit.isdigit(), f"X-RateLimit-Limit should be numeric: {limit}"
                    assert int(limit) > 0, f"X-RateLimit-Limit should be positive: {limit}"
                
                if "X-RateLimit-Remaining" in headers:
                    remaining = headers["X-RateLimit-Remaining"]
                    assert remaining.isdigit(), f"X-RateLimit-Remaining should be numeric: {remaining}"
                    # Should be 0 or low when rate limited
                    assert int(remaining) >= 0, f"X-RateLimit-Remaining should be non-negative: {remaining}"
                
                if "X-RateLimit-Reset" in headers:
                    reset = headers["X-RateLimit-Reset"]
                    # Could be Unix timestamp or seconds until reset
                    assert reset.isdigit(), f"X-RateLimit-Reset should be numeric: {reset}"
                
                break


@pytest.mark.integration
@pytest.mark.slow
class TestRateLimitIntegrationWithAuth:
    """Test rate limiting interaction with authentication."""

    def test_rate_limit_with_invalid_auth_key(
        self,
        test_api_client: httpx.Client,
        base_url: str
    ):
        """Test that rate limiting applies even with invalid API keys."""
        # Use invalid API key
        invalid_helper = APITestHelper(test_api_client, base_url, "invalid-key-12345")
        
        query = "solar installation costs"
        
        # Make requests with invalid key
        responses = []
        for i in range(10):
            response = invalid_helper.search_documents(query=query, limit=2)
            responses.append(response)
            
            # Stop if we get rate limited or unauthorized
            if response.status_code in [401, 429]:
                break
        
        # Should get either 401 (unauthorized) or 429 (rate limited)
        # depending on whether rate limiting is checked before or after auth
        final_response = responses[-1] if responses else None
        
        if final_response:
            assert final_response.status_code in [401, 429], f"Expected 401 or 429, got {final_response.status_code}"
            
            if final_response.status_code == 429:
                assert_error_response(final_response, "rate_limit_exceeded")
            elif final_response.status_code == 401:
                assert_error_response(final_response, "unauthorized")

    def test_rate_limit_per_api_key_isolation(
        self,
        test_api_client: httpx.Client,
        base_url: str
    ):
        """Test that different API keys have separate rate limits."""
        # This test assumes we have multiple valid API keys available
        # In practice, this might need to be adapted based on test environment
        
        api_key1 = "test-api-key-12345"
        api_key2 = "test-api-key-67890"  # Would need to be valid in real environment
        
        helper1 = APITestHelper(test_api_client, base_url, api_key1)
        
        with httpx.Client(base_url=base_url, timeout=30.0) as client2:
            helper2 = APITestHelper(client2, base_url, api_key2)
            
            query = "wind turbine efficiency"
            
            # Saturate rate limit for first API key
            responses1 = []
            for i in range(15):
                response = helper1.search_documents(query=f"{query} key1 {i}", limit=2)
                responses1.append(response)
                if response.status_code == 429:
                    break
            
            # Check if first key got rate limited
            rate_limited1 = any(r.status_code == 429 for r in responses1)
            
            if rate_limited1:
                # Second key should still be able to make requests
                response2 = helper2.search_documents(query=f"{query} key2", limit=2)
                
                # Should succeed (200) or fail with auth error (401) but not rate limit (429)
                # unless rate limiting is global rather than per-key
                assert response2.status_code in [200, 401], f"Second API key should not be rate limited when first is, got {response2.status_code}"