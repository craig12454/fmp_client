"""Tests for FMPClient."""

import pytest
import pandas as pd
from unittest.mock import patch, Mock

from fmp_client import FMPClient, TooManyRequestsException

# Sample API response for testing
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


class TestFMPClientInit:
    """Tests for FMPClient initialization."""

    def test_init_with_api_key(self, api_key):
        """Test that client initializes with direct API key."""
        client = FMPClient(api_key=api_key)
        assert client.api_key == api_key

    def test_init_missing_api_key_raises(self):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError):
            FMPClient()

    def test_init_with_config_dict(self):
        """Test initialization with config dictionary."""
        config = {"fmp": {"api_key": "config-key-123"}}
        client = FMPClient(config=config)
        assert client.api_key == "config-key-123"


class TestGetQuote:
    """Tests for get_quote method."""

    def test_get_quote_returns_data(self, fmp_client, mock_session):
        """Test that get_quote returns quote data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_QUOTE_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_quote("AAPL")
        assert result == SAMPLE_QUOTE_RESPONSE

    def test_get_quote_invalid_symbol_type_raises(self, fmp_client):
        """Test that non-string symbol raises ValueError."""
        with pytest.raises(ValueError):
            fmp_client.get_quote(123)

    def test_get_quote_returns_dataframe(self, fmp_client, mock_session):
        """Test that return_type='df' returns DataFrame."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_QUOTE_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_quote("AAPL", return_type="df")
        assert isinstance(result, pd.DataFrame)
        assert result["symbol"].iloc[0] == "AAPL"


class TestRateLimiting:
    """Tests for rate limit handling."""

    def test_rate_limit_raises_exception(self, fmp_client, mock_session):
        """Test that HTTP 429 raises TooManyRequestsException."""
        mock_session.get.return_value.status_code = 429
        fmp_client.session = mock_session
        with pytest.raises(TooManyRequestsException):
            fmp_client.get_quote("AAPL")
