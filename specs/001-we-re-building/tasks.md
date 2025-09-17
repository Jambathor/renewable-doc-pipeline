# Tasks: Renewable Energy PDF Processing Pipeline

**Input**: Design documents from `/specs/001-we-re-building/`
**Prerequisites**: research.md, data-model.md, contracts/openapi.yaml, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract: FastAPI + Pydantic v2, LlamaIndex, OCR pipeline, Qdrant, S3
2. Load design documents:
   → data-model.md: 6 entities → model tasks
   → contracts/openapi.yaml: 8 endpoints → contract test tasks
   → quickstart.md: Integration scenarios → integration test tasks
   → research.md: Infrastructure decisions → setup tasks
3. Generate tasks by category:
   → Setup: Python project, deps, Terraform, docker-compose, CI
   → Tests: 8 contract tests, 9 integration tests
   → Core: 6 models, 4 services, 8 endpoints
   → Integration: DB, auth, error handling, metrics
   → Polish: unit tests, performance, quality checks
4. Apply TDD: All tests before implementation
5. Number tasks sequentially (T001-T091)
6. Mark [P] for different files only
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Phase 3.1: Setup

- [ ] T001 Create project structure: src/{models,services,api,storage,ocr,monitoring,config}, tests/{contract,integration,unit,fixtures}, infrastructure/{terraform,monitoring}, docker/
- [ ] T002 Initialize Python 3.11 project with requirements.txt and requirements-dev.txt
- [ ] T003 [P] Configure ruff, mypy, black in pyproject.toml
- [ ] T004 [P] Set up pytest configuration in pytest.ini
- [ ] T005 [P] Create minimal Terraform single-root in infrastructure/terraform/main.tf with ECS/App Runner + S3 + ECR
- [ ] T006 [P] Docker Compose for local observability in infrastructure/monitoring/docker-compose.yml (Postgres, Qdrant, Prometheus, Grafana)
- [ ] T007 [P] GitHub Actions CI workflow in .github/workflows/ci.yml
- [ ] T008 [P] Dockerfile for API service in docker/Dockerfile.api
- [ ] T081 [P] Environment configuration with STORAGE_BACKEND toggle in src/config/settings.py
- [ ] T083 [P] Local storage fixtures and test configuration in tests/fixtures/storage_fixtures.py

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (OpenAPI Validation)
- [ ] T009 [P] Contract test POST /documents in tests/contract/test_documents_post.py
- [ ] T010 [P] Contract test GET /jobs/{job_id} in tests/contract/test_jobs_get.py
- [ ] T011 [P] Contract test GET /search in tests/contract/test_search_get.py
- [ ] T012 [P] Contract test POST /qa in tests/contract/test_qa_post.py
- [ ] T013 [P] Contract test GET /documents/{document_id} in tests/contract/test_documents_get.py
- [ ] T014 [P] Contract test DELETE /documents/{document_id} in tests/contract/test_documents_delete.py
- [ ] T015 [P] Contract test GET /healthz in tests/contract/test_health_get.py
- [ ] T016 [P] Contract test GET /metrics in tests/contract/test_metrics_get.py

### Integration Tests (Quickstart Scenarios)
- [ ] T017 [P] Integration test upload→status→search→QA→delete flow in tests/integration/test_quickstart_flow.py
- [ ] T018 [P] Integration test rate limiting on /search and /qa (429 errors) in tests/integration/test_rate_limits.py
- [ ] T019 [P] Integration test Idempotency-Key and content_hash deduplication on POST /documents in tests/integration/test_idempotency.py
- [ ] T020 [P] Integration test immediate hard delete with 202 response in tests/integration/test_deletion.py
- [ ] T021 [P] Integration test /metrics auth (401 outside local) in tests/integration/test_metrics_auth.py
- [ ] T077 [P] Integration test /qa returns 200 "No evidence found" when no docs match in tests/integration/test_no_evidence.py
- [ ] T078 [P] Integration test upload errors 413/415/422 for file validation in tests/integration/test_upload_errors.py
- [ ] T079 [P] Integration test scanned PDF yields "is_ocr_generated": true in tests/integration/test_ocr_flag.py
- [ ] T080 [P] Integration test POST /documents returns 429 when account at 200 docs in tests/integration/test_quota_limit.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models (Pydantic v2)
- [ ] T022 [P] Account model in src/models/account.py
- [ ] T023 [P] Document model in src/models/document.py
- [ ] T024 [P] ProcessingJob model in src/models/processing_job.py
- [ ] T025 [P] ExtractedContent model in src/models/extracted_content.py
- [ ] T026 [P] Citation model in src/models/citation.py
- [ ] T027 [P] QualityMetrics model in src/models/quality_metrics.py

### Storage Layer
- [ ] T028 [P] S3 storage service in src/storage/s3_client.py
- [ ] T029 [P] Qdrant vector database client in src/storage/qdrant_client.py
- [ ] T030 [P] PostgreSQL database client in src/storage/postgres_client.py
- [ ] T030a [P] Local storage backend implementation for demo tests in src/storage/local_storage.py
- [ ] T031 Database migrations for all entities in src/storage/migrations.py

