"""Account service for renewable energy PDF processing pipeline.

Provides account management, API key authentication, and quota enforcement
with PostgreSQL storage backend. Handles API key hashing, database operations,
and document count tracking for account limits.
"""

import hashlib
import logging
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from ..models.account import Account
from ..storage.postgres_client import (
    DatabaseError,
    NotFoundError,
    ValidationError,
    get_postgres_client,
)

logger = logging.getLogger(__name__)


class AccountError(Exception):
    """Base exception for account service operations."""
    
    def __init__(self, message: str, error_type: str = "account_error", details: Optional[dict] = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(AccountError):
    """Exception raised when API key authentication fails."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "authentication_error", details)


class QuotaExceededError(AccountError):
    """Exception raised when document quota is exceeded."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "quota_exceeded_error", details)


class AccountNotFoundError(AccountError):
    """Exception raised when account is not found."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "account_not_found_error", details)


class AccountService:
    """
    Account service providing authentication and quota management.
    
    Handles API key validation, account CRUD operations, and document
    count tracking with PostgreSQL storage backend.
    """
    
    def __init__(self):
        """Initialize account service."""
        self.table_name = "accounts"
    
    def _hash_api_key(self, api_key: str) -> str:
        """
        Hash API key using SHA-256 for secure storage.
        
        Args:
            api_key: Raw API key to hash
            
        Returns:
            Hexadecimal hash of the API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _generate_api_key(self) -> str:
        """
        Generate a secure random API key.
        
        Returns:
            New API key with 'ak_' prefix followed by 32 random hex characters
        """
        return f"ak_{secrets.token_hex(32)}"
    
    async def validate_api_key(self, api_key: str) -> Optional[Account]:
        """
        Validate API key and return associated account.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Account instance if valid, None if invalid
            
        Raises:
            AuthenticationError: If validation fails due to system error
        """
        if not api_key or not api_key.strip():
            logger.warning("Empty API key provided for validation")
            return None
        
        try:
            api_key_hash = self._hash_api_key(api_key.strip())
            client = await get_postgres_client()
            
            query = """
                SELECT account_id, api_key, created_at, document_count, max_documents, is_active
                FROM accounts 
                WHERE api_key_hash = $1 AND is_active = TRUE
            """
            
            results = await client.execute_query(query, (api_key_hash,))
            
            if not results:
                logger.info("API key validation failed: key not found or account inactive",
                           extra={"api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else api_key})
                return None
            
            account_data = results[0]
            account = Account(
                account_id=account_data["account_id"],
                api_key=api_key,  # Return original key, not hash
                created_at=account_data["created_at"],
                document_count=account_data["document_count"],
                max_documents=account_data["max_documents"],
                is_active=account_data["is_active"]
            )
            
            logger.info("API key validation successful",
                       extra={"account_id": str(account.account_id)})
            return account
            
        except DatabaseError as e:
            logger.error(f"Database error during API key validation: {e.message}",
                        extra={"error_type": e.error_type, "details": e.details})
            raise AuthenticationError(f"Authentication system error: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error during API key validation: {e}")
            raise AuthenticationError(f"Authentication system error: {e}")
    
    async def create_account(self, api_key: Optional[str] = None, max_documents: int = 200) -> Account:
        """
        Create a new account with API key.
        
        Args:
            api_key: Custom API key (auto-generated if None)
            max_documents: Maximum document limit for account
            
        Returns:
            Created Account instance
            
        Raises:
            AccountError: If account creation fails
            ValidationError: If input data is invalid
        """
        try:
            # Generate API key if not provided
            if not api_key:
                api_key = self._generate_api_key()
            
            # Validate inputs
            if max_documents <= 0:
                raise ValidationError("max_documents must be positive")
            
            api_key_hash = self._hash_api_key(api_key)
            client = await get_postgres_client()
            
            # Create account data
            account = Account(
                api_key=api_key,
                document_count=0,
                max_documents=max_documents,
                is_active=True
            )
            
            # Insert into database
            account_data = {
                "account_id": account.account_id,
                "api_key_hash": api_key_hash,
                "created_at": account.created_at,
                "document_count": account.document_count,
                "max_documents": account.max_documents,
                "is_active": account.is_active
            }
            
            await client.insert_record(self.table_name, account_data)
            
            logger.info("Account created successfully",
                       extra={"account_id": str(account.account_id), "max_documents": max_documents})
            return account
            
        except ValidationError:
            raise
        except DatabaseError as e:
            logger.error(f"Database error during account creation: {e.message}",
                        extra={"error_type": e.error_type, "details": e.details})
            raise AccountError(f"Account creation failed: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error during account creation: {e}")
            raise AccountError(f"Account creation failed: {e}")
    
    async def get_account(self, account_id: UUID) -> Optional[Account]:
        """
        Get account by ID.
        
        Args:
            account_id: Account UUID to retrieve
            
        Returns:
            Account instance if found, None otherwise
            
        Raises:
            AccountError: If retrieval fails due to system error
        """
        try:
            client = await get_postgres_client()
            account_data = await client.get_record(self.table_name, str(account_id))
            
            # Reconstruct account (API key is hashed in DB, so we can't return it)
            account = Account(
                account_id=account_data["account_id"],
                api_key="[REDACTED]",  # Don't expose API key hash
                created_at=account_data["created_at"],
                document_count=account_data["document_count"],
                max_documents=account_data["max_documents"],
                is_active=account_data["is_active"]
            )
            
            logger.info("Account retrieved successfully",
                       extra={"account_id": str(account_id)})
            return account
            
        except NotFoundError:
            logger.info("Account not found", extra={"account_id": str(account_id)})
            return None
        except DatabaseError as e:
            logger.error(f"Database error during account retrieval: {e.message}",
                        extra={"error_type": e.error_type, "details": e.details})
            raise AccountError(f"Account retrieval failed: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error during account retrieval: {e}")
            raise AccountError(f"Account retrieval failed: {e}")
    
    async def update_document_count(self, account_id: UUID, increment: int) -> bool:
        """
        Update document count for account.
        
        Args:
            account_id: Account UUID to update
            increment: Amount to increment document count (can be negative)
            
        Returns:
            True if update successful
            
        Raises:
            AccountNotFoundError: If account not found
            QuotaExceededError: If increment would exceed limit
            AccountError: If update fails due to system error
        """
        try:
            client = await get_postgres_client()
            
            # Get current account data
            account_data = await client.get_record(self.table_name, str(account_id))
            current_count = account_data["document_count"]
            max_documents = account_data["max_documents"]
            new_count = current_count + increment
            
            # Validate new count
            if new_count < 0:
                raise ValidationError("Document count cannot be negative")
            
            if new_count > max_documents:
                logger.warning("Document count would exceed limit",
                              extra={
                                  "account_id": str(account_id),
                                  "current_count": current_count,
                                  "increment": increment,
                                  "new_count": new_count,
                                  "max_documents": max_documents
                              })
                raise QuotaExceededError(
                    f"Document count would exceed limit ({new_count} > {max_documents})",
                    {"current_count": current_count, "increment": increment, "max_documents": max_documents}
                )
            
            # Update document count
            update_data = {"document_count": new_count}
            await client.update_record(self.table_name, str(account_id), update_data)
            
            logger.info("Document count updated successfully",
                       extra={
                           "account_id": str(account_id),
                           "old_count": current_count,
                           "new_count": new_count,
                           "increment": increment
                       })
            return True
            
        except NotFoundError:
            logger.warning("Account not found for document count update",
                          extra={"account_id": str(account_id)})
            raise AccountNotFoundError(f"Account not found: {account_id}")
        except (ValidationError, QuotaExceededError):
            raise
        except DatabaseError as e:
            logger.error(f"Database error during document count update: {e.message}",
                        extra={"error_type": e.error_type, "details": e.details})
            raise AccountError(f"Document count update failed: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error during document count update: {e}")
            raise AccountError(f"Document count update failed: {e}")
    
    async def check_document_limit(self, account_id: UUID) -> bool:
        """
        Check if account can add more documents.
        
        Args:
            account_id: Account UUID to check
            
        Returns:
            True if account can add more documents, False if at limit
            
        Raises:
            AccountNotFoundError: If account not found
            AccountError: If check fails due to system error
        """
        try:
            client = await get_postgres_client()
            account_data = await client.get_record(self.table_name, str(account_id))
            
            current_count = account_data["document_count"]
            max_documents = account_data["max_documents"]
            can_add = current_count < max_documents
            
            logger.debug("Document limit check completed",
                        extra={
                            "account_id": str(account_id),
                            "current_count": current_count,
                            "max_documents": max_documents,
                            "can_add": can_add
                        })
            return can_add
            
        except NotFoundError:
            logger.warning("Account not found for limit check",
                          extra={"account_id": str(account_id)})
            raise AccountNotFoundError(f"Account not found: {account_id}")
        except DatabaseError as e:
            logger.error(f"Database error during document limit check: {e.message}",
                        extra={"error_type": e.error_type, "details": e.details})
            raise AccountError(f"Document limit check failed: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error during document limit check: {e}")
            raise AccountError(f"Document limit check failed: {e}")
    
    async def deactivate_account(self, account_id: UUID) -> bool:
        """
        Deactivate account (soft delete).
        
        Args:
            account_id: Account UUID to deactivate
            
        Returns:
            True if deactivation successful
            
        Raises:
            AccountNotFoundError: If account not found
            AccountError: If deactivation fails due to system error
        """
        try:
            client = await get_postgres_client()
            
            # Update account status
            update_data = {"is_active": False}
            await client.update_record(self.table_name, str(account_id), update_data)
            
            logger.info("Account deactivated successfully",
                       extra={"account_id": str(account_id)})
            return True
            
        except NotFoundError:
            logger.warning("Account not found for deactivation",
                          extra={"account_id": str(account_id)})
            raise AccountNotFoundError(f"Account not found: {account_id}")
        except DatabaseError as e:
            logger.error(f"Database error during account deactivation: {e.message}",
                        extra={"error_type": e.error_type, "details": e.details})
            raise AccountError(f"Account deactivation failed: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error during account deactivation: {e}")
            raise AccountError(f"Account deactivation failed: {e}")


# Global service instance
_account_service: Optional[AccountService] = None


def get_account_service() -> AccountService:
    """
    Get the global account service instance.
    
    Returns:
        AccountService instance
    """
    global _account_service
    if not _account_service:
        _account_service = AccountService()
    return _account_service