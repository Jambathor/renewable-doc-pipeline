# Quickstart: Renewable Energy PDF Processing Pipeline

**Date**: 2025-09-17  
**Feature**: Renewable Energy PDF Processing Pipeline  
**Branch**: `001-we-re-building`

## Overview

This quickstart guide demonstrates the complete workflow of the renewable energy PDF processing pipeline, from document upload through question answering with citations.

## Prerequisites

- Valid API key with account limits (200 documents max)
- Sample renewable energy PDF files (<=150MB, <=300 pages each)
- HTTP client (curl, Postman, or similar)
- Base URL: `https://api.renewable-docs.example.com`

## Step 1: Health Check

Verify the API service is running and healthy.

```bash
curl -X GET https://api.renewable-docs.example.com/healthz
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-17T10:00:00Z",
  "version": "1.0.0",
  "dependencies": {
    "database": "healthy",
    "vector_store": "healthy",
    "storage": "healthy",
    "queue": "healthy"
  }
}
```

**Note**: In this demo implementation, "queue" refers to the background task runner since async processing uses in-process background tasks rather than external message queues.

## Step 2: Upload a PDF Document

Upload a renewable energy PDF for processing and indexing.

```bash
curl -X POST https://api.renewable-docs.example.com/documents \
  -H "X-API-Key: your-api-key-here" \
  -H "Idempotency-Key: 123e4567-e89b-12d3-a456-426614174000" \
  -F "file=@solar-panel-efficiency-report.pdf" \
  -F 'metadata={"title":"Solar Panel Efficiency Report 2024","tags":["solar","efficiency","california"],"source_url":"https://example.com/report.pdf","uploaded_by":"researcher@company.com"}'
```

**Expected Response:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "filename": "solar-panel-efficiency-report.pdf",
  "file_size": 2457600,
  "status": "uploaded",
  "upload_time": "2025-09-17T10:01:00Z"
}
```

**Validation Points:**
- ✅ Document uploaded successfully (201 Created)
- ✅ Valid UUID returned for document_id and job_id
- ✅ Status is "uploaded" or "queued"
- ✅ File size and filename correctly captured

## Step 3: Monitor Processing Status

Check the processing job status until completion.

```bash
curl -X GET https://api.renewable-docs.example.com/jobs/6ba7b810-9dad-11d1-80b4-00c04fd430c8 \
  -H "X-API-Key: your-api-key-here"
```

**Expected Response (Processing):**
```json
{
  "job_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress_percentage": 65,
  "started_at": "2025-09-17T10:01:30Z",
  "completed_at": null,
  "error_message": null,
  "error_type": null,
  "retry_count": 0
}
```

**Expected Response (Completed):**
```json
{
  "job_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress_percentage": 100,
  "started_at": "2025-09-17T10:01:30Z",
  "completed_at": "2025-09-17T10:03:45Z",
  "error_message": null,
  "error_type": null,
  "retry_count": 0
}
```

**Validation Points:**
- ✅ Status progresses from "pending" → "running" → "completed"
- ✅ Progress percentage increases from 0 to 100
- ✅ completed_at timestamp populated on success
- ✅ No error messages or retry attempts

## Step 3.5: Get Document Metadata

Retrieve document metadata and processing status.

```bash
curl -X GET https://api.renewable-docs.example.com/documents/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your-api-key-here"
```

**Expected Response:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "solar-panel-efficiency-report.pdf",
  "file_size": 2457600,
  "page_count": 42,
  "processing_status": "completed",
  "upload_time": "2025-09-17T10:01:00Z",
  "metadata": {
    "title": "Solar Panel Efficiency Report 2024",
    "tags": ["solar", "efficiency", "california"],
    "source_url": "https://example.com/report.pdf",
    "uploaded_by": "researcher@company.com"
  }
}
```

## Step 4: Search Indexed Content

Search across the processed document content.

```bash
curl -X GET "https://api.renewable-docs.example.com/search?query=solar%20panel%20efficiency%20california&content_types=text,table,chart&limit=10&min_confidence=0.7" \
  -H "X-API-Key: your-api-key-here"
```

