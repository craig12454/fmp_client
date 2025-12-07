"""Pytest fixtures for FMP client tests.

Fixtures defined here are automatically available to all test files
in this directory without needing to import them.
"""

import pytest
from unittest.mock import Mock, patch
from fmp_client import FMPClient
# Sample API responses for mocking
SAMPLE_QUOTE_RESPONSE = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 175.50,
        "change": 2.35,
        "changesPercentage": 1.36,
        "volume": 52436789,
    }
]

SAMPLE_PROFILE_RESPONSE = [
    {
        "symbol": "AAPL",
        "companyName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "marketCap": 2800000000000,
        "description": "Apple designs and manufactures consumer electronics.",
    }
]


# TODO(human): Implement the fixtures below


@pytest.fixture
def api_key():
    """Provide a test API key."""
    return "test-api-key-12345"


@pytest.fixture
def fmp_client(api_key):
    """Create an FMPClient instance for testing.

    This fixture should create a real client instance that we can test.
    The client won't make real API calls - we'll mock those in individual tests.
    """
    return FMPClient(api_key=api_key)


@pytest.fixture
def mock_session():
    """Create a mock requests session.

    This fixture provides a mock that replaces the CachedSession,
    allowing us to control API responses without making real HTTP calls.
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.from_cache = False
    mock_response.json.return_value = [] # Empty default

    session = Mock()
    session.get.return_value = mock_response
    return session
