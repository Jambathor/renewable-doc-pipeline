"""
UUID generation and validation helpers for renewable energy pipeline tests.

Provides utilities for generating valid UUIDs, validating UUID formats,
and managing UUID-based test data as required by the CLAUDE.md guidelines.
"""

import uuid
from typing import Dict, List, Set
from uuid import UUID

import pytest


@pytest.fixture
def uuid_generator():
    """UUID generation helper for tests."""
    class UUIDGenerator:
        """Helper class for generating and managing test UUIDs."""
        
        def __init__(self):
            self._generated_uuids: Set[str] = set()
        
        def generate(self) -> str:
            """Generate a new UUID4 string."""
            new_uuid = str(uuid.uuid4())
            self._generated_uuids.add(new_uuid)
            return new_uuid
        
        def generate_multiple(self, count: int) -> List[str]:
            """Generate multiple unique UUIDs."""
            return [self.generate() for _ in range(count)]
        
        def generate_batch(self, names: List[str]) -> Dict[str, str]:
            """Generate a batch of UUIDs with descriptive names."""
            return {name: self.generate() for name in names}
        
        def is_valid_uuid(self, uuid_string: str) -> bool:
            """Validate UUID format."""
            try:
                UUID(uuid_string)
                return True
            except (ValueError, TypeError):
                return False
        
        def assert_valid_uuid(self, uuid_string: str) -> None:
            """Assert that a string is a valid UUID format."""
            if not self.is_valid_uuid(uuid_string):
                pytest.fail(f"Invalid UUID format: {uuid_string}")
        
        def assert_valid_uuids(self, uuid_list: List[str]) -> None:
            """Assert that all strings in list are valid UUIDs."""
            for uuid_string in uuid_list:
                self.assert_valid_uuid(uuid_string)
        
        def get_generated_uuids(self) -> Set[str]:
            """Get all UUIDs generated in this session."""
            return self._generated_uuids.copy()
        
        def clear_generated(self) -> None:
            """Clear the generated UUIDs tracking."""
            self._generated_uuids.clear()
    
    return UUIDGenerator()


@pytest.fixture
def test_uuids() -> Dict[str, str]:
    """Pre-generated UUIDs for consistent testing."""
    return {
        # Document IDs
        "document_1": "550e8400-e29b-41d4-a716-446655440000",
        "document_2": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "document_3": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
        "document_4": "12345678-1234-5678-9012-123456789012",
        "document_5": "87654321-4321-8765-2109-876543210987",
        
        # Job IDs
        "job_1": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "job_2": "6ba7b812-9dad-11d1-80b4-00c04fd430c8",
        "job_3": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "job_4": "fedcba09-8765-4321-0987-654321fedcba",
        "job_5": "11111111-2222-3333-4444-555555555555",
        
        # Content IDs
        "content_1": "01234567-89ab-cdef-0123-456789abcdef",
        "content_2": "98765432-10fe-dcba-9876-543210fedcba",
        "content_3": "11111111-2222-3333-4444-555555555555",
        "content_4": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "content_5": "ffffffff-0000-1111-2222-333333333333",
        
        # Idempotency keys
        "idempotency_1": "12345678-abcd-1234-abcd-123456789012",
        "idempotency_2": "87654321-dcba-4321-dcba-987654321098",
        "idempotency_3": "abcdef01-2345-6789-abcd-ef0123456789",
        
        # Request IDs
        "request_1": "req_01HXZ9K7N8P2Q3R4S5T6U7V8W9",
        "request_2": "req_02HYA0L8O9Q3R4S5T6U7V8W9X0",
        "request_3": "req_03HZB1M9P0R4S5T6U7V8W9X0Y1",
    }


@pytest.fixture
def document_uuids(test_uuids: Dict[str, str]) -> Dict[str, str]:
    """Document-specific UUIDs for testing."""
    return {
        key: value for key, value in test_uuids.items()
        if key.startswith("document_")
    }


@pytest.fixture
def job_uuids(test_uuids: Dict[str, str]) -> Dict[str, str]:
    """Job-specific UUIDs for testing."""
    return {
        key: value for key, value in test_uuids.items()
        if key.startswith("job_")
    }


@pytest.fixture
def content_uuids(test_uuids: Dict[str, str]) -> Dict[str, str]:
    """Content-specific UUIDs for testing."""
    return {
        key: value for key, value in test_uuids.items()
        if key.startswith("content_")
    }


@pytest.fixture
def idempotency_uuids(test_uuids: Dict[str, str]) -> Dict[str, str]:
    """Idempotency key UUIDs for testing."""
    return {
        key: value for key, value in test_uuids.items()
        if key.startswith("idempotency_")
    }


