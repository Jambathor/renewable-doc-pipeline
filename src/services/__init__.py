"""
Business logic services for renewable energy PDF processing pipeline.

This package contains the core business logic services that implement
the document processing workflow:

Services:
    AccountService: API key authentication and quota management
    DocumentService: PDF processing with LlamaIndex integration
    SearchService: Hybrid vector/semantic search with Qdrant
    QAService: Question answering with evidence grounding
    TaskRunner: Background task processing for async operations

The services layer orchestrates interactions between models, storage,
and external processing tools while maintaining proper separation of concerns.
"""

from .account_service import AccountService, AccountError
from .document_service import DocumentService, DocumentProcessingError  
from .search_service import SearchService, SearchError, SearchFilters, SearchResults
from .qa_service import QAService, QAServiceError, QAResponse
from .task_runner import BackgroundTaskRunner, get_task_runner, schedule_document_processing

__all__ = [
    "AccountService",
    "AccountError", 
    "DocumentService",
    "DocumentProcessingError",
    "SearchService", 
    "SearchError",
    "SearchFilters",
    "SearchResults",
    "QAService",
    "QAServiceError", 
    "QAResponse",
    "BackgroundTaskRunner",
    "get_task_runner",
    "schedule_document_processing",
]