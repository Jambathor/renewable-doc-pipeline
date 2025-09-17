# Research: Renewable Energy PDF Processing Pipeline

**Date**: 2025-09-17  
**Feature**: Renewable Energy PDF Processing Pipeline  
**Branch**: `001-we-re-building`

## Research Topics

### 1. LlamaIndex Multimodal Pipeline Architecture

**Decision**: LlamaIndex as the primary parsing/extraction/indexing framework  
**Rationale**: 
- Batteries-included multimodal document processing (text, tables, images, charts)
- Built-in chunking strategies and embedding generation
- Native support for page anchoring and citation tracking
- Strong integration with vector databases like Qdrant
- Reduces custom glue code for document processing workflows

**Alternatives considered**:
- Custom solution with PyPDF2/pymupdf + manual table extraction + separate OCR
- Unstructured.io + separate indexing pipeline
- Apache Tika + custom processing pipeline

**Implementation approach**:
- Use LlamaIndex document loaders for PDF ingestion
- Configure multimodal parsing with table extraction and image detection
- Implement custom metadata extraction for renewable energy domain specifics
- Leverage built-in vector store integration for Qdrant

### 2. OCR Strategy: ocrmypdf + Tesseract vs AWS Textract

**Decision**: ocrmypdf + Tesseract as default, AWS Textract via feature flag  
**Rationale**:
- ocrmypdf is container-friendly and has zero external API dependencies
- Tesseract provides good enough quality for demo purposes
- Self-contained approach reduces complexity and external costs
- AWS Textract kept as optional upgrade path for production quality/scale

**Alternatives considered**:
- AWS Textract only (high API costs, external dependency)
- Google Cloud Document AI (vendor lock-in concerns)
- Azure Form Recognizer (less mature ecosystem)

**Implementation approach**:
- Default OCR pipeline: ocrmypdf preprocessing → LlamaIndex PDF loader
- Feature flag: `USE_TEXTRACT=true` switches to AWS Textract integration
- OCR confidence scores and provenance flags in metadata
- Fallback handling for OCR failures

### 3. Asynchronous Processing Architecture

**Decision**: In-process background tasks (demo default); SQS/ECS worker optional for future  
**Rationale**:
- In-process tasks provide async processing without external dependencies for demo
- Simplifies deployment and reduces infrastructure overhead
- SQS/ECS scaling path available when processing volume increases
- Clear separation maintained: API handles requests, background tasks process documents

**Alternatives considered**:
- Amazon SQS + ECS Fargate workers (future scaling option)
- Celery + Redis (requires managing Redis infrastructure)
- AWS Lambda (150MB/15min limits problematic for large PDFs)
- Synchronous processing (poor user experience for large documents)

**Implementation approach**:
- API service: FastAPI receives uploads, starts background tasks, tracks status
- Background tasks: In-process processing with LlamaIndex for demo
- Job status tracking via database with progress updates
- Error handling and retry logic for processing failures
- SQS/ECS worker path available for future production scaling

### 4. Vector Database: Qdrant Configuration

**Decision**: Qdrant hosted on AWS with rich payload metadata  
**Rationale**:
- Native support for payload-based filtering (essential for multi-tenant/multi-document)
- Strong Python SDK with async support
- Easy to deploy and manage on AWS infrastructure
- Good performance for similarity search at demo scale

**Alternatives considered**:
- Pinecone (SaaS costs, less control over infrastructure)
- Weaviate (more complex setup, GraphQL overhead)
- PostgreSQL with pgvector (limited vector search capabilities)

**Implementation approach**:
- Collections organized by account/document for isolation (optional for demo; single-tenant acceptable)
- Rich metadata in payloads: doc_id, page, content_type, bbox, confidence, ocr_flag
- Hybrid search combining vector similarity and metadata filters
- Embedding strategy: sentence transformers via LlamaIndex

### 5. AWS Infrastructure Pattern

**Decision**: Minimal Terraform (single ECS service or App Runner) + ECR; ALB only if ECS  
**Rationale**:
- Single service simplifies deployment and reduces infrastructure overhead
- ECS or App Runner both provide serverless container hosting
- ECR provides secure image registry with vulnerability scanning
- ALB only needed for ECS; App Runner includes built-in load balancing
- Scales to zero when not in use (cost-effective for demo)

