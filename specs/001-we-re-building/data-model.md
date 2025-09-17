# Data Model: Renewable Energy PDF Processing Pipeline

**Date**: 2025-09-17  
**Feature**: Renewable Energy PDF Processing Pipeline  
**Branch**: `001-we-re-building`

## Core Entities

### 1. Account
**Purpose**: Represent API key holders with document limits and usage tracking

**Fields**:
- `account_id` (UUID, Primary Key): Unique identifier
- `api_key` (String, Unique): Authentication token, hashed
- `created_at` (DateTime): Account creation timestamp
- `document_count` (Integer): Current number of uploaded documents
- `max_documents` (Integer): Maximum allowed documents (default: 200)
- `is_active` (Boolean): Account status

**Validation Rules**:
- `document_count` must be <= `max_documents`
- `api_key` must be unique and non-empty
- `max_documents` must be > 0

**Relationships**:
- One-to-many with Document
- One-to-many with ProcessingJob

### 2. Document
**Purpose**: Represent uploaded PDF documents with metadata and processing status

**Fields**:
- `document_id` (UUID, Primary Key): Unique identifier
- `account_id` (UUID, Foreign Key): Owner account
- `filename` (String): Original filename
- `file_size` (Integer): Size in bytes
- `page_count` (Integer): Number of pages (after processing)
- `s3_key` (String): S3 object key for original PDF
- `upload_time` (DateTime): Upload timestamp
- `processing_status` (Enum): Current processing state
- `content_hash` (String): SHA-256 hash for deduplication
- `metadata` (JSON): Additional document metadata (includes optional source_url and uploaded_by fields)

**Validation Rules**:
- `file_size` must be <= 150MB (157,286,400 bytes)
- `page_count` must be <= 300 pages (when known)
- `filename` must not be empty
- `processing_status` must be valid enum value

**Processing Status Enum** (wire and DB store lowercase):
- `uploaded`: File uploaded, not yet processed
- `queued`: Processing job created and queued
- `processing`: Currently being processed
- `completed`: Successfully processed and indexed
- `failed`: Processing failed with error
- `deleted`: Marked for deletion

**Relationships**:
- Many-to-one with Account
- One-to-many with ProcessingJob
- One-to-many with ExtractedContent
- One-to-many with QualityMetrics

### 3. ProcessingJob
**Purpose**: Track asynchronous document processing tasks with progress and error details

**Fields**:
- `job_id` (UUID, Primary Key): Unique identifier
- `document_id` (UUID, Foreign Key): Associated document
- `account_id` (UUID, Foreign Key): Owner account
- `status` (Enum): Current job status
- `progress_percentage` (Integer): Completion percentage (0-100)
- `started_at` (DateTime): Processing start time
- `completed_at` (DateTime, Nullable): Processing completion time
- `error_message` (String, Nullable): Error details if failed
- `error_type` (Enum, Nullable): Error category
- `retry_count` (Integer): Number of retry attempts
- `worker_id` (String, Nullable): Processing worker identifier

**Validation Rules**:
- `progress_percentage` must be 0-100
- `retry_count` must be >= 0
- `completed_at` must be after `started_at` when present

**Job Status Enum** (wire and DB store lowercase):
- `pending`: Waiting to be processed
- `running`: Currently processing
- `completed`: Successfully completed
- `failed`: Failed with error
- `retrying`: Failed but will retry

**Error Type Enum** (wire and DB store lowercase):
- `validation_error`: Invalid PDF or constraints violation
- `processing_error`: OCR or extraction failure
- `storage_error`: S3 or database operation failure
- `quota_exceeded`: Account limits exceeded
- `system_error`: Unexpected system failure

**Relationships**:
- Many-to-one with Document
- Many-to-one with Account

### 4. ExtractedContent
**Purpose**: Represent chunks of content extracted from documents with vector embeddings

**Fields**:
- `content_id` (UUID, Primary Key): Unique identifier
- `document_id` (UUID, Foreign Key): Source document
- `page_number` (Integer): Page location in document
- `content_type` (Enum): Type of extracted content
- `text_content` (Text): Extracted text content
- `metadata` (JSON): Content-specific metadata
- `vector_embedding` (Vector): Semantic embedding for search
- `bounding_box` (JSON, Nullable): Coordinates in source page
- `confidence_score` (Float): Extraction confidence (0.0-1.0)
- `is_ocr_generated` (Boolean): Whether content came from OCR
- `extracted_at` (DateTime): Extraction timestamp

**Validation Rules**:
- `page_number` must be > 0
- `confidence_score` must be 0.0-1.0
- `text_content` must not be empty
- `content_type` must be valid enum value

**Content Type Enum** (wire and DB store lowercase):
- `text`: Plain text paragraph or section
- `table`: Structured tabular data
- `chart`: Chart or graph with description
- `image`: Image with caption or description
- `title`: Document or section title
- `metadata`: Document metadata (dates, authors, etc.)

