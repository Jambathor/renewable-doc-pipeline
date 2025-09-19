"""
Integration tests for OCR flag functionality (T079).

Tests that validate OCR processing flags, confidence tracking, and visual content
handling in search results and Q&A responses. These tests are designed to fail
initially following TDD approach until OCR endpoints are implemented.
"""

from typing import Any, Dict

import httpx
import pytest

from tests.fixtures.api_client import (
    APITestHelper,
    assert_response_structure,
    assert_uuid_format,
)
from tests.fixtures.test_data import sample_document_uuids


@pytest.mark.integration
class TestOCRFlag:
    """Test OCR flag functionality and confidence tracking."""

    def test_scanned_pdf_yields_ocr_flag_true_in_search(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: dict[str, str],
        scanned_pdf_content: bytes,
    ):
        """Test that scanned PDF uploads yield is_ocr_generated: true in search results."""
        # Upload scanned PDF document
        response = api_helper.upload_document(
            file_content=scanned_pdf_content,
            filename="scanned_wind_report.pdf",
            metadata={
                "title": "Scanned Wind Energy Report",
                "tags": ["wind", "scanned", "ocr"],
            },
            idempotency_key=sample_document_uuids["document_1"],
        )

        # Expect successful upload
        assert response.status_code == 201
        upload_data = response.json()
        document_id = upload_data["document_id"]
        job_id = upload_data["job_id"]

        # Wait for processing to complete
        self._wait_for_job_completion(api_helper, job_id)

        # Search for OCR content
        search_response = api_helper.search_documents(
            query="wind energy efficiency",
            content_types=["text", "table", "chart"],
            document_ids=[document_id],
        )

        assert search_response.status_code == 200
        search_data = search_response.json()

        # Validate OCR flags in search results
        assert search_data["total_results"] > 0
        for result in search_data["results"]:
            assert_response_structure(
                httpx.Response(200, json=result),
                ["content_id", "document_id", "is_ocr_generated", "confidence_score"]
            )
            assert_uuid_format(result["content_id"])
            assert result["is_ocr_generated"] is True, "Scanned PDF should yield OCR-generated content"
            assert 0.0 <= result["confidence_score"] <= 1.0

    def test_native_digital_pdf_yields_ocr_flag_false_in_search(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: dict[str, str],
        sample_pdf_content: bytes,
    ):
        """Test that native digital PDFs yield is_ocr_generated: false in search results."""
        # Upload native digital PDF document
        response = api_helper.upload_document(
            file_content=sample_pdf_content,
            filename="native_solar_report.pdf",
            metadata={
                "title": "Native Solar Energy Report",
                "tags": ["solar", "digital", "native"],
            },
            idempotency_key=sample_document_uuids["document_2"],
        )

        # Expect successful upload
        assert response.status_code == 201
        upload_data = response.json()
        document_id = upload_data["document_id"]
        job_id = upload_data["job_id"]

        # Wait for processing to complete
        self._wait_for_job_completion(api_helper, job_id)

        # Search for native content
        search_response = api_helper.search_documents(
            query="renewable energy",
            content_types=["text"],
            document_ids=[document_id],
        )

        assert search_response.status_code == 200
        search_data = search_response.json()

        # Validate no OCR flags in search results for native content
        assert search_data["total_results"] > 0
        for result in search_data["results"]:
            assert result["is_ocr_generated"] is False, "Native PDF should not be OCR-generated"
            assert result["confidence_score"] >= 0.9, "Native text should have high confidence"

    def test_ocr_confidence_scores_are_tracked(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: dict[str, str],
        poor_quality_scanned_pdf: bytes,
    ):
        """Test that OCR confidence scores are properly tracked and reported."""
        # Upload poor quality scanned PDF
        response = api_helper.upload_document(
            file_content=poor_quality_scanned_pdf,
            filename="poor_quality_scan.pdf",
            metadata={
                "title": "Poor Quality Scanned Report",
                "tags": ["scanned", "poor_quality", "ocr"],
            },
            idempotency_key=sample_document_uuids["document_3"],
        )

        assert response.status_code == 201
        upload_data = response.json()
        document_id = upload_data["document_id"]
        job_id = upload_data["job_id"]

        # Wait for processing to complete
        self._wait_for_job_completion(api_helper, job_id)

        # Search and validate confidence tracking
        search_response = api_helper.search_documents(
            query="energy report",
            document_ids=[document_id],
            min_confidence=0.1,  # Lower threshold to catch poor OCR
        )

        assert search_response.status_code == 200
        search_data = search_response.json()

        # Validate confidence score distribution for OCR content
        ocr_results = [r for r in search_data["results"] if r["is_ocr_generated"]]
        assert len(ocr_results) > 0, "Should have OCR-generated results"

        for result in ocr_results:
            # Poor quality scans should have lower confidence scores
            assert result["confidence_score"] < 0.9, "Poor OCR should have lower confidence"
            assert result["confidence_score"] >= 0.1, "Should meet minimum threshold"

    def test_ocr_content_appears_in_search_and_qa_responses(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: dict[str, str],
        scanned_pdf_content: bytes,
    ):
        """Test that OCR content is searchable and quotable in Q&A responses."""
        # Upload scanned document
        response = api_helper.upload_document(
            file_content=scanned_pdf_content,
            filename="scanned_chart_report.pdf",
            metadata={
                "title": "Scanned Chart Report",
                "tags": ["charts", "ocr", "visual"],
            },
            idempotency_key=sample_document_uuids["job_1"],
        )

        assert response.status_code == 201
        upload_data = response.json()
        document_id = upload_data["document_id"]
        job_id = upload_data["job_id"]

        # Wait for processing
        self._wait_for_job_completion(api_helper, job_id)

        # Test Q&A with OCR content
        qa_response = api_helper.ask_question(
            question="What efficiency data is shown in the charts?",
            context_filters={
                "document_ids": [document_id],
                "content_types": ["chart", "table"],
            },
            include_thumbnails=True,
        )

        assert qa_response.status_code == 200
        qa_data = qa_response.json()

        # Validate OCR content in citations
        assert qa_data["confidence"] > 0.0
        assert len(qa_data["citations"]) > 0

        ocr_citations = [c for c in qa_data["citations"] if c["is_ocr_generated"]]
        assert len(ocr_citations) > 0, "Should include OCR-generated citations"

        for citation in ocr_citations:
            assert citation["content_type"] in ["chart", "table", "text"]
            assert citation["confidence_score"] > 0.0
            assert len(citation["snippet"]) > 0

    def test_visual_content_thumbnails_for_ocr_generated_content(
        self,
        api_helper: APITestHelper,
        sample_document_uuids: dict[str, str],
        scanned_chart_pdf: bytes,
    ):
        """Test that visual content thumbnails are provided for OCR-generated content."""
        # Upload document with charts/tables
        response = api_helper.upload_document(
            file_content=scanned_chart_pdf,
            filename="scanned_charts.pdf",
            metadata={
                "title": "Scanned Visual Content",
                "tags": ["charts", "tables", "visual"],
            },
            idempotency_key=sample_document_uuids["content_1"],
        )

        assert response.status_code == 201
        upload_data = response.json()
        document_id = upload_data["document_id"]
        job_id = upload_data["job_id"]

        # Wait for processing
        self._wait_for_job_completion(api_helper, job_id)

        # Search for visual content
        search_response = api_helper.search_documents(
            query="efficiency chart",
            content_types=["chart", "table"],
            document_ids=[document_id],
        )

        assert search_response.status_code == 200
        search_data = search_response.json()

        # Validate thumbnails for visual OCR content
        visual_results = [
            r for r in search_data["results"]
            if r["content_type"] in ["chart", "table"] and r["is_ocr_generated"]
        ]

        assert len(visual_results) > 0, "Should find visual OCR content"

        for result in visual_results:
            if result["content_type"] in ["chart", "table"]:
                assert result["thumbnail_url"] is not None, "Visual content should have thumbnails"
                assert result["thumbnail_url"].startswith("https://"), "Should be valid URL"
                assert "expires" in result["thumbnail_url"], "Should be pre-signed URL"

    def _wait_for_job_completion(self, api_helper: APITestHelper, job_id: str, timeout: int = 60):
        """Helper to wait for job completion with timeout."""
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            response = api_helper.get_job_status(job_id)
            if response.status_code == 200:
                job_data = response.json()
                if job_data["status"] in ["completed", "failed"]:
                    assert job_data["status"] == "completed", f"Job failed: {job_data.get('error_message')}"
                    return
            time.sleep(2)

        pytest.fail(f"Job {job_id} did not complete within {timeout} seconds")