class UUIDTestHelper:
    """Helper class for UUID-related test operations."""
    
    @staticmethod
    def generate_document_uuid() -> str:
        """Generate a UUID for document testing."""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_job_uuid() -> str:
        """Generate a UUID for job testing."""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_content_uuid() -> str:
        """Generate a UUID for content testing."""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_idempotency_key() -> str:
        """Generate a UUID for idempotency key testing."""
        return str(uuid.uuid4())
    
    @staticmethod
    def is_valid_uuid_format(uuid_string: str) -> bool:
        """Check if string matches UUID format."""
        try:
            UUID(uuid_string, version=4)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def assert_uuid_format(uuid_string: str, context: str = "") -> None:
        """Assert that string is valid UUID format."""
        try:
            UUID(uuid_string)
        except (ValueError, TypeError):
            context_msg = f" (context: {context})" if context else ""
            pytest.fail(f"Invalid UUID format: {uuid_string}{context_msg}")
    
    @staticmethod
    def assert_all_uuid_format(uuid_list: List[str], context: str = "") -> None:
        """Assert that all strings in list are valid UUID format."""
        for i, uuid_string in enumerate(uuid_list):
            item_context = f"{context}[{i}]" if context else f"item {i}"
            UUIDTestHelper.assert_uuid_format(uuid_string, item_context)
    
    @staticmethod
    def validate_uuid_fields(data: Dict, uuid_fields: List[str]) -> None:
        """Validate that specified fields contain valid UUIDs."""
        for field in uuid_fields:
            if field in data:
                UUIDTestHelper.assert_uuid_format(data[field], f"field '{field}'")
            else:
                pytest.fail(f"Required UUID field '{field}' missing from data")
    
    @staticmethod
    def create_test_document_data(document_id: str = None, job_id: str = None) -> Dict[str, str]:
        """Create test document data with proper UUID format."""
        return {
            "document_id": document_id or UUIDTestHelper.generate_document_uuid(),
            "job_id": job_id or UUIDTestHelper.generate_job_uuid(),
        }
    
    @staticmethod
    def create_test_search_result(
        content_id: str = None,
        document_id: str = None
    ) -> Dict[str, str]:
        """Create test search result with proper UUID format."""
        return {
            "content_id": content_id or UUIDTestHelper.generate_content_uuid(),
            "document_id": document_id or UUIDTestHelper.generate_document_uuid(),
        }


@pytest.fixture
def uuid_helper() -> UUIDTestHelper:
    """UUID test helper instance."""
    return UUIDTestHelper()


# UUID validation fixtures for common patterns

@pytest.fixture
def uuid_validator():
    """UUID validation helper function."""
    def validate(uuid_string: str, context: str = "") -> None:
        """Validate UUID format with optional context."""
        UUIDTestHelper.assert_uuid_format(uuid_string, context)
    
    return validate


@pytest.fixture
def uuid_list_validator():
    """UUID list validation helper function."""
    def validate(uuid_list: List[str], context: str = "") -> None:
        """Validate list of UUIDs with optional context."""
        UUIDTestHelper.assert_all_uuid_format(uuid_list, context)
    
    return validate


@pytest.fixture
def response_uuid_validator():
    """Helper for validating UUIDs in API responses."""
    def validate(response_data: Dict, uuid_fields: List[str]) -> None:
        """Validate UUID fields in API response data."""
        UUIDTestHelper.validate_uuid_fields(response_data, uuid_fields)
    
    return validate


# Specialized UUID fixtures for different entity types

@pytest.fixture
def solar_document_uuids() -> Dict[str, str]:
    """UUIDs for solar energy document testing."""
    return {
        "solar_efficiency_report": "550e8400-e29b-41d4-a716-446655440001",
        "solar_panel_analysis": "550e8400-e29b-41d4-a716-446655440002",
        "solar_installation_guide": "550e8400-e29b-41d4-a716-446655440003",
    }


@pytest.fixture
def wind_document_uuids() -> Dict[str, str]:
    """UUIDs for wind energy document testing."""
    return {
        "wind_turbine_report": "6ba7b810-9dad-11d1-80b4-00c04fd430c1",
        "wind_efficiency_study": "6ba7b810-9dad-11d1-80b4-00c04fd430c2", 
        "wind_farm_analysis": "6ba7b810-9dad-11d1-80b4-00c04fd430c3",
    }


@pytest.fixture
def processing_job_uuids() -> Dict[str, str]:
    """UUIDs for processing job testing."""
    return {
        "ocr_job": "f47ac10b-58cc-4372-a567-0e02b2c3d470",
        "indexing_job": "f47ac10b-58cc-4372-a567-0e02b2c3d471",
        "embedding_job": "f47ac10b-58cc-4372-a567-0e02b2c3d472",
        "validation_job": "f47ac10b-58cc-4372-a567-0e02b2c3d473",
    }


# Mock data with proper UUIDs

@pytest.fixture
def mock_document_response_with_uuids(test_uuids: Dict[str, str]) -> Dict:
    """Mock document response with proper UUID formatting."""
    return {
        "document_id": test_uuids["document_1"],
        "job_id": test_uuids["job_1"],
        "filename": "renewable_energy_report.pdf",
        "file_size": 2457600,
        "status": "uploaded",
        "upload_time": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def mock_search_results_with_uuids(test_uuids: Dict[str, str]) -> Dict:
    """Mock search results with proper UUID formatting."""
    return {
        "query": "solar efficiency",
        "total_results": 2,
        "results": [
            {
                "content_id": test_uuids["content_1"],
                "document_id": test_uuids["document_1"],
                "document_title": "Solar Efficiency Report",
                "page_number": 15,
                "content_type": "text",
                "snippet": "Solar panel efficiency improvements",
                "confidence_score": 0.95,
                "relevance_score": 0.88,
                "is_ocr_generated": False,
            },
            {
                "content_id": test_uuids["content_2"],
                "document_id": test_uuids["document_2"], 
                "document_title": "Renewable Energy Analysis",
                "page_number": 8,
                "content_type": "chart",
                "snippet": "Efficiency comparison chart",
                "confidence_score": 0.87,
                "relevance_score": 0.82,
                "is_ocr_generated": True,
            },
        ],
    }