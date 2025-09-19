"""Account model for renewable energy PDF processing pipeline.

This module defines the Account Pydantic model representing API key holders
with document limits and usage tracking.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Account(BaseModel):
    """Account model representing API key holders with document limits and usage tracking.

    Attributes:
        account_id: Unique identifier for the account
        api_key: Authentication token, must be unique and non-empty
        created_at: Account creation timestamp
        document_count: Current number of uploaded documents
        max_documents: Maximum allowed documents (default: 200)
        is_active: Account status indicating if account is active
    """

    account_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the account"
    )

    api_key: str = Field(
        ...,
        min_length=1,
        description="Authentication token, must be unique and non-empty",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Account creation timestamp"
    )

    document_count: int = Field(
        default=0, ge=0, description="Current number of uploaded documents"
    )

    max_documents: int = Field(
        default=200, gt=0, description="Maximum allowed documents"
    )

    is_active: bool = Field(
        default=True, description="Account status indicating if account is active"
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that api_key is non-empty.

        Args:
            v: The api_key value to validate

        Returns:
            The validated api_key

        Raises:
            ValueError: If api_key is empty or only whitespace
        """
        if not v or not v.strip():
            raise ValueError("api_key must be non-empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_document_limits(self) -> "Account":
        """Validate that document_count does not exceed max_documents.

        Returns:
            The validated Account instance

        Raises:
            ValueError: If document_count exceeds max_documents
        """
        if self.document_count > self.max_documents:
            raise ValueError(
                f"document_count ({self.document_count}) must be <= "
                f"max_documents ({self.max_documents})"
            )
        return self

    class Config:
        """Pydantic model configuration."""

        # Allow usage of UUID types
        arbitrary_types_allowed = True

        # Validate assignments after initial creation
        validate_assignment = True

        # Use enum values in serialization
        use_enum_values = True

        # JSON schema extra configuration
        json_schema_extra = {
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "api_key": "ak_1234567890abcdef",
                "created_at": "2025-09-17T10:30:00Z",
                "document_count": 5,
                "max_documents": 200,
                "is_active": True,
            }
        }
