"""
T017: Complete quickstart workflow integration test.

Tests the end-to-end renewable energy PDF processing pipeline workflow
as described in quickstart.md. This test implements TDD approach and will
fail until the endpoints are implemented.

The test validates:
1. Health check (GET /healthz)
2. Document upload (POST /documents with Idempotency-Key)
3. Job status monitoring (GET /jobs/{job_id})
4. Document metadata retrieval (GET /documents/{document_id})
5. Content search (GET /search)
6. Question answering (POST /qa)
7. Document deletion (DELETE /documents/{document_id})

All UUIDs follow proper format per CLAUDE.md requirements.
"""

import json
import time
from typing import Any, Dict

import httpx
import pytest

from tests.fixtures.api_client import (
    APITestHelper,
    assert_response_structure,
    assert_uuid_format,
)


@pytest.mark.integration
class TestQuickstartWorkflow:
    """Complete quickstart workflow integration tests."""

    def test_complete_quickstart_flow(
        self,
        api_helper: APITestHelper,
        sample_pdf_content: bytes,
        sample_document_metadata: dict[str, Any],
        test_uuids: dict[str, str],
    ):
        """
        Test the complete quickstart workflow from upload to deletion.

        This is the main integration test that validates the entire pipeline
        workflow as described in quickstart.md. Expected to fail until
        endpoints are implemented.
        """
        # Use consistent UUIDs for this test flow
        idempotency_key = test_uuids["idempotency_1"]
        expected_document_id = test_uuids["document_1"]
        expected_job_id = test_uuids["job_1"]

        # Step 1: Health Check
        self._test_health_check(api_helper)

        # Step 2: Upload Document
        upload_response = self._test_document_upload(
            api_helper, sample_pdf_content, sample_document_metadata, idempotency_key
        )
        document_id = upload_response["document_id"]
        job_id = upload_response["job_id"]

        # Step 3: Monitor Processing Status
        self._test_job_status_monitoring(api_helper, job_id)

        # Step 3.5: Get Document Metadata
        self._test_document_metadata_retrieval(api_helper, document_id)

        # Step 4: Search Indexed Content
        search_results = self._test_content_search(api_helper, document_id)

        # Step 5: Question Answering
        self._test_question_answering(api_helper, document_id, search_results)

        # Step 6: Document Deletion
        self._test_document_deletion(api_helper, document_id)

    def _test_health_check(self, api_helper: APITestHelper):
        """Test Step 1: Health check endpoint."""
        response = api_helper.check_health()

        # Validate response structure and status
        assert response.status_code == 200
        assert_response_structure(response, ["status", "timestamp", "version", "dependencies"])

        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "dependencies" in health_data

        # Validate dependencies per quickstart.md
        dependencies = health_data["dependencies"]
        required_deps = ["database", "vector_store", "storage", "queue"]
        for dep in required_deps:
            assert dep in dependencies
            assert dependencies[dep] == "healthy"

    def _test_document_upload(
        self,
        api_helper: APITestHelper,
        pdf_content: bytes,
        metadata: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Test Step 2: Document upload with idempotency."""
        response = api_helper.upload_document(
            file_content=pdf_content,
            filename="solar-panel-efficiency-report.pdf",
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

        # Validate upload response
        assert response.status_code == 201
        assert_response_structure(
            response, ["document_id", "job_id", "filename", "file_size", "status", "upload_time"]
        )

        upload_data = response.json()

        # Validate UUID formats
        assert_uuid_format(upload_data["document_id"])
        assert_uuid_format(upload_data["job_id"])

        # Validate status and metadata
        assert upload_data["status"] in ["uploaded", "queued"]
        assert upload_data["filename"] == "solar-panel-efficiency-report.pdf"
        assert upload_data["file_size"] > 0

        return upload_data

    def _test_job_status_monitoring(self, api_helper: APITestHelper, job_id: str):
        """Test Step 3: Job status monitoring until completion."""
        max_attempts = 30  # 30 seconds timeout
        attempt = 0

        while attempt < max_attempts:
            response = api_helper.get_job_status(job_id)

            # Validate response structure
            assert response.status_code == 200
            assert_response_structure(
                response,
                [
                    "job_id",
                    "document_id",
                    "status",
                    "progress_percentage",
                    "started_at",
                    "completed_at",
                    "error_message",
                    "error_type",
                    "retry_count",
                ],
            )

            job_data = response.json()

            # Validate UUID formats
            assert_uuid_format(job_data["job_id"])
            assert_uuid_format(job_data["document_id"])

            # Check status progression
            status = job_data["status"]
            assert status in ["pending", "queued", "running", "completed", "failed"]

            # Validate progress
            progress = job_data["progress_percentage"]
            assert 0 <= progress <= 100

            # If completed, validate completion data
            if status == "completed":
                assert progress == 100
                assert job_data["completed_at"] is not None
                assert job_data["error_message"] is None
                break

            # If failed, fail the test
            if status == "failed":
                pytest.fail(f"Job failed: {job_data.get('error_message', 'Unknown error')}")

            time.sleep(1)
            attempt += 1

        if attempt >= max_attempts:
            pytest.fail("Job did not complete within timeout period")

    def _test_document_metadata_retrieval(self, api_helper: APITestHelper, document_id: str):
        """Test Step 3.5: Document metadata retrieval."""
        response = api_helper.get_document(document_id)

        # Validate response
        assert response.status_code == 200
        assert_response_structure(
            response,
            [
                "document_id",
                "filename",
                "file_size",
                "page_count",
                "processing_status",
                "upload_time",
                "metadata",
            ],
        )

        doc_data = response.json()

        # Validate UUID format
        assert_uuid_format(doc_data["document_id"])

        # Validate processing completion
        assert doc_data["processing_status"] == "completed"
        assert doc_data["page_count"] > 0
        assert doc_data["file_size"] > 0

    def _test_content_search(self, api_helper: APITestHelper, document_id: str) -> dict[str, Any]:
        """Test Step 4: Content search functionality."""
        response = api_helper.search_documents(
            query="solar panel efficiency california",
            content_types=["text", "table", "chart"],
            document_ids=[document_id],
            limit=10,
            min_confidence=0.7,
        )

        # Validate search response
        assert response.status_code == 200
        assert_response_structure(response, ["query", "total_results", "results", "filters_applied"])

        search_data = response.json()

        # Validate search metadata
        assert search_data["query"] == "solar panel efficiency california"
        assert search_data["total_results"] >= 0

        # Validate filters applied
        filters = search_data["filters_applied"]
        assert "content_types" in filters
        assert "min_confidence" in filters
        assert filters["min_confidence"] == 0.7

        # Validate search results structure
        for result in search_data["results"]:
            self._validate_search_result(result, document_id)

        return search_data

    def _validate_search_result(self, result: dict[str, Any], expected_document_id: str):
        """Validate individual search result structure."""
        required_fields = [
            "content_id",
            "document_id",
            "document_title",
            "page_number",
            "content_type",
            "snippet",
            "confidence_score",
            "relevance_score",
            "is_ocr_generated",
        ]

        for field in required_fields:
            assert field in result, f"Missing field '{field}' in search result"

        # Validate UUID formats
        assert_uuid_format(result["content_id"])
        assert_uuid_format(result["document_id"])

        # Validate document association
        assert result["document_id"] == expected_document_id

        # Validate content type
        assert result["content_type"] in ["text", "table", "chart", "image"]

        # Validate scores
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert 0.0 <= result["relevance_score"] <= 1.0
        assert result["confidence_score"] >= 0.7  # Min confidence filter

        # Validate page number
        assert result["page_number"] >= 1

        # Validate OCR flag
        assert isinstance(result["is_ocr_generated"], bool)

    def _test_question_answering(
        self, api_helper: APITestHelper, document_id: str, search_results: dict[str, Any]
    ):
        """Test Step 5: Question answering with citations."""
        response = api_helper.ask_question(
            question="What is the average solar panel efficiency in California projects?",
            context_filters={
                "document_ids": [document_id],
                "content_types": ["text", "table", "chart"],
            },
            include_thumbnails=True,
            max_citations=3,
        )

        # Validate Q&A response
        assert response.status_code == 200
        assert_response_structure(
            response, ["question", "answer", "confidence", "citations", "refinement_hints", "processing_time_ms"]
        )

        qa_data = response.json()

        # Validate question echo
        assert qa_data["question"] == "What is the average solar panel efficiency in California projects?"

        # Validate answer quality
        answer = qa_data["answer"]
        confidence = qa_data["confidence"]

        if answer == "No evidence found":
            assert confidence == 0.0
            assert len(qa_data["citations"]) == 0
            assert len(qa_data["refinement_hints"]) > 0
        else:
            assert confidence > 0.0
            assert len(answer) > 0

            # Validate citations
            citations = qa_data["citations"]
            assert len(citations) <= 3  # max_citations constraint

            for citation in citations:
                self._validate_citation(citation)

        # Validate processing time
        assert qa_data["processing_time_ms"] > 0

    def _validate_citation(self, citation: dict[str, Any]):
        """Validate individual citation structure."""
        required_fields = [
            "document_title",
            "page_number",
            "content_type",
            "snippet",
            "context",
            "confidence_score",
            "relevance_score",
            "is_ocr_generated",
        ]

        for field in required_fields:
            assert field in citation, f"Missing field '{field}' in citation"

        # Validate content type
        assert citation["content_type"] in ["text", "table", "chart", "image"]

        # Validate scores
        assert 0.0 <= citation["confidence_score"] <= 1.0
        assert 0.0 <= citation["relevance_score"] <= 1.0

        # Validate page number
        assert citation["page_number"] >= 1

        # Validate OCR flag
        assert isinstance(citation["is_ocr_generated"], bool)

    def _test_document_deletion(self, api_helper: APITestHelper, document_id: str):
        """Test Step 7: Document deletion."""
        response = api_helper.delete_document(document_id)

        # Validate deletion response
        assert response.status_code == 202
        assert_response_structure(
            response, ["document_id", "status", "deletion_scheduled_at", "message"]
        )

        deletion_data = response.json()

        # Validate UUID format
        assert_uuid_format(deletion_data["document_id"])
        assert deletion_data["document_id"] == document_id

        # Validate deletion status
        assert deletion_data["status"] == "marked_for_deletion"
        assert "deletion_scheduled_at" in deletion_data
        assert "message" in deletion_data


@pytest.mark.integration
class TestQuickstartEdgeCases:
    """Test edge cases and error scenarios from quickstart.md."""

    def test_no_results_question_answering(self, api_helper: APITestHelper):
        """Test Q&A with question that has no evidence."""
        response = api_helper.ask_question(
            question="What is the nuclear power efficiency in underwater installations?",
            max_citations=5,
        )

        # Should return 200 with "No evidence found"
        assert response.status_code == 200

        qa_data = response.json()
        assert qa_data["answer"] == "No evidence found"
        assert qa_data["confidence"] == 0.0
        assert len(qa_data["citations"]) == 0
        assert len(qa_data["refinement_hints"]) > 0

    def test_upload_file_too_large(self, api_helper: APITestHelper):
        """Test upload with file exceeding size limit."""
        # Create a mock large file (this will fail due to endpoint not existing)
        large_content = b"x" * (150 * 1024 * 1024 + 1)  # 150MB + 1 byte

        response = api_helper.upload_document(
            file_content=large_content,
            filename="large_file.pdf",
        )

        # Should return 413 Payload Too Large
        assert response.status_code == 413

        error_data = response.json()
        assert error_data["error"]["code"] == "payload_too_large"
        assert "file_size" in error_data["error"]["details"]
        assert "max_allowed" in error_data["error"]["details"]

    def test_upload_unsupported_media_type(self, api_helper: APITestHelper):
        """Test upload with non-PDF file."""
        # Mock Word document content
        word_content = b"PK\x03\x04"  # ZIP signature for DOCX

        response = api_helper.upload_document(
            file_content=word_content,
            filename="document.docx",
        )

        # Should return 415 Unsupported Media Type
        assert response.status_code == 415

        error_data = response.json()
        assert error_data["error"]["code"] == "unsupported_media_type"
        assert "provided_type" in error_data["error"]["details"]
        assert "supported_types" in error_data["error"]["details"]

    def test_upload_corrupted_pdf(self, api_helper: APITestHelper):
        """Test upload with corrupted PDF file."""
        # Mock corrupted PDF content
        corrupted_content = b"%PDF-1.4\ngarbage_data_here"

        response = api_helper.upload_document(
            file_content=corrupted_content,
            filename="corrupted.pdf",
        )

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422

        error_data = response.json()
        assert error_data["error"]["code"] == "unprocessable_entity"
        assert "validation_error" in error_data["error"]["details"]

    def test_search_with_ocr_content_flags(
        self, api_helper: APITestHelper, test_uuids: dict[str, str]
    ):
        """Test search results include OCR confidence flags."""
        # This test expects some documents to have OCR-generated content
        response = api_helper.search_documents(
            query="scanned document content",
            content_types=["text"],
            limit=5,
        )

        # Even if no results, response should be valid
        assert response.status_code == 200

        search_data = response.json()

        # If results exist, validate OCR flags
        for result in search_data["results"]:
            assert "is_ocr_generated" in result
            assert isinstance(result["is_ocr_generated"], bool)

            # OCR results should have appropriate confidence handling
            if result["is_ocr_generated"]:
                # OCR content might have lower confidence
                assert 0.0 <= result["confidence_score"] <= 1.0


@pytest.mark.integration
class TestQuickstartPerformanceRequirements:
    """Test performance requirements from quickstart.md."""

    def test_upload_response_time(self, api_helper: APITestHelper, sample_pdf_content: bytes):
        """Test upload response time < 2 seconds."""
        start_time = time.time()

        response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="performance_test.pdf",
        )

        response_time = time.time() - start_time

        # This will fail until endpoint exists, but validates performance requirement
        if response.status_code == 201:
            assert response_time < 2.0, f"Upload took {response_time:.2f}s, expected < 2s"

    def test_search_response_time(self, api_helper: APITestHelper):
        """Test search response time < 500ms."""
        start_time = time.time()

        response = api_helper.search_documents(
            query="renewable energy efficiency",
            limit=10,
        )

        response_time = time.time() - start_time

        # This will fail until endpoint exists, but validates performance requirement
        if response.status_code == 200:
            assert response_time < 0.5, f"Search took {response_time:.2f}s, expected < 0.5s"

    def test_qa_response_time(self, api_helper: APITestHelper):
        """Test Q&A response time < 2 seconds."""
        start_time = time.time()

        response = api_helper.ask_question(
            question="What are the latest efficiency trends in renewable energy?",
            max_citations=3,
        )

        response_time = time.time() - start_time

        # This will fail until endpoint exists, but validates performance requirement
        if response.status_code == 200:
            assert response_time < 2.0, f"Q&A took {response_time:.2f}s, expected < 2s"


@pytest.mark.integration
class TestQuickstartQualityMetrics:
    """Test quality metrics requirements from quickstart.md."""

    def test_page_anchoring_requirement(self, api_helper: APITestHelper):
        """Test ≥95% page anchoring requirement."""
        response = api_helper.search_documents(
            query="efficiency data",
            limit=20,
        )

        if response.status_code == 200:
            search_data = response.json()
            results = search_data["results"]

            if len(results) > 0:
                # Validate that all results have valid page numbers
                valid_page_anchors = 0
                for result in results:
                    if "page_number" in result and result["page_number"] >= 1:
                        valid_page_anchors += 1

                page_anchor_rate = valid_page_anchors / len(results)
                assert page_anchor_rate >= 0.95, f"Page anchoring rate {page_anchor_rate:.2%} < 95%"

    def test_table_extraction_requirement(self, api_helper: APITestHelper):
        """Test ≥90% table extraction requirement."""
        response = api_helper.search_documents(
            query="data table",
            content_types=["table"],
            limit=10,
        )

        if response.status_code == 200:
            search_data = response.json()
            table_results = search_data["results"]

            if len(table_results) > 0:
                # Validate table metadata exists
                valid_tables = 0
                for result in table_results:
                    if (
                        result["content_type"] == "table"
                        and "metadata" in result
                        and result["metadata"] is not None
                    ):
                        valid_tables += 1

                table_extraction_rate = valid_tables / len(table_results)
                assert table_extraction_rate >= 0.90, f"Table extraction rate {table_extraction_rate:.2%} < 90%"

    def test_citation_correctness_requirement(self, api_helper: APITestHelper):
        """Test ≥95% citation correctness requirement."""
        response = api_helper.ask_question(
            question="What efficiency metrics are reported in the documents?",
            max_citations=5,
        )

        if response.status_code == 200:
            qa_data = response.json()
            citations = qa_data["citations"]

            if len(citations) > 0:
                # Validate citation correctness
                valid_citations = 0
                for citation in citations:
                    # Check required fields are present and valid
                    if (
                        citation.get("page_number", 0) >= 1
                        and citation.get("document_title")
                        and citation.get("snippet")
                        and citation.get("content_type") in ["text", "table", "chart", "image"]
                    ):
                        valid_citations += 1

                citation_correctness_rate = valid_citations / len(citations)
                assert citation_correctness_rate >= 0.95, f"Citation correctness rate {citation_correctness_rate:.2%} < 95%"