@pytest.fixture
def scanned_pdf_content() -> bytes:
    """Sample scanned PDF content that requires OCR processing."""
    # Simulated scanned PDF that would trigger OCR processing
    # In real implementation, this would be a PDF with image-based content
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/XObject <<
/Im1 4 0 R
>>
>>
/MediaBox [0 0 612 792]
/Contents 5 0 R
>>
endobj

4 0 obj
<<
/Type /XObject
/Subtype /Image
/Width 400
/Height 300
/ColorSpace /DeviceRGB
/BitsPerComponent 8
/Length 7
>>
stream
SCANNED
endstream
endobj

5 0 obj
<<
/Length 25
>>
stream
q
400 0 0 300 100 400 cm
/Im1 Do
Q
endstream
endobj

xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000136 00000 n
0000000301 00000 n
0000000458 00000 n
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
534
%%EOF"""


@pytest.fixture
def poor_quality_scanned_pdf() -> bytes:
    """Sample poor quality scanned PDF for confidence testing."""
    # Simulated poor quality scan with low OCR confidence
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/XObject <<
/Im1 4 0 R
>>
>>
/MediaBox [0 0 612 792]
/Contents 5 0 R
>>
endobj

4 0 obj
<<
/Type /XObject
/Subtype /Image
/Width 200
/Height 150
/ColorSpace /DeviceGray
/BitsPerComponent 1
/Length 12
>>
stream
POOR_QUALITY_
endstream
endobj

5 0 obj
<<
/Length 25
>>
stream
q
200 0 0 150 100 300 cm
/Im1 Do
Q
endstream
endobj

xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000136 00000 n
0000000301 00000 n
0000000464 00000 n
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
540
%%EOF"""