### Core Services
- [ ] T032 [P] Account service with API key validation in src/services/account_service.py
- [ ] T033 [P] Document processing service with LlamaIndex integration in src/services/document_service.py
- [ ] T034 [P] OCR pipeline service with ocrmypdf + Tesseract in src/ocr/ocr_service.py
- [ ] T035 [P] Search service with Qdrant hybrid retrieval in src/services/search_service.py
- [ ] T036 [P] Question answering service with evidence grounding in src/services/qa_service.py
- [ ] T037 Background task runner for in-process async processing in src/services/task_runner.py

### API Endpoints (FastAPI)
- [ ] T038 FastAPI application setup and middleware in src/api/main.py
- [ ] T039 POST /documents endpoint with file upload validation in src/api/documents.py
- [ ] T040 GET /jobs/{job_id} endpoint for processing status in src/api/jobs.py
- [ ] T041 GET /search endpoint with hybrid retrieval in src/api/search.py
- [ ] T042 POST /qa endpoint with evidence-grounded responses in src/api/qa.py
- [ ] T043 GET /documents/{document_id} endpoint in src/api/documents.py
- [ ] T044 DELETE /documents/{document_id} endpoint with immediate hard delete in src/api/documents.py
- [ ] T045 GET /healthz endpoint (unauthenticated) in src/api/health.py
- [ ] T046 GET /metrics endpoint with X-API-Key auth in src/api/metrics.py

## Phase 3.4: Integration

- [ ] T047 Database connection and migration runner in src/storage/database.py
- [ ] T048 API key authentication middleware in src/api/auth.py
- [ ] T049 Error handling middleware with custom exceptions in src/api/errors.py
- [ ] T050 Request logging with correlation IDs in src/api/request_logging.py
- [ ] T051 Rate limiting middleware for /search and /qa endpoints in src/api/rate_limiting.py
- [ ] T052 Metrics collection and Prometheus endpoint in src/monitoring/metrics.py
- [ ] T053 Content hash deduplication logic in src/services/deduplication.py
- [ ] T054 File validation (size, type, structure) in src/services/validation.py

## Phase 3.5: Polish

### Unit Tests
- [ ] T055 [P] Unit tests for Account model validation in tests/unit/test_account_model.py
- [ ] T056 [P] Unit tests for Document processing states in tests/unit/test_document_model.py
- [ ] T057 [P] Unit tests for OCR confidence scoring in tests/unit/test_ocr_service.py
- [ ] T058 [P] Unit tests for vector search logic in tests/unit/test_search_service.py
- [ ] T059 [P] Unit tests for citation generation in tests/unit/test_qa_service.py
- [ ] T060 [P] Unit tests for file validation rules in tests/unit/test_validation.py

### Performance & Quality
- [ ] T061 [P] Performance tests for search (<500ms) in tests/performance/test_search_perf.py
- [ ] T062 [P] Performance tests for QA (<2s) in tests/performance/test_qa_perf.py
- [ ] T063 [P] Quality metrics validation (95% anchoring, 90% tables) in tests/quality/test_sla_metrics.py
- [ ] T064 [P] Load test for document upload pipeline in tests/performance/test_upload_load.py

### Infrastructure & Documentation
- [ ] T065 [P] Terraform variables and environments config in infrastructure/terraform/variables.tf
- [ ] T066 [P] Grafana dashboard configuration in infrastructure/monitoring/grafana/dashboards/
- [ ] T067 [P] GitHub Actions deployment workflow in .github/workflows/deploy.yml
- [ ] T068 Update CLAUDE.md with final commands and structure

### Final Quality Checks
- [ ] T084 Run ruff check on all Python files
- [ ] T085 Run mypy type checking on src/
- [ ] T086 Run black formatting on src/ and tests/
- [ ] T087 Verify all contract tests pass with OpenAPI spec
- [ ] T088 Verify all integration tests pass end-to-end
- [ ] T089 Manual testing following quickstart.md scenarios
- [ ] T090 Performance smoke test for processing pipeline
- [ ] T091 Terraform plan validation for deployment readiness

## Dependencies

### Phase Dependencies
- Setup (T001-T008, T081, T083) before all other phases
- Tests (T009-T021, T077-T080) before implementation (T022-T046)
- Models (T022-T027) before services (T032-T037)
- Services before endpoints (T038-T046)
- Core implementation before integration (T047-T054)
- Implementation before polish (T055-T091)

### Specific Dependencies
- T031 (migrations) blocks T047 (DB connection)
- T032 (account service) blocks T048 (auth middleware) and T080 (quota test)
- T033 (document service) blocks T037 (task runner) and T079 (OCR flag test)
- T034 (OCR service) blocks T033 (document service) and T079 (OCR flag test)
- T035 (search service) blocks T041 (search endpoint)
- T036 (QA service) blocks T042 (QA endpoint) and T077 (no evidence test)
- T052 (metrics) blocks T046 (metrics endpoint)
- T054 (file validation) blocks T078 (upload error test)

