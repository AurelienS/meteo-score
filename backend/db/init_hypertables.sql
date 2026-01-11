-- TimescaleDB Initialization Script for MétéoScore
-- This script runs automatically when PostgreSQL container starts
-- (mounted to /docker-entrypoint-initdb.d/init.sql in docker-compose.yml)
--
-- Purpose:
-- 1. Enable TimescaleDB extension
-- 2. Configure database settings for time-series workloads
--
-- Note: Table creation and hypertable conversion are handled by Alembic migrations
-- Run `alembic upgrade head` after container starts to create the schema

-- Enable TimescaleDB extension (required for hypertables)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Verify TimescaleDB is installed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
    ) THEN
        RAISE EXCEPTION 'TimescaleDB extension not installed';
    END IF;
    RAISE NOTICE 'TimescaleDB extension is ready (version: %)',
        (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb');
END $$;

-- Configure PostgreSQL settings optimized for TimescaleDB
-- These settings improve performance for time-series workloads

-- Enable parallel query execution for large aggregations
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;

-- Increase work memory for complex queries (default is too low)
ALTER SYSTEM SET work_mem = '64MB';

-- Increase maintenance work memory for faster index creation
ALTER SYSTEM SET maintenance_work_mem = '256MB';

-- Enable JIT compilation for complex queries
ALTER SYSTEM SET jit = on;

-- Reload configuration
SELECT pg_reload_conf();

-- Log success message
DO $$
BEGIN
    RAISE NOTICE 'MétéoScore database initialized with TimescaleDB support';
    RAISE NOTICE 'Run "alembic upgrade head" to create tables and hypertables';
END $$;