**Expected Response:**
```json
{
  "query": "solar panel efficiency california",
  "total_results": 8,
  "results": [
    {
      "content_id": "123e4567-e89b-12d3-a456-426614174000",
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "document_title": "Solar Panel Efficiency Report 2024",
      "page_number": 15,
      "content_type": "table",
      "snippet": "California solar installations showed 22.5% average efficiency with peak performance of 24.8% under optimal conditions...",
      "confidence_score": 0.92,
      "relevance_score": 0.88,
      "is_ocr_generated": false,
      "metadata": {
        "table_type": "performance_data",
        "headers": ["Location", "Efficiency %", "Peak Performance %"],
        "rows": 12
      },
      "thumbnail_url": null
    },
    {
      "content_id": "123e4567-e89b-12d3-a456-426614174001",
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "document_title": "Solar Panel Efficiency Report 2024",
      "page_number": 8,
      "content_type": "chart",
      "snippet": "Performance comparison chart showing California leading in residential solar efficiency metrics across Q1-Q4 2024",
      "confidence_score": 0.85,
      "relevance_score": 0.82,
      "is_ocr_generated": false,
      "metadata": {
        "chart_type": "bar_chart",
        "axes": {"x": "Quarter", "y": "Efficiency %"},
        "data_series": ["CA", "TX", "FL", "AZ"]
      },
      "thumbnail_url": "https://s3.amazonaws.com/bucket/123e4567-e89b-12d3-a456-426614174001-thumb.png?X-Amz-Expires=3600&X-Amz-Signature=..."
    }
  ],
  "filters_applied": {
    "content_types": ["text", "table", "chart"],
    "min_confidence": 0.7
  }
}
```

**Note**: Thumbnail URLs are pre-signed and expire after a limited time for security.

**Rate Limiting**: The /search and /qa endpoints MAY return HTTP 429 if rate limits are exceeded. Clients should implement retry with exponential backoff.

**Validation Points:**
- ✅ Results ranked by relevance score
- ✅ Multiple content types returned (text, table, chart)
- ✅ All results have page references
- ✅ Confidence scores meet minimum threshold
- ✅ Document titles and content types correctly labeled

## Step 5: Question Answering with Citations

Ask a specific question and get an evidence-grounded answer.

```bash
curl -X POST https://api.renewable-docs.example.com/qa \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the average solar panel efficiency in California projects?",
    "context_filters": {
      "document_ids": ["550e8400-e29b-41d4-a716-446655440000"],
      "content_types": ["text", "table", "chart"]
    },
    "include_thumbnails": true,
    "max_citations": 3
  }'
```

**Expected Response:**
```json
{
  "question": "What is the average solar panel efficiency in California projects?",
  "answer": "Based on the data from the Solar Panel Efficiency Report 2024, California solar installations show an average efficiency of 22.5%, with peak performance reaching 24.8% under optimal conditions. The state leads in residential solar efficiency metrics, consistently outperforming other major solar markets like Texas, Florida, and Arizona throughout 2024.",
  "confidence": 0.91,
  "citations": [
    {
      "document_title": "Solar Panel Efficiency Report 2024",
      "page_number": 15,
      "content_type": "table",
      "snippet": "California solar installations showed 22.5% average efficiency with peak performance of 24.8% under optimal conditions",
      "context": "Performance data table comparing efficiency metrics across western states for residential installations",
      "confidence_score": 0.92,
      "relevance_score": 0.95,
      "is_ocr_generated": false,
      "thumbnail_url": null
    },
    {
      "document_title": "Solar Panel Efficiency Report 2024",
      "page_number": 8,
      "content_type": "chart",
      "snippet": "Performance comparison chart showing California leading in residential solar efficiency metrics across Q1-Q4 2024",
      "context": "Quarterly performance analysis with bar chart visualization",
      "confidence_score": 0.85,
      "relevance_score": 0.89,
      "is_ocr_generated": false,
      "thumbnail_url": "https://s3.amazonaws.com/bucket/123e4567-e89b-12d3-a456-426614174001-thumb.png?X-Amz-Expires=3600&X-Amz-Signature=..."
    },
    {
      "document_title": "Solar Panel Efficiency Report 2024",
      "page_number": 23,
      "content_type": "text",
      "snippet": "California's regulatory framework and optimal weather conditions contribute to higher efficiency rates compared to national averages",
      "context": "Analysis section discussing factors affecting regional performance variations",
      "confidence_score": 0.88,
      "relevance_score": 0.82,
      "is_ocr_generated": false,
      "thumbnail_url": null
    }
  ],
  "refinement_hints": [],
  "processing_time_ms": 850
}
```

**Validation Points:**
- ✅ Answer includes specific numerical data from documents
- ✅ At least 3 citations with correct document titles and page numbers
- ✅ Citations include mix of content types (table, chart, text)
- ✅ High confidence scores (≥0.8) for answer and citations
- ✅ Thumbnail URLs provided for visual content when requested

## Step 6: Test Edge Cases

### 6.1 No Results Found

