-- PostgreSQL Initialization Script
-- This runs automatically when PostgreSQL container starts for the first time

-- Create database (already created by POSTGRES_DB env var, but kept for reference)
-- CREATE DATABASE IF NOT EXISTS supply_chain;

-- Connect to the database
\c supply_chain;

-- Create schema if needed (optional, using default public schema)
-- CREATE SCHEMA IF NOT EXISTS supply_chain;

-- Enable UUID extension (useful for future enhancements)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better query performance
-- These will be created by Hibernate on first run, but can be pre-created here

-- Note: Tables will be created automatically by Spring Boot / Hibernate
-- based on @Entity annotations (hibernate.ddl-auto=update)

-- Optionally, you can pre-load reference data here
-- For now, data is loaded from CSVs by the application

-- Print confirmation
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL database initialized successfully';
END $$;
