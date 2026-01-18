"""Integration tests for MétéoScore data collection.

This package contains tests that interact with real external APIs
and the actual database. These tests are slower and may fail due
to external service availability.

Usage:
    # Run only integration tests
    pytest -m integration

    # Skip integration tests (default for CI)
    pytest -m "not integration"

    # Run all tests including integration
    pytest --run-integration

Note:
    Integration tests require:
    - DATABASE_URL environment variable pointing to a test database
    - METEOFRANCE_API_TOKEN for AROME tests (optional)
    - Network access to external APIs
"""
