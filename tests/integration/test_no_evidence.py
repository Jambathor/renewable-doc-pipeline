"""
T077 - No Evidence Integration Tests

Tests for Q&A endpoints when no evidence is found for questions.
These tests verify proper handling of no-match scenarios and response structure.

Expected to FAIL until /qa endpoint is implemented (TDD approach).
"""

import httpx
import pytest

from tests.fixtures.api_client import (
    APITestHelper,
    assert_response_structure,
    assert_uuid_format,
)


@pytest.mark.integration
class TestNoEvidence:
    """Integration tests for no evidence scenarios in Q&A."""

    def test_qa_returns_no_evidence_found_response(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: dict
    ):
        """Test /qa returns proper 'No evidence found' response when no docs match."""
        # This test MUST fail since /qa endpoint doesn't exist yet
        response = api_helper.ask_question(
            question="What is the nuclear power efficiency in underwater installations?",
            max_citations=5
        )

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")

        response_data = response.json()

        # Verify no evidence response structure
        assert response_data["question"] == "What is the nuclear power efficiency in underwater installations?"
        assert response_data["answer"] == "No evidence found"
        assert response_data["confidence"] == 0.0
        assert response_data["citations"] == []
        assert isinstance(response_data["refinement_hints"], list)
        assert len(response_data["refinement_hints"]) > 0
        assert isinstance(response_data["processing_time_ms"], int)
        assert response_data["processing_time_ms"] > 0

    def test_qa_no_evidence_confidence_is_zero(
        self,
        api_helper: APITestHelper
    ):
        """Test confidence score is exactly 0.0 for no evidence responses."""
        # This test MUST fail since /qa endpoint doesn't exist yet
        response = api_helper.ask_question(
            question="How efficient are dragon-powered renewable energy systems?",
            max_citations=3
        )

        assert response.status_code == 200
        response_data = response.json()

        # No evidence scenarios must have 0.0 confidence
        assert response_data["confidence"] == 0.0
        assert response_data["answer"] == "No evidence found"

    def test_qa_no_evidence_empty_citations_array(
        self,
        api_helper: APITestHelper
    ):
        """Test citations array is empty for no evidence responses."""
        # This test MUST fail since /qa endpoint doesn't exist yet
        response = api_helper.ask_question(
            question="What are the efficiency metrics for perpetual motion machines?",
            context_filters={
                "content_types": ["text", "table", "chart"]
            },
            max_citations=10
        )

        assert response.status_code == 200
        response_data = response.json()

        # No evidence must return empty citations
        assert response_data["citations"] == []
        assert isinstance(response_data["citations"], list)
        assert len(response_data["citations"]) == 0

    def test_qa_no_evidence_provides_refinement_hints(
        self,
        api_helper: APITestHelper
    ):
        """Test refinement_hints are provided for no evidence responses."""
        # This test MUST fail since /qa endpoint doesn't exist yet
        response = api_helper.ask_question(
            question="What is the energy output of solar panels on Mars?",
            include_thumbnails=True
        )

        assert response.status_code == 200
        response_data = response.json()

        # Verify refinement hints structure per quickstart.md
        assert "refinement_hints" in response_data
        hints = response_data["refinement_hints"]
        assert isinstance(hints, list)
        assert len(hints) > 0

        # Expected hints from quickstart.md example
        expected_hint_keywords = ["renewable energy", "solar", "wind", "broadening", "documents"]
        hint_text = " ".join(hints).lower()
        has_relevant_hint = any(keyword in hint_text for keyword in expected_hint_keywords)
        assert has_relevant_hint, f"No relevant hints found in: {hints}"

    def test_qa_no_evidence_still_tracks_processing_time(
        self,
        api_helper: APITestHelper
    ):
        """Test processing_time_ms is still tracked for no evidence responses."""
        # This test MUST fail since /qa endpoint doesn't exist yet
        response = api_helper.ask_question(
            question="How do unicorns contribute to renewable energy generation?",
            max_citations=1
        )

        assert response.status_code == 200
        response_data = response.json()

        # Processing time should still be tracked
        assert "processing_time_ms" in response_data
        processing_time = response_data["processing_time_ms"]
        assert isinstance(processing_time, int)
        assert processing_time > 0  # Should be positive even for no evidence
        assert processing_time < 10000  # Should be reasonable (< 10 seconds)

    def test_qa_no_evidence_with_document_filters(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: dict
    ):
        """Test no evidence response when using document filters."""
        # This test MUST fail since /qa endpoint doesn't exist yet
        response = api_helper.ask_question(
            question="What is the thermal efficiency of ice-based solar panels?",
            context_filters={
                "document_ids": [sample_document_uuids["document_1"]],
                "content_types": ["text", "table"]
            },
            max_citations=5
        )

        assert response.status_code == 200
        response_data = response.json()

        # Should still return no evidence structure even with filters
        assert response_data["answer"] == "No evidence found"
        assert response_data["confidence"] == 0.0
        assert response_data["citations"] == []
        assert len(response_data["refinement_hints"]) > 0

    def test_qa_no_evidence_question_echo(
        self,
        api_helper: APITestHelper
    ):
        """Test question is echoed back correctly in no evidence responses."""
        # This test MUST fail since /qa endpoint doesn't exist yet
        original_question = "What is the efficiency of rainbow-powered energy systems?"

        response = api_helper.ask_question(
            question=original_question,
            max_citations=3
        )

        assert response.status_code == 200
        response_data = response.json()

        # Question should be echoed back exactly
        assert response_data["question"] == original_question
        assert response_data["answer"] == "No evidence found"

    def test_qa_no_evidence_response_schema_compliance(
        self,
        api_helper: APITestHelper
    ):
        """Test no evidence response matches OpenAPI schema structure."""
        # This test MUST fail since /qa endpoint doesn't exist yet
        response = api_helper.ask_question(
            question="How efficient are quantum crystal energy harvesting systems?",
            include_thumbnails=False,
            max_citations=2
        )

        assert response.status_code == 200

        # Verify all required fields per OpenAPI schema
        expected_fields = [
            "question", "answer", "confidence",
            "citations", "refinement_hints", "processing_time_ms"
        ]
        assert_response_structure(response, expected_fields)

        response_data = response.json()

        # Verify field types
        assert isinstance(response_data["question"], str)
        assert isinstance(response_data["answer"], str)
        assert isinstance(response_data["confidence"], (int, float))
        assert isinstance(response_data["citations"], list)
        assert isinstance(response_data["refinement_hints"], list)
        assert isinstance(response_data["processing_time_ms"], int)

        # Verify no evidence specific values
        assert response_data["answer"] == "No evidence found"
        assert response_data["confidence"] == 0.0
        assert len(response_data["citations"]) == 0
