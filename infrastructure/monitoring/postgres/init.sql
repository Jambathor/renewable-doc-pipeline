-- Initialize renewable energy document processing database
CREATE DATABASE renewable_docs;

-- Connect to the database and create initial schema if needed
\c renewable_docs;

-- Create basic tables for development/testing
-- These will be replaced by proper migrations later

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Placeholder comment for future migrations
-- Actual table creation will be handled by migration scripts in Phase 3.3