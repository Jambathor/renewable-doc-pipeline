"""
Database migrations for renewable energy PDF processing pipeline.

This module defines SQL migrations for creating and updating database schema
for all entities in the data model. Supports both forward and rollback migrations.
"""

from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

from src.storage.postgres_client import get_postgres_client, DatabaseError

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a single database migration."""
    
    version: str
    description: str
    up_sql: str
    down_sql: str
    applied_at: Optional[datetime] = None


class MigrationRunner:
    """Database migration runner for schema management."""
    
    def __init__(self):
        self.client = get_postgres_client()
        
    async def ensure_migration_table(self) -> None:
        """Create the migration tracking table if it doesn't exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            checksum VARCHAR(64) NOT NULL
        );
        """
        
        try:
            await self.client.execute_query(create_table_sql)
            logger.info("Migration tracking table ensured")
        except DatabaseError as e:
            logger.error(f"Failed to create migration table: {e}")
            raise
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        try:
            result = await self.client.execute_query(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return [row['version'] for row in result]
        except DatabaseError as e:
            logger.error(f"Failed to get applied migrations: {e}")
            raise
    
    async def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration."""
        try:
            # Calculate checksum for verification
            import hashlib
            checksum = hashlib.sha256(migration.up_sql.encode()).hexdigest()
            
            # Apply migration in transaction
            queries = [
                (migration.up_sql, []),
                (
                    "INSERT INTO schema_migrations (version, description, checksum) VALUES (%s, %s, %s)",
                    [migration.version, migration.description, checksum]
                )
            ]
            
            await self.client.execute_transaction(queries)
            logger.info(f"Applied migration {migration.version}: {migration.description}")
            return True
            
        except DatabaseError as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            raise
    
    async def rollback_migration(self, migration: Migration) -> bool:
        """Rollback a single migration."""
        try:
            queries = [
                (migration.down_sql, []),
                ("DELETE FROM schema_migrations WHERE version = %s", [migration.version])
            ]
            
            await self.client.execute_transaction(queries)
            logger.info(f"Rolled back migration {migration.version}")
            return True
            
        except DatabaseError as e:
            logger.error(f"Failed to rollback migration {migration.version}: {e}")
            raise
    
    async def migrate(self, target_version: Optional[str] = None) -> bool:
        """Run all pending migrations up to target version."""
        await self.ensure_migration_table()
        applied = await self.get_applied_migrations()
        
        migrations = get_all_migrations()
        pending = [m for m in migrations if m.version not in applied]
        
        if target_version:
            pending = [m for m in pending if m.version <= target_version]
        
        for migration in pending:
            await self.apply_migration(migration)
        
        logger.info(f"Applied {len(pending)} migrations")
        return True


