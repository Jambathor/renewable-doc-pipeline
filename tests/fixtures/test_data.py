"""
Test data fixtures for renewable energy document processing pipeline.

Provides sample data for documents, jobs, search results, Q&A data that
matches the OpenAPI schema requirements and follows UUID format requirements.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest


@pytest.fixture
def sample_document_uuids() -> dict[str, str]:
    """Sample UUIDs for document testing in proper format."""
    return {
        "document_1": "550e8400-e29b-41d4-a716-446655440000",
        "document_2": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "document_3": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
        "job_1": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "job_2": "6ba7b812-9dad-11d1-80b4-00c04fd430c8",
        "content_1": "01234567-89ab-cdef-0123-456789abcdef",
        "content_2": "98765432-10fe-dcba-9876-543210fedcba",
        "content_3": "11111111-2222-3333-4444-555555555555",
    }


@pytest.fixture
def sample_document_metadata() -> dict[str, Any]:
    """Sample document metadata matching OpenAPI schema."""
    return {
        "title": "Solar Energy Efficiency Report 2024",
        "tags": ["solar", "efficiency", "renewable", "2024"],
        "source_url": "https://example.com/solar-report-2024.pdf",
        "uploaded_by": "researcher@renewabletech.com",
    }


@pytest.fixture
def sample_document_upload_data(sample_document_uuids: dict[str, str]) -> dict[str, Any]:
    """Sample document upload response data."""
    return {
        "document_id": sample_document_uuids["document_1"],
        "job_id": sample_document_uuids["job_1"],
        "filename": "solar_efficiency_report_2024.pdf",
        "file_size": 2457600,  # ~2.4MB
        "status": "uploaded",
        "upload_time": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def sample_job_status_data(sample_document_uuids: dict[str, str]) -> dict[str, Any]:
    """Sample job status response data."""
    return {
        "job_id": sample_document_uuids["job_1"],
        "document_id": sample_document_uuids["document_1"],
        "status": "completed",
        "progress_percentage": 100,
        "started_at": "2024-01-15T10:30:05Z",
        "completed_at": "2024-01-15T10:32:45Z",
        "error_message": None,
        "error_type": None,
        "retry_count": 0,
    }


@pytest.fixture
def sample_failed_job_status_data(sample_document_uuids: dict[str, str]) -> dict[str, Any]:
    """Sample failed job status response data."""
    return {
        "job_id": sample_document_uuids["job_2"],
        "document_id": sample_document_uuids["document_2"],
        "status": "failed",
        "progress_percentage": 45,
        "started_at": "2024-01-15T11:00:00Z",
        "completed_at": None,
        "error_message": "PDF structure validation failed: corrupted file header",
        "error_type": "validation_error",
        "retry_count": 2,
    }


@pytest.fixture
def sample_search_results(sample_document_uuids: dict[str, str]) -> dict[str, Any]:
    """Sample search response data matching OpenAPI schema."""
    return {
        "query": "solar panel efficiency trends",
        "total_results": 3,
        "results": [
            {
                "content_id": sample_document_uuids["content_1"],
                "document_id": sample_document_uuids["document_1"],
                "document_title": "Solar Energy Efficiency Report 2024",
                "page_number": 15,
                "content_type": "text",
                "snippet": "Solar panel efficiency has improved by 12% year-over-year, with crystalline silicon panels reaching 22.5% efficiency in commercial applications.",
                "confidence_score": 0.95,
                "relevance_score": 0.88,
                "is_ocr_generated": False,
                "metadata": {
                    "section": "efficiency_analysis",
                    "subsection": "commercial_panels",
                },
                "thumbnail_url": None,
            },
            {
                "content_id": sample_document_uuids["content_2"],
                "document_id": sample_document_uuids["document_1"],
                "document_title": "Solar Energy Efficiency Report 2024",
                "page_number": 23,
                "content_type": "chart",
                "snippet": "Efficiency comparison chart showing trends from 2020-2024",
                "confidence_score": 0.87,
                "relevance_score": 0.82,
                "is_ocr_generated": True,
                "metadata": {
                    "chart_type": "line_graph",
                    "data_points": 48,
                },
                "thumbnail_url": "https://s3.amazonaws.com/test-bucket/thumbnails/chart_123.jpg?expires=1642248000",
            },
            {
                "content_id": sample_document_uuids["content_3"],
                "document_id": sample_document_uuids["document_2"],
                "document_title": "Wind Energy Technical Analysis",
                "page_number": 8,
                "content_type": "table",
                "snippet": "Efficiency data table with quarterly performance metrics",
                "confidence_score": 0.91,
                "relevance_score": 0.75,
                "is_ocr_generated": False,
                "metadata": {
                    "table_rows": 12,
                    "table_columns": 6,
                },
                "thumbnail_url": None,
            },
        ],
        "filters_applied": {
            "content_types": ["text", "chart", "table"],
            "min_confidence": 0.7,
        },
    }


@pytest.fixture
def sample_question_request() -> dict[str, Any]:
    """Sample Q&A question request data."""
    return {
        "question": "What are the latest efficiency improvements in solar panel technology?",
        "context_filters": {
            "content_types": ["text", "chart", "table"],
            "date_range": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        },
        "include_thumbnails": True,
        "max_citations": 5,
    }


@pytest.fixture
def sample_question_response(sample_document_uuids: dict[str, str]) -> dict[str, Any]:
    """Sample Q&A response data matching OpenAPI schema."""
    return {
        "question": "What are the latest efficiency improvements in solar panel technology?",
        "answer": "Recent advances in solar panel technology have shown significant efficiency improvements. Crystalline silicon panels have reached 22.5% efficiency in commercial applications, representing a 12% year-over-year improvement. Additionally, perovskite-silicon tandem cells in laboratory settings have achieved over 31% efficiency, suggesting promising future developments for commercial deployment.",
        "confidence": 0.89,
        "citations": [
            {
                "document_title": "Solar Energy Efficiency Report 2024",
                "page_number": 15,
                "content_type": "text",
                "snippet": "Solar panel efficiency has improved by 12% year-over-year, with crystalline silicon panels reaching 22.5% efficiency in commercial applications.",
                "context": "This data represents commercial deployments across North America and Europe during Q3-Q4 2024.",
                "confidence_score": 0.95,
                "relevance_score": 0.92,
                "is_ocr_generated": False,
                "thumbnail_url": None,
            },
            {
                "document_title": "Solar Energy Efficiency Report 2024",
                "page_number": 23,
                "content_type": "chart",
                "snippet": "Efficiency trends chart showing progressive improvements from 2020-2024",
                "context": None,
                "confidence_score": 0.87,
                "relevance_score": 0.85,
                "is_ocr_generated": True,
                "thumbnail_url": "https://s3.amazonaws.com/test-bucket/thumbnails/chart_123.jpg?expires=1642248000",
            },
        ],
        "refinement_hints": [
            "Try asking about specific panel types (monocrystalline, polycrystalline, thin-film)",
            "Consider narrowing the time range for more recent developments",
        ],
        "processing_time_ms": 1250,
    }


@pytest.fixture
def sample_document_response(sample_document_uuids: dict[str, str]) -> dict[str, Any]:
    """Sample document metadata response data."""
    return {
        "document_id": sample_document_uuids["document_1"],
        "filename": "solar_efficiency_report_2024.pdf",
        "file_size": 2457600,
        "page_count": 45,
        "processing_status": "completed",
        "upload_time": "2024-01-15T10:30:00Z",
        "metadata": {
            "title": "Solar Energy Efficiency Report 2024",
            "tags": ["solar", "efficiency", "renewable", "2024"],
            "source_url": "https://example.com/solar-report-2024.pdf",
            "uploaded_by": "researcher@renewabletech.com",
        },
    }


@pytest.fixture
def sample_deletion_response(sample_document_uuids: dict[str, str]) -> dict[str, Any]:
    """Sample document deletion response data."""
    return {
        "document_id": sample_document_uuids["document_1"],
        "status": "marked_for_deletion",
        "deletion_scheduled_at": "2024-01-15T15:00:00Z",
        "message": "Document marked for deletion and will be removed within 24 hours",
    }


@pytest.fixture
def sample_health_response() -> dict[str, Any]:
    """Sample health check response data."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-15T12:00:00Z",
        "version": "1.0.0",
        "dependencies": {
            "database": "healthy",
            "vector_store": "healthy",
            "storage": "healthy",
            "queue": "healthy",
        },
    }


