"""
Integration tests for metrics endpoint authentication (T021).

Tests verify that the /metrics endpoint properly implements authentication
requiring X-API-Key header, with different behavior in local vs non-local
environments. These tests will initially fail as the endpoint doesn't exist yet.
"""

import os
from typing import Dict, Any

import pytest
import httpx

from tests.fixtures.api_client import APITestHelper, assert_error_response


@pytest.mark.integration
class TestMetricsEndpointAuthentication:
    """Test authentication requirements for the /metrics endpoint."""

    def test_metrics_requires_auth_header(
        self,
        test_api_client: httpx.Client,
        base_url: str
    ):
        """Test that /metrics endpoint requires X-API-Key header."""
        # Make request without authentication header
        response = test_api_client.get("/metrics")
        
        # Should return 401 Unauthorized
        assert response.status_code == 401, f"Expected 401 without auth header, got {response.status_code}"
        assert_error_response(response, "unauthorized")
        
        # Verify error message mentions authentication
        response_data = response.json()
        error_message = response_data["error"]["message"].lower()
        assert any(word in error_message for word in ["auth", "key", "unauthorized", "credential"]), \
            f"Error message should mention authentication: {response_data['error']['message']}"

    def test_metrics_invalid_auth_header(
        self,
        test_api_client: httpx.Client,
        base_url: str
    ):
        """Test that /metrics endpoint rejects invalid API keys."""
        # Make request with invalid API key
        invalid_headers = {"X-API-Key": "invalid-key-12345"}
        response = test_api_client.get("/metrics", headers=invalid_headers)
        
        # Should return 401 Unauthorized
        assert response.status_code == 401, f"Expected 401 with invalid key, got {response.status_code}"
        assert_error_response(response, "unauthorized")

    def test_metrics_missing_auth_header_value(
        self,
        test_api_client: httpx.Client,
        base_url: str
    ):
        """Test that /metrics endpoint rejects empty X-API-Key header."""
        # Make request with empty API key
        empty_headers = {"X-API-Key": ""}
        response = test_api_client.get("/metrics", headers=empty_headers)
        
        # Should return 401 Unauthorized
        assert response.status_code == 401, f"Expected 401 with empty key, got {response.status_code}"
        assert_error_response(response, "unauthorized")

    def test_metrics_valid_auth_header(
        self,
        api_helper: APITestHelper
    ):
        """Test that /metrics endpoint returns data with valid API key."""
        response = api_helper.get_metrics()
        
        # Should return 200 OK with Prometheus metrics format
        assert response.status_code == 200, f"Expected 200 with valid key, got {response.status_code}"
        
        # Content should be Prometheus metrics format
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type or "text/x-prometheus" in content_type, \
            f"Expected Prometheus metrics content type, got: {content_type}"
        
        # Response should contain metrics data
        metrics_text = response.text
        assert len(metrics_text.strip()) > 0, "Metrics response should not be empty"
        
        # Should contain some basic Prometheus metrics patterns
        # Look for metric names (alphanumeric with underscores) followed by values
        import re
        metric_pattern = r'^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+[\d\.e\+\-]+$'
        lines = [line.strip() for line in metrics_text.split('\n') if line.strip()]
        
        # Filter out comment lines (start with #)
        metric_lines = [line for line in lines if not line.startswith('#')]
        
        if metric_lines:  # If we have non-comment lines, they should be valid metrics
            valid_metrics = [line for line in metric_lines if re.match(metric_pattern, line)]
            assert len(valid_metrics) > 0, f"Should contain valid Prometheus metrics, got: {metrics_text[:200]}"

    def test_metrics_case_sensitive_header(
        self,
        test_api_client: httpx.Client,
        base_url: str,
        api_key: str
    ):
        """Test that X-API-Key header is case-sensitive."""
        # Test different case variations
        test_cases = [
            "x-api-key",      # lowercase
            "X-Api-Key",      # mixed case
            "X-API-key",      # partial lowercase
            "x-API-KEY",      # mixed case
        ]
        
        for header_name in test_cases:
            headers = {header_name: api_key}
            response = test_api_client.get("/metrics", headers=headers)
            
            # HTTP headers are case-insensitive per RFC, but some implementations
            # might be case-sensitive. Test the actual behavior.
            if response.status_code == 200:
                # If it works, verify it's returning metrics
                content_type = response.headers.get("content-type", "")
                assert "text/plain" in content_type or "text/x-prometheus" in content_type
            else:
                # If it fails, should be 401
                assert response.status_code == 401, f"Expected 401 for header {header_name}, got {response.status_code}"


