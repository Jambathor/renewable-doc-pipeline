# Renewable Doc Pipeline Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-17

## Active Technologies

**Language/Runtime**: Python 3.11  
**Primary Framework**: FastAPI + Pydantic v2  
**Document Processing**: LlamaIndex (multimodal parsing, indexing)  
**OCR**: ocrmypdf + Tesseract (default), AWS Textract (feature flag)  
**Vector Database**: Qdrant (AWS-hosted)  
**Storage**: Amazon S3  
**Async Processing**: In-process background tasks (demo); SQS/ECS worker optional for future  
**Testing**: pytest (unit/integration), contract testing  
**Infrastructure**: Minimal Terraform - single ECS service (or App Runner), ECR, security group, ALB if ECS; docker-compose for local  
**Observability**: Single /metrics endpoint; Grafana dashboard provisioning optional; alerts via single Grafana rule  
**CI/CD**: GitHub Actions

## Project Structure
```
src/
├── models/           # Pydantic data models, database schemas
├── services/         # Business logic, document processing
├── api/             # FastAPI routes, request/response handling
├── storage/         # S3 and Qdrant integrations
├── ocr/             # OCR processing pipelines
└── monitoring/      # OpenTelemetry, metrics collection

tests/
├── contract/        # API contract tests (OpenAPI validation)
├── integration/     # End-to-end workflow tests
└── unit/           # Component unit tests

infrastructure/
├── terraform/       # Minimal Terraform config (single root)
├── docker/         # Container definitions
└── monitoring/     # Grafana dashboards, Prometheus config

specs/
└── 001-we-re-building/  # Current feature documentation
```

## Commands

**Development**:
```bash
# Local development setup
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

# Run API service locally
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v
pytest tests/contract/ -v --openapi-spec specs/001-we-re-building/contracts/openapi.yaml
pytest tests/integration/ -v

# Quality checks
ruff check src/ tests/
mypy src/
black src/ tests/
```

**Infrastructure**:
```bash
# Minimal Terraform operations (single root with locals/variables)
cd infrastructure/terraform
terraform init
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"

# Docker builds
docker build -f docker/Dockerfile.api -t renewable-pipeline-api .
docker build -f docker/Dockerfile.worker -t renewable-pipeline-worker .

# Deploy to AWS
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin
docker tag renewable-pipeline-api:latest $ECR_REPO/api:latest
docker push $ECR_REPO/api:latest
```

**Monitoring**:
```bash
# Local observability stack (Postgres, Qdrant, Prometheus, Grafana)
docker-compose -f infrastructure/monitoring/docker-compose.yml up -d

# View metrics - single /metrics endpoint (requires X-API-Key in non-local environments)
curl http://localhost:8000/metrics

# Health checks (public endpoint, no auth required)
curl http://localhost:8000/healthz
```

## Code Style

**Python (PEP 8 + Black)**:
- Use type hints for all function signatures
- Pydantic models for all API request/response schemas
- Async/await for I/O operations (S3, Qdrant; SQS optional in future)
- Structured logging with correlation IDs
- Exception handling with custom error types
- Use lowercase enum values consistently (wire format and DB storage)
- All examples and tests must use UUID format for content_id fields

**FastAPI Patterns**:
```python
# Route definitions with proper type hints
@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[DocumentMetadata] = None,
    account: Account = Depends(get_current_account)
) -> DocumentUploadResponse:
    # Implementation
```

**LlamaIndex Integration**:
```python
# Document processing with metadata preservation
from llama_index import Document, VectorStoreIndex
from llama_index.node_parser import SentenceSplitter

# Multimodal parsing with page anchoring
documents = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
nodes = parser.get_nodes_from_documents(documents)
```

**Error Handling**:
```python
# Custom exception hierarchy
class PipelineError(Exception):
    error_type: str
    details: dict

class ValidationError(PipelineError):
    error_type = "validation_error"

class ProcessingError(PipelineError):
    error_type = "processing_error"
```

## Design Notes

**Demo Mode Considerations**:
- Async processing may use in-process background tasks instead of SQS
- Document deletion performs immediate hard delete while preserving API semantics
- Rate limiting on /search and /qa endpoints; clients should handle HTTP 429

**Consistency Guardrails**:
- Use lowercase enum values everywhere (wire format and DB storage)
- All examples must use UUID format for content_id fields
- Array query parameters use CSV format
- Idempotency-Key header on uploads

## Recent Changes

**001-we-re-building** (2025-09-17): Initial renewable energy PDF processing pipeline
- Added FastAPI + Pydantic v2 API foundation
- Integrated LlamaIndex for multimodal document processing
- Implemented OCR pipeline with ocrmypdf + Tesseract
- Set up Qdrant vector database for embeddings
- Configured minimal Terraform deployment approach
- Added single /metrics endpoint with basic observability
- Created comprehensive API contracts and data models

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->