## Parallel Execution Examples

### Setup Phase (can run together)
```bash
# T003, T004, T005, T006, T007, T008 together:
Task: "Configure ruff, mypy, black in pyproject.toml"
Task: "Set up pytest configuration in pytest.ini"
Task: "Create minimal Terraform single-root in infrastructure/terraform/main.tf"
Task: "Docker Compose for local observability in infrastructure/monitoring/docker-compose.yml"
Task: "GitHub Actions CI workflow in .github/workflows/ci.yml"
Task: "Dockerfile for API service in docker/Dockerfile.api"
```

### Contract Tests Phase (all parallel)
```bash
# T009-T016 together:
Task: "Contract test POST /documents in tests/contract/test_documents_post.py"
Task: "Contract test GET /jobs/{job_id} in tests/contract/test_jobs_get.py"
Task: "Contract test GET /search in tests/contract/test_search_get.py"
Task: "Contract test POST /qa in tests/contract/test_qa_post.py"
Task: "Contract test GET /documents/{document_id} in tests/contract/test_documents_get.py"
Task: "Contract test DELETE /documents/{document_id} in tests/contract/test_documents_delete.py"
Task: "Contract test GET /healthz in tests/contract/test_health_get.py"
Task: "Contract test GET /metrics in tests/contract/test_metrics_get.py"
```

### Integration Tests Phase (all parallel)
```bash
# T017-T021 together:
Task: "Integration test upload→status→search→QA→delete flow in tests/integration/test_quickstart_flow.py"
Task: "Integration test rate limiting on /search and /qa (429 errors) in tests/integration/test_rate_limits.py"
Task: "Integration test Idempotency-Key and content_hash deduplication in tests/integration/test_idempotency.py"
Task: "Integration test immediate hard delete with 202 response in tests/integration/test_deletion.py"
Task: "Integration test /metrics auth (401 outside local) in tests/integration/test_metrics_auth.py"
```

### Additional Integration Tests (all parallel)
```bash
# T077-T080 together:
Task: "Integration test /qa returns 200 \"No evidence found\" when no docs match in tests/integration/test_no_evidence.py"
Task: "Integration test upload errors 413/415/422 for file validation in tests/integration/test_upload_errors.py"
Task: "Integration test scanned PDF yields \"is_ocr_generated\": true in tests/integration/test_ocr_flag.py"
Task: "Integration test POST /documents returns 429 when account at 200 docs in tests/integration/test_quota_limit.py"
```

### Models Phase (all parallel)
```bash
# T022-T027 together:
Task: "Account model in src/models/account.py"
Task: "Document model in src/models/document.py"
Task: "ProcessingJob model in src/models/processing_job.py"
Task: "ExtractedContent model in src/models/extracted_content.py"
Task: "Citation model in src/models/citation.py"
Task: "QualityMetrics model in src/models/quality_metrics.py"
```

### Storage Layer (T028-T030 parallel, then T031)
```bash
# T028-T030 together:
Task: "S3 storage service in src/storage/s3_client.py"
Task: "Qdrant vector database client in src/storage/qdrant_client.py"
Task: "PostgreSQL database client in src/storage/postgres_client.py"
```

## Validation Checklist

**Coverage against OpenAPI/spec/quickstart:**
- [x] All 8 endpoints have contract tests
- [x] All 6 entities have model tasks
- [x] Rate limiting tests for /search and /qa (429 semantics)
- [x] Idempotency-Key and content_hash dedup tests
- [x] Immediate hard delete with 202 response semantics
- [x] /metrics auth test (401 outside local)
- [x] Upload→status→search→QA→delete integration flow
- [x] All paths match CLAUDE.md structure
- [x] Minimal Terraform (single root, no multi-module)
- [x] In-process background tasks (no SQS)
- [x] Docker-compose for local observability

## Notes

- **[P] tasks**: Different files, no dependencies
- **Demo constraints**: Single-tenant, immediate hard delete, in-process tasks
- **TDD approach**: All tests must be written and failing before implementation
- **Quality guardrails**: 95% anchoring, 90% table extraction, 95% citation accuracy
- **File scope**: One file per task to enable granular parallel execution
- **Infrastructure scope**: Minimal Terraform, prefer App Runner over ECS complexity

## Local Storage Backend for Demo

For development and testing, the system supports a local storage backend via environment variable:
- `STORAGE_BACKEND=local` (default for tests): Uses local filesystem instead of S3
- `STORAGE_BACKEND=s3` (cloud deployment): Uses Amazon S3

Local storage keeps tests hermetic and eliminates AWS credentials requirement for demo.

## Task Acceptance Criteria

Each task includes:
1. **Exact file path** for the deliverable
2. **Clear acceptance criteria** based on contracts/data-model/quickstart
3. **Single responsibility** (one file or one change)
4. **Testable outcome** (can verify completion)
5. **Proper [P] marking** only for truly independent files