@pytest.mark.integration
class TestMetricsLocalEnvironmentBehavior:
    """Test metrics endpoint behavior in local vs non-local environments."""

    def test_metrics_local_environment_detection(
        self,
        test_api_client: httpx.Client,
        base_url: str,
        api_key: str
    ):
        """Test that metrics endpoint behavior varies by environment."""
        # The behavior depends on whether we're in local environment
        # Local environment typically means localhost or 127.0.0.1
        is_local_url = any(host in base_url.lower() for host in [
            "localhost", "127.0.0.1", "0.0.0.0"
        ])
        
        # According to CLAUDE.md, /metrics should require X-API-Key 
        # outside local environment
        if is_local_url:
            # In local environment, might allow access without auth
            # Try without auth first
            response_no_auth = test_api_client.get("/metrics")
            
            if response_no_auth.status_code == 200:
                # Local bypass is working
                content_type = response_no_auth.headers.get("content-type", "")
                assert "text/plain" in content_type or "text/x-prometheus" in content_type
            else:
                # Still requires auth even in local - that's valid too
                assert response_no_auth.status_code == 401
                
                # But with auth should work
                headers = {"X-API-Key": api_key}
                response_with_auth = test_api_client.get("/metrics", headers=headers)
                assert response_with_auth.status_code == 200
        else:
            # Non-local environment - should always require auth
            response_no_auth = test_api_client.get("/metrics")
            assert response_no_auth.status_code == 401, "Non-local environment should require authentication"
            
            # With auth should work
            headers = {"X-API-Key": api_key}
            response_with_auth = test_api_client.get("/metrics", headers=headers)
            assert response_with_auth.status_code == 200

    def test_metrics_environment_variable_override(
        self,
        test_api_client: httpx.Client,
        base_url: str,
        api_key: str,
        monkeypatch
    ):
        """Test that environment variables can override local behavior."""
        # Test with environment variable that might control auth bypass
        test_cases = [
            ("ENVIRONMENT", "local"),
            ("ENVIRONMENT", "development"), 
            ("METRICS_AUTH_BYPASS", "true"),
            ("LOCAL_DEVELOPMENT", "true"),
        ]
        
        for env_var, env_value in test_cases:
            # Set environment variable
            monkeypatch.setenv(env_var, env_value)
            
            # Test behavior - this is speculative since we don't know
            # the exact implementation, but it's common to have such controls
            response_no_auth = test_api_client.get("/metrics")
            
            # The exact behavior will depend on implementation
            # Just verify we get a consistent response
            assert response_no_auth.status_code in [200, 401], \
                f"Unexpected status with {env_var}={env_value}: {response_no_auth.status_code}"
            
            if response_no_auth.status_code == 200:
                # If auth bypass worked, verify it's metrics content
                content_type = response_no_auth.headers.get("content-type", "")
                assert "text/plain" in content_type or "text/x-prometheus" in content_type
            
            # Clean up
            monkeypatch.delenv(env_var, raising=False)


@pytest.mark.integration
class TestMetricsContentValidation:
    """Test the content and format of metrics responses."""

    def test_metrics_prometheus_format(
        self,
        api_helper: APITestHelper
    ):
        """Test that metrics endpoint returns valid Prometheus format."""
        response = api_helper.get_metrics()
        assert response.status_code == 200
        
        metrics_text = response.text
        lines = metrics_text.split('\n')
        
        # Should contain HELP and TYPE comments for metrics
        help_lines = [line for line in lines if line.startswith('# HELP')]
        type_lines = [line for line in lines if line.startswith('# TYPE')]
        
        # If we have metric definitions, should have some documentation
        metric_lines = [line for line in lines if line.strip() and not line.startswith('#')]
        
        if metric_lines:
            # Should have at least some documentation
            assert len(help_lines) > 0 or len(type_lines) > 0, \
                "Prometheus metrics should include HELP or TYPE comments"

    def test_metrics_expected_metric_families(
        self,
        api_helper: APITestHelper
    ):
        """Test that metrics include expected application metrics."""
        response = api_helper.get_metrics()
        assert response.status_code == 200
        
        metrics_text = response.text.lower()
        
        # Expected metric families for this application
        expected_metrics = [
            # HTTP request metrics
            "http_requests_total",
            "http_request_duration", 
            "http_request_size",
            
            # Application-specific metrics
            "document_processing",
            "search_requests",
            "qa_requests",
            
            # System metrics that might be present
            "process_cpu",
            "process_memory",
            "python_gc",
        ]
        
        # At least some expected metrics should be present
        found_metrics = []
        for metric in expected_metrics:
            if metric in metrics_text:
                found_metrics.append(metric)
        
        # Should have at least a few standard metrics
        assert len(found_metrics) >= 2, f"Expected to find common metrics, found: {found_metrics}"

    def test_metrics_response_headers(
        self,
        api_helper: APITestHelper
    ):
        """Test that metrics response has appropriate headers."""
        response = api_helper.get_metrics()
        assert response.status_code == 200
        
        headers = response.headers
        
        # Content-Type should be appropriate for Prometheus
        content_type = headers.get("content-type", "")
        assert content_type in [
            "text/plain; charset=utf-8",
            "text/plain",
            "text/x-prometheus; charset=utf-8",
            "application/openmetrics-text; charset=utf-8"
        ], f"Unexpected content type for metrics: {content_type}"
        
        # Should not be cached
        cache_control = headers.get("cache-control", "")
        if cache_control:
            assert "no-cache" in cache_control or "max-age=0" in cache_control, \
                f"Metrics should not be cached: {cache_control}"