```bash
curl -X POST https://api.renewable-docs.example.com/qa \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the nuclear power efficiency in underwater installations?",
    "max_citations": 5
  }'
```

**Expected Response:**
```json
{
  "question": "What is the nuclear power efficiency in underwater installations?",
  "answer": "No evidence found",
  "confidence": 0.0,
  "citations": [],
  "refinement_hints": [
    "Try searching for 'renewable energy' or 'solar/wind power' instead",
    "Check if your documents contain the specific topic you're asking about",
    "Consider broadening your question to related energy technologies"
  ],
  "processing_time_ms": 120
}
```

### 6.2 OCR Content with Confidence Flags

Upload a scanned PDF and verify OCR processing:

```bash
curl -X POST https://api.renewable-docs.example.com/documents \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@scanned-wind-report.pdf"
```

Search results should include `"is_ocr_generated": true` for scanned content.

### 6.3 Account Quota Validation

Attempt to upload when near the 200-document limit:

**Expected Response (429 Too Many Requests):**
```json
{
  "error": {
    "code": "quota_exceeded",
    "message": "Account has reached maximum document limit of 200. Delete existing documents to upload new ones.",
    "details": {
      "current_count": 200,
      "max_allowed": 200
    },
    "request_id": "req-789-abc-def"
  }
}
```

### 6.4 Upload Error Validation

Test file size limit (413), unsupported media type (415), and invalid PDF structure (422):

**File Too Large (413 Payload Too Large):**
```json
{
  "error": {
    "code": "payload_too_large",
    "message": "File size exceeds maximum limit of 150MB",
    "details": {
      "file_size": 157286401,
      "max_allowed": 157286400
    },
    "request_id": "req-413-large-file"
  }
}
```

**Unsupported Media Type (415):**
```json
{
  "error": {
    "code": "unsupported_media_type",
    "message": "Only PDF files are supported",
    "details": {
      "provided_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "supported_types": ["application/pdf"]
    },
    "request_id": "req-415-wrong-type"
  }
}
```

**Invalid PDF Structure (422 Unprocessable Entity):**
```json
{
  "error": {
    "code": "unprocessable_entity",
    "message": "PDF file is corrupted or has invalid structure",
    "details": {
      "validation_error": "Unable to read PDF metadata"
    },
    "request_id": "req-422-corrupt-pdf"
  }
}
```

## Step 7: Document Deletion

Clean up by deleting the test document:

```bash
curl -X DELETE https://api.renewable-docs.example.com/documents/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your-api-key-here"
```

**Expected Response:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "marked_for_deletion",
  "deletion_scheduled_at": "2025-09-18T10:00:00Z",
  "message": "Document will be permanently deleted within 24 hours"
}
```

**Note**: In this demo, the system performs deletion immediately upon receiving the DELETE request, though the API response preserves the same format for contract compatibility.

## Quality Metrics Verification

The quickstart should demonstrate compliance with SLA requirements:

### Page Anchoring (≥95% requirement)
- ✅ All search results include valid page_number fields
- ✅ Citations reference specific pages in source documents
- ✅ Page references are consistent across multiple queries

### Table Extraction (≥90% requirement)
- ✅ Identifiable tables detected and extracted as "table" content type
- ✅ Table metadata includes headers and row counts
- ✅ Table content searchable and quotable in responses

### Citation Correctness (≥95% requirement)
- ✅ Document titles match uploaded filenames/metadata
- ✅ Page numbers are valid (1-based, within document range)
- ✅ Content snippets accurately reflect source material
- ✅ Multiple citations provided for comprehensive answers

## Troubleshooting

### Common Issues

1. **Processing Stuck in "running" status**
   - Check system load and background task capacity
   - Check API/background task logs for processing errors
   - SQS/CloudWatch available in future deployments

2. **Low confidence scores in search results**
   - Document may have poor OCR quality
   - Try broadening search terms
   - Check if content type filters are too restrictive

3. **No search results returned**
   - Verify document processing completed successfully
   - Check if search terms match document content
   - Ensure API key has access to the document account

4. **Citations missing page numbers**
   - Document may have processing errors during indexing
   - Re-upload document if anchor extraction failed
   - Check quality metrics for anchor success rate

### Performance Expectations

- **Upload Response**: < 2 seconds for files up to 150MB
- **Processing Time**: 30-180 seconds depending on document complexity
- **Search Response**: < 500ms for typical queries
- **Q&A Response**: < 2 seconds including evidence retrieval

This quickstart validates the complete pipeline functionality and serves as an integration test for the acceptance criteria defined in the feature specification.