@pytest.fixture
def sample_unhealthy_response() -> dict[str, Any]:
    """Sample unhealthy health check response data."""
    return {
        "status": "unhealthy",
        "timestamp": "2024-01-15T12:00:00Z",
        "version": "1.0.0",
        "dependencies": {
            "database": "healthy",
            "vector_store": "unhealthy",
            "storage": "healthy",
            "queue": "healthy",
        },
    }


@pytest.fixture
def sample_error_response() -> dict[str, Any]:
    """Sample error response data."""
    return {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid file format: only PDF files are supported",
            "details": {
                "file_type": "image/jpeg",
                "supported_types": ["application/pdf"],
            },
            "request_id": "req_01HXZ9K7N8P2Q3R4S5T6U7V8W9",
        }
    }


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF file content for upload testing."""
    # Minimal but valid PDF structure for testing
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
/Font <<
/F1 4 0 R
>>
>>
/MediaBox [0 0 612 792]
/Contents 5 0 R
>>
endobj

4 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Times-Roman
>>
endobj

5 0 obj
<<
/Length 73
>>
stream
BT
/F1 18 Tf
100 700 Td
(Test renewable energy document) Tj
ET
endstream
endobj

xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000136 00000 n
0000000271 00000 n
0000000349 00000 n
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
474
%%EOF"""


@pytest.fixture
def search_query_params() -> dict[str, Any]:
    """Sample search query parameters for testing."""
    return {
        "query": "solar efficiency trends",
        "content_types": "text,chart,table",
        "document_ids": "550e8400-e29b-41d4-a716-446655440000,6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "page_range": "1-50",
        "limit": 10,
        "min_confidence": 0.8,
    }


@pytest.fixture
def invalid_search_params() -> dict[str, Any]:
    """Invalid search parameters for error testing."""
    return {
        "query": "",  # Empty query
        "limit": 150,  # Exceeds maximum
        "min_confidence": 1.5,  # Out of range
        "page_range": "invalid-range",  # Invalid format
    }


@pytest.fixture
def multipart_form_data(sample_pdf_content: bytes, sample_document_metadata: dict[str, Any]) -> dict[str, Any]:
    """Sample multipart form data for document upload."""
    import json

    return {
        "files": {
            "file": ("solar_report_2024.pdf", sample_pdf_content, "application/pdf")
        },
        "data": {
            "metadata": json.dumps(sample_document_metadata)
        }
    }