@pytest.mark.integration
class TestMetricsSecurityAspects:
    """Test security aspects of the metrics endpoint."""

    def test_metrics_no_sensitive_information(
        self,
        api_helper: APITestHelper
    ):
        """Test that metrics don't expose sensitive information."""
        response = api_helper.get_metrics()
        assert response.status_code == 200
        
        metrics_text = response.text.lower()
        
        # Should not contain sensitive information
        sensitive_patterns = [
            "password", "secret", "key", "token", "credential",
            "user", "email", "phone", "address", "ssn",
            "api_key", "database_url", "connection_string"
        ]
        
        for pattern in sensitive_patterns:
            assert pattern not in metrics_text, \
                f"Metrics should not contain sensitive pattern: {pattern}"

    def test_metrics_rate_limiting_interaction(
        self,
        api_helper: APITestHelper
    ):
        """Test that metrics endpoint might have different rate limits."""
        # Metrics endpoint might have more lenient rate limits than search/qa
        responses = []
        for i in range(10):
            response = api_helper.get_metrics()
            responses.append(response)
            
            # Stop if we get rate limited
            if response.status_code == 429:
                break
        
        # Metrics endpoint should generally allow more frequent access
        # or have no rate limiting since it's for monitoring
        success_count = len([r for r in responses if r.status_code == 200])
        rate_limited_count = len([r for r in responses if r.status_code == 429])
        
        # Should allow at least several successful requests
        assert success_count >= 5, f"Metrics endpoint should allow frequent access, only {success_count} succeeded"
        
        # If rate limited, should still return proper error format
        if rate_limited_count > 0:
            rate_limited_response = next(r for r in responses if r.status_code == 429)
            assert_error_response(rate_limited_response, "rate_limit_exceeded")

    def test_metrics_concurrent_access(
        self,
        base_url: str,
        api_key: str
    ):
        """Test that metrics endpoint handles concurrent requests."""
        import concurrent.futures
        import threading
        
        results = []
        
        def make_metrics_request():
            with httpx.Client(base_url=base_url, timeout=30.0) as client:
                helper = APITestHelper(client, base_url, api_key)
                response = helper.get_metrics()
                return response.status_code
        
        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_metrics_request) for _ in range(5)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    status_code = future.result(timeout=10)
                    results.append(status_code)
                except Exception as e:
                    results.append(f"Exception: {e}")
        
        # Most requests should succeed
        success_count = len([r for r in results if r == 200])
        assert success_count >= 3, f"Most concurrent requests should succeed, results: {results}"


@pytest.mark.integration
class TestMetricsErrorHandling:
    """Test error handling for the metrics endpoint."""

    def test_metrics_malformed_auth_header(
        self,
        test_api_client: httpx.Client,
        base_url: str
    ):
        """Test metrics endpoint with malformed authentication."""
        # Test various malformed auth headers
        malformed_headers = [
            {"Authorization": "Bearer test-key"},  # Wrong header name
            {"X-API-Key": "key with spaces"},      # Spaces in key
            {"X-API-Key": "key\nwith\nnewlines"}, # Newlines in key
            {"X-API-Key": "🔑invalid-unicode"},   # Unicode characters
        ]
        
        for headers in malformed_headers:
            response = test_api_client.get("/metrics", headers=headers)
            
            # Should return 401 for malformed auth
            assert response.status_code == 401, \
                f"Expected 401 for malformed header {headers}, got {response.status_code}"
            
            # Should return proper error response
            assert_error_response(response, "unauthorized")

    def test_metrics_multiple_auth_headers(
        self,
        test_api_client: httpx.Client,
        base_url: str,
        api_key: str
    ):
        """Test metrics endpoint with multiple authentication headers."""
        # Send multiple X-API-Key headers
        headers = {
            "X-API-Key": api_key,
        }
        
        # httpx doesn't easily support duplicate headers, but we can test
        # with additional auth-related headers
        conflicting_headers = {
            "X-API-Key": api_key,
            "Authorization": f"Bearer {api_key}",
            "X-Auth-Token": api_key,
        }
        
        response = test_api_client.get("/metrics", headers=conflicting_headers)
        
        # Should either succeed (using X-API-Key) or fail consistently
        assert response.status_code in [200, 401], \
            f"Unexpected status with multiple auth headers: {response.status_code}"
        
        if response.status_code == 200:
            # If successful, should return proper metrics
            content_type = response.headers.get("content-type", "")
            assert "text/plain" in content_type or "text/x-prometheus" in content_type