def get_all_migrations() -> List[Migration]:
    """Get all defined migrations in order."""
    return [
        Migration(
            version="001_initial_schema",
            description="Create initial tables for accounts, documents, processing jobs",
            up_sql="""
            -- Create accounts table
            CREATE TABLE accounts (
                account_id UUID PRIMARY KEY,
                api_key VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                document_count INTEGER NOT NULL DEFAULT 0 CHECK (document_count >= 0),
                max_documents INTEGER NOT NULL DEFAULT 200 CHECK (max_documents > 0),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                CONSTRAINT chk_document_limit CHECK (document_count <= max_documents)
            );
            
            -- Create documents table
            CREATE TABLE documents (
                document_id UUID PRIMARY KEY,
                account_id UUID NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL CHECK (filename != ''),
                file_size BIGINT NOT NULL CHECK (file_size >= 0 AND file_size <= 157286400),
                page_count INTEGER CHECK (page_count >= 0 AND page_count <= 300),
                s3_key VARCHAR(512) NOT NULL,
                upload_time TIMESTAMP WITH TIME ZONE NOT NULL,
                processing_status VARCHAR(50) NOT NULL CHECK (processing_status IN 
                    ('uploaded', 'queued', 'processing', 'completed', 'failed', 'deleted')),
                content_hash VARCHAR(64) NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
            -- Create processing_jobs table
            CREATE TABLE processing_jobs (
                job_id UUID PRIMARY KEY,
                document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                account_id UUID NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
                status VARCHAR(50) NOT NULL CHECK (status IN 
                    ('pending', 'running', 'completed', 'failed', 'retrying')),
                progress_percentage INTEGER NOT NULL CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
                started_at TIMESTAMP WITH TIME ZONE NOT NULL,
                completed_at TIMESTAMP WITH TIME ZONE,
                error_message TEXT,
                error_type VARCHAR(50) CHECK (error_type IN 
                    ('validation_error', 'processing_error', 'storage_error', 'quota_exceeded', 'system_error')),
                retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
                worker_id VARCHAR(255),
                CONSTRAINT chk_completed_after_started CHECK (completed_at IS NULL OR completed_at > started_at)
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS processing_jobs CASCADE;
            DROP TABLE IF EXISTS documents CASCADE;
            DROP TABLE IF EXISTS accounts CASCADE;
            """
        ),
        
        Migration(
            version="002_content_and_citations",
            description="Create tables for extracted content and citations",
            up_sql="""
            -- Create extracted_content table
            CREATE TABLE extracted_content (
                content_id UUID PRIMARY KEY,
                document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL CHECK (page_number > 0),
                content_type VARCHAR(50) NOT NULL CHECK (content_type IN 
                    ('text', 'table', 'chart', 'image', 'title', 'metadata')),
                text_content TEXT NOT NULL CHECK (text_content != ''),
                metadata JSONB DEFAULT '{}'::jsonb,
                bounding_box JSONB,
                confidence_score DOUBLE PRECISION NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
                is_ocr_generated BOOLEAN NOT NULL,
                extracted_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
            
            -- Create citations table
            CREATE TABLE citations (
                citation_id UUID PRIMARY KEY,
                content_id UUID NOT NULL REFERENCES extracted_content(content_id) ON DELETE CASCADE,
                document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL CHECK (page_number > 0),
                relevance_score DOUBLE PRECISION NOT NULL CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
                snippet TEXT NOT NULL CHECK (snippet != ''),
                context TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS citations CASCADE;
            DROP TABLE IF EXISTS extracted_content CASCADE;
            """
        ),
        
        Migration(
            version="003_quality_metrics",
            description="Create quality metrics table for SLA tracking",
            up_sql="""
            -- Create quality_metrics table
            CREATE TABLE quality_metrics (
                metric_id UUID PRIMARY KEY,
                document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                pages_with_anchors INTEGER NOT NULL CHECK (pages_with_anchors >= 0),
                total_pages INTEGER NOT NULL CHECK (total_pages >= 0),
                tables_extracted INTEGER NOT NULL CHECK (tables_extracted >= 0),
                tables_detected INTEGER NOT NULL CHECK (tables_detected >= 0),
                citations_correct INTEGER NOT NULL CHECK (citations_correct >= 0),
                citations_total INTEGER NOT NULL CHECK (citations_total >= 0),
                ocr_confidence_avg DOUBLE PRECISION CHECK (ocr_confidence_avg >= 0.0 AND ocr_confidence_avg <= 1.0),
                processing_time_seconds INTEGER NOT NULL CHECK (processing_time_seconds >= 0),
                measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
                CONSTRAINT chk_anchors_within_pages CHECK (pages_with_anchors <= total_pages),
                CONSTRAINT chk_tables_within_detected CHECK (tables_extracted <= tables_detected),
                CONSTRAINT chk_citations_within_total CHECK (citations_correct <= citations_total)
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS quality_metrics CASCADE;
            """
        ),
        
        Migration(
            version="004_indexes_and_performance",
            description="Create indexes for query performance",
            up_sql="""
            -- Indexes for accounts
            CREATE INDEX idx_accounts_api_key ON accounts(api_key);
            CREATE INDEX idx_accounts_active ON accounts(is_active);
            
            -- Indexes for documents
            CREATE INDEX idx_documents_account_id ON documents(account_id);
            CREATE INDEX idx_documents_status ON documents(processing_status);
            CREATE INDEX idx_documents_account_status ON documents(account_id, processing_status);
            CREATE INDEX idx_documents_hash ON documents(content_hash);
            CREATE INDEX idx_documents_upload_time ON documents(upload_time);
            
            -- Indexes for processing jobs
            CREATE INDEX idx_processing_jobs_document_id ON processing_jobs(document_id);
            CREATE INDEX idx_processing_jobs_account_id ON processing_jobs(account_id);
            CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
            CREATE INDEX idx_processing_jobs_started_at ON processing_jobs(started_at);
            
            -- Indexes for extracted content
            CREATE INDEX idx_extracted_content_document_id ON extracted_content(document_id);
            CREATE INDEX idx_extracted_content_page ON extracted_content(document_id, page_number);
            CREATE INDEX idx_extracted_content_type ON extracted_content(content_type);
            CREATE INDEX idx_extracted_content_confidence ON extracted_content(confidence_score);
            
            -- Indexes for citations
            CREATE INDEX idx_citations_content_id ON citations(content_id);
            CREATE INDEX idx_citations_document_id ON citations(document_id);
            CREATE INDEX idx_citations_relevance ON citations(relevance_score);
            
            -- Indexes for quality metrics
            CREATE INDEX idx_quality_metrics_document_id ON quality_metrics(document_id);
            CREATE INDEX idx_quality_metrics_measured_at ON quality_metrics(measured_at);
            """,
            down_sql="""
            DROP INDEX IF EXISTS idx_quality_metrics_measured_at;
            DROP INDEX IF EXISTS idx_quality_metrics_document_id;
            DROP INDEX IF EXISTS idx_citations_relevance;
            DROP INDEX IF EXISTS idx_citations_document_id;
            DROP INDEX IF EXISTS idx_citations_content_id;
            DROP INDEX IF EXISTS idx_extracted_content_confidence;
            DROP INDEX IF EXISTS idx_extracted_content_type;
            DROP INDEX IF EXISTS idx_extracted_content_page;
            DROP INDEX IF EXISTS idx_extracted_content_document_id;
            DROP INDEX IF EXISTS idx_processing_jobs_started_at;
            DROP INDEX IF EXISTS idx_processing_jobs_status;
            DROP INDEX IF EXISTS idx_processing_jobs_account_id;
            DROP INDEX IF EXISTS idx_processing_jobs_document_id;
            DROP INDEX IF EXISTS idx_documents_upload_time;
            DROP INDEX IF EXISTS idx_documents_hash;
            DROP INDEX IF EXISTS idx_documents_account_status;
            DROP INDEX IF EXISTS idx_documents_status;
            DROP INDEX IF EXISTS idx_documents_account_id;
            DROP INDEX IF EXISTS idx_accounts_active;
            DROP INDEX IF EXISTS idx_accounts_api_key;
            """
        )
    ]


# Convenience functions for common migration operations
async def migrate_to_latest() -> bool:
    """Run all pending migrations to latest version."""
    runner = MigrationRunner()
    return await runner.migrate()


async def get_migration_status() -> Dict[str, any]:
    """Get current migration status."""
    runner = MigrationRunner()
    await runner.ensure_migration_table()
    
    all_migrations = get_all_migrations()
    applied = await runner.get_applied_migrations()
    
    return {
        "total_migrations": len(all_migrations),
        "applied_count": len(applied),
        "pending_count": len(all_migrations) - len(applied),
        "applied_versions": applied,
        "pending_versions": [m.version for m in all_migrations if m.version not in applied]
    }