# Integration Tests

This directory contains integration tests that validate end-to-end functionality of the renewable energy document processing pipeline.

## Test Files

### T079 - OCR Flag Tests (`test_ocr_flag.py`)
Tests OCR functionality and confidence tracking:
- ✅ `test_scanned_pdf_yields_ocr_flag_true_in_search` - Validates `is_ocr_generated: true` for scanned PDFs
- ✅ `test_native_digital_pdf_yields_ocr_flag_false_in_search` - Validates `is_ocr_generated: false` for native PDFs  
- ✅ `test_ocr_confidence_scores_are_tracked` - Validates OCR confidence score tracking
- ✅ `test_ocr_content_appears_in_search_and_qa_responses` - Validates OCR content is searchable and quotable
- ✅ `test_visual_content_thumbnails_for_ocr_generated_content` - Validates thumbnail generation for visual content

### T080 - Quota Limit Tests (`test_quota_limit.py`)
Tests account quota enforcement and management:
- ✅ `test_document_upload_returns_429_when_account_at_200_docs` - Validates 429 response at quota limit
- ✅ `test_quota_validation_before_processing_starts` - Validates quota check before processing begins
- ✅ `test_quota_error_message_indicates_current_max_document_counts` - Validates error message details
- ✅ `test_quota_enforcement_per_account_api_key_isolation` - Validates per-account quota isolation
- ✅ `test_quota_resets_after_document_deletion` - Validates quota count decreases after deletion
- ✅ `test_quota_validation_with_idempotency_key` - Validates idempotency behavior with quota
- ✅ `test_quota_near_limit_behavior` - Validates behavior when approaching quota limit
- ✅ `test_quota_error_includes_request_id` - Validates request tracking in quota errors

## Expected Behavior (TDD)

**These tests are designed to FAIL initially** as part of the TDD (Test-Driven Development) approach. They will fail because:

1. **OCR endpoints don't exist yet** - The API doesn't currently implement OCR processing or flag tracking
2. **Quota enforcement not implemented** - The API doesn't currently implement per-account quota limits
3. **Missing document processing features** - Background job processing, document indexing, search, and Q&A endpoints need implementation

## Running Tests

```bash
# Run OCR flag tests (will fail until implementation)
pytest tests/integration/test_ocr_flag.py -v

# Run quota limit tests (will fail until implementation)
pytest tests/integration/test_quota_limit.py -v

# Run all integration tests
pytest tests/integration/ -v -m integration
```

## Required Fixtures

These tests depend on fixtures from `tests/fixtures/`:
- `api_client.py` - HTTP client helpers and authentication
- `test_data.py` - Sample UUIDs and test data
- Additional fixtures for OCR test PDFs (scanned vs native content)

## Validation Points

### OCR Flag Tests Validate:
- `is_ocr_generated` field presence in SearchResult schema
- OCR confidence score tracking and reporting
- Thumbnail URL generation for visual content  
- Search and Q&A integration with OCR content

### Quota Limit Tests Validate:
- HTTP 429 response when quota exceeded
- Error message format per quickstart.md specification
- Account isolation (API key-based quota tracking)
- Quota management (delete documents to free quota)
- Idempotency key behavior with quota limits

## Implementation Notes

When implementing the actual features, ensure:

1. **OCR Processing**: 
   - Use ocrmypdf + Tesseract as specified in CLAUDE.md
   - Track confidence scores per document content
   - Generate thumbnails for charts/tables
   - Set `is_ocr_generated` flag based on content source

2. **Quota Management**:
   - Enforce 200 document limit per account (API key)
   - Validate quota before starting document processing  
   - Return proper error format matching quickstart.md examples
   - Update quota count after document deletion

3. **API Contract Compliance**:
   - Follow OpenAPI schema definitions exactly
   - Use UUID format for all IDs per CLAUDE.md requirements
   - Include proper error codes and request IDs
   - Maintain consistent response structures