**Alternatives considered**:
- Multi-service architecture with VPC/Cloud Map (future scaling option)
- EKS (overkill for single-service demo)
- EC2 Auto Scaling Groups (requires instance management)
- AWS Lambda (payload and timeout limitations)

**Implementation approach**:
- Single service: API with in-process background tasks
- ECS Fargate option: single service + ALB + security group
- App Runner option: single service with built-in scaling
- Multi-service VPC architecture available for future scaling

### 6. Observability Stack

**Decision**: Single /metrics endpoint + Prometheus + Grafana (docker-compose locally); simple Grafana alert  
**Rationale**:
- Single /metrics endpoint provides essential metrics without complexity
- Prometheus + Grafana via docker-compose for local development
- Simple Grafana alert on processing success rate sufficient for demo
- OpenTelemetry and CloudWatch available for future production scaling

**Alternatives considered**:
- Full OpenTelemetry + CloudWatch stack (future production option)
- AWS X-Ray only (vendor lock-in, limited customization)
- Datadog/New Relic (high costs for demo usage)
- ELK stack (complex setup and management)

**Implementation approach**:
- Single /metrics endpoint exposing processing success rate, extraction coverage
- Prometheus scraping metrics endpoint locally via docker-compose
- Simple Grafana dashboard with basic alert on processing failures
- OpenTelemetry SDK optional for future distributed tracing needs

### 7. Infrastructure as Code: Terraform

**Decision**: Minimal single-root Terraform for demo; modular split optional later  
**Rationale**:
- Single Terraform root simplifies demo deployment and reduces complexity
- Reproducible infrastructure deployments with minimal moving parts
- Version control for infrastructure changes
- Easy environment teardown/recreation for demo
- Modular architecture available when scaling to multi-service production

**Alternatives considered**:
- Modular Terraform architecture (future scaling option for production)
- AWS CloudFormation (vendor lock-in, complex syntax)
- CDK (requires TypeScript/Python expertise)
- Manual AWS Console (not reproducible, error-prone)

**Implementation approach**:
- Single Terraform root with locals and variables for demo
- Separate environments (dev/staging/prod) with variable overrides
- State management via S3 backend with DynamoDB locking
- GitHub Actions integration for automated deployments
- Modular split (VPC, ECS, storage, IAM, monitoring) available for future scaling

## Quality Assurance Strategy

### Page Anchoring (≥95% requirement)
- LlamaIndex page tracking during document ingestion
- Metadata preservation through chunking process
- Validation during indexing to ensure page references
- Quality metrics tracking in monitoring dashboards

### Table Extraction (≥90% requirement)
- LlamaIndex table detection and extraction capabilities
- Confidence scoring for extracted tables
- Manual validation dataset for quality assessment
- Fallback handling for complex table structures

### Citation Correctness (≥95% requirement)
- Structured citation metadata in vector store payloads
- Template-based citation formatting
- Integration tests validating citation accuracy
- User feedback collection for citation quality

## Security Considerations

### API Key Authentication
- Account-scoped API keys with document limits
- Request validation and rate limiting
- HTTPS-only communication
- API key rotation capabilities

### Data Privacy
- No sensitive data logging in observability stack
- Encryption at rest for S3 storage
- VPC isolation for processing services
- IAM least-privilege access policies

## Performance Optimization

### Document Processing
- Parallel processing for independent PDF pages
- Efficient memory management for large documents
- Streaming upload/download for S3 interactions
- Connection pooling for database and vector store

### API Response Times
- Asynchronous processing for upload endpoints
- Caching for frequently accessed metadata
- Optimized vector search with appropriate indexing
- CDN integration for static asset delivery

## Demo Constraints Implementation

### Resource Limits
- Account-level document limits (200 PDFs max)
- File size validation (≤150MB)
- Page count validation (≤300 pages)
- Processing timeout handling

### Error Handling
- Clear error messages for validation failures
- Graceful degradation for processing issues
- User-friendly refinement hints for search
- Comprehensive error logging for debugging