**Metadata Structure (JSON)**:
- For TABLE: `{"headers": [...], "rows": [...], "table_type": "..."}`
- For CHART: `{"chart_type": "...", "axes": {...}, "data_series": [...]}`
- For IMAGE: `{"image_type": "...", "caption": "...", "s3_key": "..."}`
- For TEXT: `{"section_type": "...", "language": "...", "entities": [...]}`

**Relationships**:
- Many-to-one with Document
- One-to-many with Citation

### 5. Citation
**Purpose**: Link query responses to specific content sources with page references

**Fields**:
- `citation_id` (UUID, Primary Key): Unique identifier
- `content_id` (UUID, Foreign Key): Referenced content
- `document_id` (UUID, Foreign Key): Source document (denormalized)
- `page_number` (Integer): Page reference (denormalized)
- `relevance_score` (Float): Relevance to query (0.0-1.0)
- `snippet` (Text): Highlighted content snippet
- `context` (Text, Nullable): Surrounding context
- `created_at` (DateTime): Citation creation time

**Validation Rules**:
- `relevance_score` must be 0.0-1.0
- `snippet` must not be empty
- `page_number` must be > 0

**Relationships**:
- Many-to-one with ExtractedContent
- Many-to-one with Document

### 6. QualityMetrics
**Purpose**: Track quality metrics for documents to ensure SLA compliance

**Fields**:
- `metric_id` (UUID, Primary Key): Unique identifier
- `document_id` (UUID, Foreign Key): Associated document
- `pages_with_anchors` (Integer): Pages with successful anchoring
- `total_pages` (Integer): Total pages in document
- `tables_extracted` (Integer): Number of tables extracted
- `tables_detected` (Integer): Number of tables detected
- `citations_correct` (Integer): Number of correct citations
- `citations_total` (Integer): Total citations generated
- `ocr_confidence_avg` (Float): Average OCR confidence
- `processing_time_seconds` (Integer): Total processing time
- `measured_at` (DateTime): Metrics measurement time

**Validation Rules**:
- `pages_with_anchors` <= `total_pages`
- `tables_extracted` <= `tables_detected`
- `citations_correct` <= `citations_total`
- `ocr_confidence_avg` must be 0.0-1.0 when present
- All counts must be >= 0

**Computed Properties**:
- `anchor_success_rate` = `pages_with_anchors` / `total_pages`
- `table_extraction_rate` = `tables_extracted` / `tables_detected`
- `citation_accuracy_rate` = `citations_correct` / `citations_total`

**SLA Thresholds**:
- Anchor success rate >= 95%
- Table extraction rate >= 90%
- Citation accuracy rate >= 95%

**Relationships**:
- Many-to-one with Document

## State Transitions

### Document Processing Flow
```
uploaded -> queued -> processing -> [completed | failed]
                                 |
                                 v
                              failed -> deleted (demo = immediate hard delete)
```

### Job Processing Flow
```
pending -> running -> [completed | failed]
                   |
                   v
               retrying -> running
```

## Storage Strategy

### Relational Database (PostgreSQL)
- Account, Document, ProcessingJob, QualityMetrics tables
- ACID transactions for data consistency
- Foreign key constraints for referential integrity

### Vector Database (Qdrant)
- ExtractedContent with embeddings for similarity search
- Rich payload metadata for filtering
- Collections organized by account for isolation

### Object Storage (S3)
- Original PDF files: `{account_id}/{document_id}/original.pdf`
- Extracted images: `{account_id}/{document_id}/images/{content_id}.{ext}`
- Processing artifacts: `{account_id}/{document_id}/artifacts/`

### Citation Storage
- Citations stored relationally for audit trail
- Cached in application layer for performance
- Generated on-demand from content matches

## Indexing Strategy

### Database Indexes
- `documents(account_id, processing_status)` for status queries
- `processing_jobs(document_id, status)` for job tracking
- `extracted_content(document_id, page_number)` for page queries
- `quality_metrics(document_id)` for SLA monitoring

### Vector Database Collections
- Collection per account: `account_{account_id}` (optional for demo; single-tenant acceptable)
- Payload filters: document_id, content_type, page_number, confidence_score
- Embedding dimensions: 384 (sentence-transformers default)

## Data Retention and Cleanup

### Document Deletion Process
1. Set Document status=deleted for audit messaging
2. Immediate hard delete of S3 objects (original PDF + extracted assets)
3. Immediate hard delete of vector embeddings from Qdrant
4. Immediate hard delete of content and embeddings from database
5. Retain audit-only identifiers and timestamps for traceability

### Temporary Data Cleanup
- Failed job artifacts cleaned after 7 days
- Processing logs rotated after 30 days
- Metrics aggregated and detailed records archived after 90 days

## Security Considerations

### Data Encryption
- Database: Encryption at rest via AWS RDS
- S3: Server-side encryption with KMS keys
- Vector DB: TLS encryption in transit

### Access Control
- API keys with account-level isolation
- IAM roles with least-privilege access
- Database connection pooling with role-based access

### Data Privacy
- No PII logging in application logs
- Document content encrypted in vector payloads
- Audit trail for all data access operations