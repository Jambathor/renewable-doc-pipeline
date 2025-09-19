"""
PostgreSQL database client for renewable document pipeline.

Provides async database operations with connection pooling, transaction support,
and basic CRUD operations. Follows the storage strategy for Account, Document,
ProcessingJob, and QualityMetrics tables with ACID transactions and foreign key constraints.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

import psycopg
from psycopg import AsyncConnection, AsyncCursor
from psycopg.pool import AsyncConnectionPool
from psycopg.rows import dict_row

from ..config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""
    
    def __init__(self, message: str, error_type: str = "database_error", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(message)


class ConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "connection_error", details)


class TransactionError(DatabaseError):
    """Exception raised when transaction operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "transaction_error", details)


class ValidationError(DatabaseError):
    """Exception raised when data validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "validation_error", details)


class NotFoundError(DatabaseError):
    """Exception raised when requested record is not found."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "not_found_error", details)


class PostgreSQLClient:
    """
    Async PostgreSQL client with connection pooling and transaction support.
    
    Provides basic CRUD operations, transaction handling, and connection management
    for the renewable document pipeline data model.
    """
    
    def __init__(self, database_url: Optional[str] = None, min_size: int = 5, max_size: int = 20):
        """
        Initialize PostgreSQL client with connection pool.
        
        Args:
            database_url: PostgreSQL connection URL. Defaults to settings.database_url
            min_size: Minimum connections in pool
            max_size: Maximum connections in pool
        """
        self.database_url = database_url or settings.database_url
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[AsyncConnectionPool] = None
        self._closed = False
    
    async def connect(self) -> None:
        """
        Initialize connection pool.
        
        Raises:
            ConnectionError: If connection pool creation fails
        """
        try:
            self.pool = AsyncConnectionPool(
                conninfo=self.database_url,
                min_size=self.min_size,
                max_size=self.max_size,
                kwargs={"row_factory": dict_row}
            )
            await self.pool.open()
            logger.info(f"PostgreSQL connection pool initialized (min={self.min_size}, max={self.max_size})")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}", {"database_url": self.database_url})
    
    async def close_connection(self) -> None:
        """
        Close connection pool and cleanup resources.
        """
        if self.pool and not self._closed:
            await self.pool.close()
            self._closed = True
            logger.info("PostgreSQL connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get a connection from the pool as context manager.
        
        Yields:
            AsyncConnection: Database connection
            
        Raises:
            ConnectionError: If pool is not initialized or connection fails
        """
        if not self.pool:
            raise ConnectionError("Connection pool not initialized. Call connect() first.")
        
        try:
            async with self.pool.connection() as conn:
                yield conn
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise ConnectionError(f"Failed to get database connection: {e}")
    
    async def execute_query(
        self, 
        query: str, 
        params: Optional[Union[Dict[str, Any], List[Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows as dictionaries
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    results = await cur.fetchall()
                    return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Query execution failed: {e}, Query: {query}")
            raise DatabaseError(f"Query execution failed: {e}", details={"query": query, "params": params})
    
    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """
        Execute multiple queries in a single transaction.
        
        Args:
            queries: List of (query, params) tuples
            
        Returns:
            True if transaction succeeds
            
        Raises:
            TransactionError: If transaction fails
        """
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cur:
                        for query, params in queries:
                            await cur.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise TransactionError(f"Transaction failed: {e}", details={"queries_count": len(queries)})
    
    async def insert_record(self, table: str, data: Dict[str, Any]) -> str:
        """
        Insert a record and return the ID.
        
        Args:
            table: Table name
            data: Record data as dictionary
            
        Returns:
            Inserted record ID (assumes UUID primary key)
            
        Raises:
            DatabaseError: If insert fails
            ValidationError: If data validation fails
        """
        if not data:
            raise ValidationError("Insert data cannot be empty")
        
        try:
            columns = list(data.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = list(data.values())
            
            # Assume primary key is {table}_id or id
            id_column = f"{table.rstrip('s')}_id" if not table.endswith('_id') else "id"
            
            query = f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING {id_column}
            """
            
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, values)
                    result = await cur.fetchone()
                    return str(result[id_column]) if result else None
                    
        except Exception as e:
            logger.error(f"Insert failed for table {table}: {e}")
            raise DatabaseError(f"Insert failed: {e}", details={"table": table, "data": data})
    
    async def update_record(self, table: str, record_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a record by ID.
        
        Args:
            table: Table name
            record_id: Record ID to update
            data: Updated data as dictionary
            
        Returns:
            True if record was updated
            
        Raises:
            DatabaseError: If update fails
            ValidationError: If data validation fails
            NotFoundError: If record not found
        """
        if not data:
            raise ValidationError("Update data cannot be empty")
        
        try:
            columns = list(data.keys())
            set_clauses = [f"{col} = ${i+2}" for i, col in enumerate(columns)]
            values = [record_id] + list(data.values())
            
            # Assume primary key is {table}_id or id
            id_column = f"{table.rstrip('s')}_id" if not table.endswith('_id') else "id"
            
            query = f"""
                UPDATE {table}
                SET {', '.join(set_clauses)}
                WHERE {id_column} = $1
            """
            
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, values)
                    if cur.rowcount == 0:
                        raise NotFoundError(f"Record not found in table {table} with ID {record_id}")
                    return True
                    
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Update failed for table {table}: {e}")
            raise DatabaseError(f"Update failed: {e}", details={"table": table, "id": record_id, "data": data})
    
    async def delete_record(self, table: str, record_id: str) -> bool:
        """
        Delete a record by ID.
        
        Args:
            table: Table name
            record_id: Record ID to delete
            
        Returns:
            True if record was deleted
            
        Raises:
            DatabaseError: If delete fails
            NotFoundError: If record not found
        """
        try:
            # Assume primary key is {table}_id or id
            id_column = f"{table.rstrip('s')}_id" if not table.endswith('_id') else "id"
            
            query = f"DELETE FROM {table} WHERE {id_column} = $1"
            
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (record_id,))
                    if cur.rowcount == 0:
                        raise NotFoundError(f"Record not found in table {table} with ID {record_id}")
                    return True
                    
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Delete failed for table {table}: {e}")
            raise DatabaseError(f"Delete failed: {e}", details={"table": table, "id": record_id})
    
    async def get_record(self, table: str, record_id: str) -> Dict[str, Any]:
        """
        Get a record by ID.
        
        Args:
            table: Table name
            record_id: Record ID to retrieve
            
        Returns:
            Record data as dictionary
            
        Raises:
            DatabaseError: If query fails
            NotFoundError: If record not found
        """
        try:
            # Assume primary key is {table}_id or id
            id_column = f"{table.rstrip('s')}_id" if not table.endswith('_id') else "id"
            
            query = f"SELECT * FROM {table} WHERE {id_column} = $1"
            
            results = await self.execute_query(query, (record_id,))
            if not results:
                raise NotFoundError(f"Record not found in table {table} with ID {record_id}")
            
            return results[0]
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Get record failed for table {table}: {e}")
            raise DatabaseError(f"Get record failed: {e}", details={"table": table, "id": record_id})
    
    async def execute_migration(self, migration_sql: str, migration_name: str) -> bool:
        """
        Execute a database migration script.
        
        Args:
            migration_sql: SQL migration script
            migration_name: Name of the migration for logging
            
        Returns:
            True if migration succeeds
            
        Raises:
            DatabaseError: If migration fails
        """
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cur:
                        await cur.execute(migration_sql)
            
            logger.info(f"Migration '{migration_name}' executed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration '{migration_name}' failed: {e}")
            raise DatabaseError(f"Migration failed: {e}", details={"migration": migration_name})
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check database connectivity and pool status.
        
        Returns:
            Health status information
        """
        try:
            start_time = asyncio.get_event_loop().time()
            await self.execute_query("SELECT 1 as health_check")
            response_time = asyncio.get_event_loop().time() - start_time
            
            pool_stats = {
                "total_connections": len(self.pool._pool) if self.pool else 0,
                "available_connections": len(self.pool._pool) if self.pool else 0,
                "min_size": self.min_size,
                "max_size": self.max_size,
            }
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "pool": pool_stats
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "pool": {"status": "disconnected"}
            }


# Global client instance
_client: Optional[PostgreSQLClient] = None


async def get_postgres_client() -> PostgreSQLClient:
    """
    Get the global PostgreSQL client instance.
    
    Returns:
        PostgreSQL client instance
        
    Raises:
        ConnectionError: If client is not initialized
    """
    global _client
    if not _client:
        _client = PostgreSQLClient()
        await _client.connect()
    return _client


async def close_postgres_client() -> None:
    """Close the global PostgreSQL client instance."""
    global _client
    if _client:
        await _client.close_connection()
        _client = None