@pytest.fixture
def scanned_chart_pdf() -> bytes:
    """Sample scanned PDF with charts and tables for thumbnail testing."""
    # Simulated scanned PDF with visual content requiring thumbnails
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/XObject <<
/Chart1 4 0 R
/Table1 5 0 R
>>
>>
/MediaBox [0 0 612 792]
/Contents 6 0 R
>>
endobj

4 0 obj
<<
/Type /XObject
/Subtype /Image
/Width 300
/Height 200
/ColorSpace /DeviceRGB
/BitsPerComponent 8
/Length 15
>>
stream
EFFICIENCY_CHART
endstream
endobj

5 0 obj
<<
/Type /XObject
/Subtype /Image
/Width 250
/Height 150
/ColorSpace /DeviceRGB
/BitsPerComponent 8
/Length 12
>>
stream
DATA_TABLE_
endstream
endobj

6 0 obj
<<
/Length 55
>>
stream
q
300 0 0 200 50 500 cm
/Chart1 Do
Q
q
250 0 0 150 300 200 cm
/Table1 Do
Q
endstream
endobj

xref
0 7
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000136 00000 n
0000000336 00000 n
0000000506 00000 n
0000000667 00000 n
trailer
<<
/Size 7
/Root 1 0 R
>>
startxref
773
%%EOF"""
