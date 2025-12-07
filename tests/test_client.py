"""Tests for FMPClient."""

import pytest
import pandas as pd
from unittest.mock import patch, Mock

from fmp_client import FMPClient, TooManyRequestsException
from tests.sample_data import (
    SAMPLE_QUOTE_RESPONSE,
    SAMPLE_SEARCH_RESPONSE,
    SAMPLE_EOD_ADJ_RESPONSE,
    SAMPLE_PROFILE_RESPONSE,
    SAMPLE_ENTERPRISE_VALUES_RESPONSE,
    SAMPLE_FINANCIAL_RATIOS_RESPONSE,
    SAMPLE_FINANCIAL_GROWTH_RESPONSE,
    SAMPLE_EARNINGS_RESPONSE,
    SAMPLE_REVENUE_SEGMENTATION_RESPONSE,
    SAMPLE_PRICE_TARGET_CONSENSUS_RESPONSE,
    SAMPLE_STOCK_NEWS_RESPONSE,
    SAMPLE_SCREENED_STOCKS_RESPONSE,
    SAMPLE_HISTORICAL_PRICE_RESPONSE,
    SAMPLE_HISTORICAL_MARKET_CAP_RESPONSE,
    SAMPLE_INCOME_STATEMENT_RESPONSE,
    SAMPLE_BALANCE_SHEET_RESPONSE,
    SAMPLE_CASH_FLOW_RESPONSE,
    SAMPLE_KEY_METRICS_RESPONSE,
    SAMPLE_SP500_CONSTITUENTS_RESPONSE,
    SAMPLE_HISTORICAL_SP500_RESPONSE,
    SAMPLE_NASDAQ_CONSTITUENTS_RESPONSE,
    SAMPLE_STOCK_SPLITS_RESPONSE,
    SAMPLE_DIVIDENDS_RESPONSE,
    SAMPLE_SECTOR_PERFORMANCE_RESPONSE,
)


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


class TestSearchMethods:
    """Tests for search methods."""

    def test_search_symbol_returns_data(self, fmp_client, mock_session):
        """Test search_symbol returns matching symbols."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SEARCH_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.search_symbol("AAPL")
        assert result == SAMPLE_SEARCH_RESPONSE
        assert len(result) == 2

    def test_search_symbol_returns_dataframe(self, fmp_client, mock_session):
        """Test search_symbol returns DataFrame when requested."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SEARCH_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.search_symbol("AAPL", return_type="df")
        assert isinstance(result, pd.DataFrame)
        assert "symbol" in result.columns

    def test_search_company_name_returns_data(self, fmp_client, mock_session):
        """Test search_company_name returns matching companies."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SEARCH_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.search_company_name("Apple")
        assert result == SAMPLE_SEARCH_RESPONSE

    def test_search_with_exchange_filter(self, fmp_client, mock_session):
        """Test search with exchange parameter."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SEARCH_RESPONSE
        fmp_client.session = mock_session
        fmp_client.search_symbol("AAPL", exchange="NYSE", limit=10)
        # Verify the call was made (checking params would require inspection)
        assert mock_session.get.called


class TestPriceDataMethods:
    """Tests for price data methods."""

    def test_get_eod_adj_returns_data(self, fmp_client, mock_session):
        """Test get_eod_adj returns historical prices."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_EOD_ADJ_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_eod_adj("AAPL")
        assert result == SAMPLE_EOD_ADJ_RESPONSE
        assert "adjClose" in result[0]

    def test_get_eod_adj_with_date_range(self, fmp_client, mock_session):
        """Test get_eod_adj with date range parameters."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_EOD_ADJ_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_eod_adj("AAPL", date_from="2024-01-01", date_to="2024-01-31")
        assert len(result) == 2

    def test_get_eod_adj_returns_dataframe(self, fmp_client, mock_session):
        """Test get_eod_adj returns DataFrame when requested."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_EOD_ADJ_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_eod_adj("AAPL", return_type="df")
        assert isinstance(result, pd.DataFrame)
        assert "date" in result.columns

    def test_get_historical_price_full_returns_data(self, fmp_client, mock_session):
        """Test get_historical_price_full returns OHLCV data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_HISTORICAL_PRICE_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_historical_price_full("AAPL")
        assert result == SAMPLE_HISTORICAL_PRICE_RESPONSE
        assert "vwap" in result[0]

    def test_get_historical_market_cap_returns_data(self, fmp_client, mock_session):
        """Test get_historical_market_cap returns market cap history."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_HISTORICAL_MARKET_CAP_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_historical_market_cap("AAPL")
        assert result == SAMPLE_HISTORICAL_MARKET_CAP_RESPONSE
        assert "marketCap" in result[0]


class TestCompanyFundamentals:
    """Tests for company fundamentals methods."""

    def test_get_company_profile_returns_data(self, fmp_client, mock_session):
        """Test get_company_profile returns company info."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_PROFILE_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_company_profile("AAPL")
        assert result == SAMPLE_PROFILE_RESPONSE
        assert result[0]["sector"] == "Technology"

    def test_get_company_profile_returns_dataframe(self, fmp_client, mock_session):
        """Test get_company_profile returns DataFrame when requested."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_PROFILE_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_company_profile("AAPL", return_type="df")
        assert isinstance(result, pd.DataFrame)
        assert "companyName" in result.columns

    def test_get_enterprise_values_returns_data(self, fmp_client, mock_session):
        """Test get_enterprise_values returns EV metrics."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_ENTERPRISE_VALUES_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_enterprise_values("AAPL")
        assert result == SAMPLE_ENTERPRISE_VALUES_RESPONSE
        assert "enterpriseValue" in result[0]

    def test_get_enterprise_values_with_period(self, fmp_client, mock_session):
        """Test get_enterprise_values with annual period."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_ENTERPRISE_VALUES_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_enterprise_values("AAPL", period="annual", limit=8)
        assert result == SAMPLE_ENTERPRISE_VALUES_RESPONSE

    def test_get_financial_ratios_returns_data(self, fmp_client, mock_session):
        """Test get_financial_ratios returns ratio data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_FINANCIAL_RATIOS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_financial_ratios("AAPL")
        assert result == SAMPLE_FINANCIAL_RATIOS_RESPONSE
        assert "priceEarningsRatio" in result[0]


class TestFinancialGrowthAndEarnings:
    """Tests for financial growth and earnings methods."""

    def test_get_financial_growth_returns_data(self, fmp_client, mock_session):
        """Test get_financial_growth returns growth metrics."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_FINANCIAL_GROWTH_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_financial_growth("AAPL")
        assert result == SAMPLE_FINANCIAL_GROWTH_RESPONSE
        assert "revenueGrowth" in result[0]

    def test_get_earnings_returns_data(self, fmp_client, mock_session):
        """Test get_earnings returns earnings data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_EARNINGS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_earnings("AAPL")
        assert result == SAMPLE_EARNINGS_RESPONSE
        assert "epsActual" in result[0]

    def test_get_revenue_product_segmentation_returns_data(self, fmp_client, mock_session):
        """Test get_revenue_product_segmentation returns segmentation data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_REVENUE_SEGMENTATION_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_revenue_product_segmentation("AAPL")
        assert result == SAMPLE_REVENUE_SEGMENTATION_RESPONSE
        assert "iPhone" in result[0]


class TestAnalystAndMarketData:
    """Tests for analyst and market data methods."""

    def test_get_price_target_consensus_returns_data(self, fmp_client, mock_session):
        """Test get_price_target_consensus returns analyst targets."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_PRICE_TARGET_CONSENSUS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_price_target_consensus("AAPL")
        assert result == SAMPLE_PRICE_TARGET_CONSENSUS_RESPONSE
        assert "targetConsensus" in result[0]

    def test_get_stock_news_returns_data(self, fmp_client, mock_session):
        """Test get_stock_news returns news articles."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_STOCK_NEWS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_stock_news("AAPL")
        assert result == SAMPLE_STOCK_NEWS_RESPONSE
        assert "title" in result[0]

    def test_get_stock_news_with_pagination(self, fmp_client, mock_session):
        """Test get_stock_news with pagination parameters."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_STOCK_NEWS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_stock_news("AAPL", limit=25, page=1)
        assert mock_session.get.called

    def test_get_price_target_news_returns_data(self, fmp_client, mock_session):
        """Test get_price_target_news returns price target news."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_STOCK_NEWS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_price_target_news("AAPL")
        assert result == SAMPLE_STOCK_NEWS_RESPONSE


class TestFinancialStatements:
    """Tests for financial statement methods."""

    def test_get_income_statement_returns_data(self, fmp_client, mock_session):
        """Test get_income_statement returns income data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_INCOME_STATEMENT_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_income_statement("AAPL")
        assert result == SAMPLE_INCOME_STATEMENT_RESPONSE
        assert "revenue" in result[0]
        assert "filingDate" in result[0]

    def test_get_income_statement_quarterly(self, fmp_client, mock_session):
        """Test get_income_statement with quarterly period."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_INCOME_STATEMENT_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_income_statement("AAPL", period="quarter", limit=8)
        assert mock_session.get.called

    def test_get_balance_sheet_returns_data(self, fmp_client, mock_session):
        """Test get_balance_sheet returns balance sheet data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_BALANCE_SHEET_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_balance_sheet("AAPL")
        assert result == SAMPLE_BALANCE_SHEET_RESPONSE
        assert "totalAssets" in result[0]

    def test_get_cash_flow_statement_returns_data(self, fmp_client, mock_session):
        """Test get_cash_flow_statement returns cash flow data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_CASH_FLOW_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_cash_flow_statement("AAPL")
        assert result == SAMPLE_CASH_FLOW_RESPONSE
        assert "freeCashFlow" in result[0]

    def test_get_key_metrics_returns_data(self, fmp_client, mock_session):
        """Test get_key_metrics returns key financial metrics."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_KEY_METRICS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_key_metrics("AAPL")
        assert result == SAMPLE_KEY_METRICS_RESPONSE
        assert "peRatio" in result[0]

    def test_get_income_statement_growth_returns_data(self, fmp_client, mock_session):
        """Test get_income_statement_growth returns growth rates."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_FINANCIAL_GROWTH_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_income_statement_growth("AAPL")
        assert mock_session.get.called


class TestIndexConstituents:
    """Tests for index constituent methods."""

    def test_get_sp500_constituents_returns_data(self, fmp_client, mock_session):
        """Test get_sp500_constituents returns S&P 500 members."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SP500_CONSTITUENTS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_sp500_constituents()
        assert result == SAMPLE_SP500_CONSTITUENTS_RESPONSE
        assert len(result) == 2

    def test_get_sp500_constituents_returns_dataframe(self, fmp_client, mock_session):
        """Test get_sp500_constituents returns DataFrame when requested."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SP500_CONSTITUENTS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_sp500_constituents(return_type="df")
        assert isinstance(result, pd.DataFrame)
        assert "symbol" in result.columns

    def test_get_historical_sp500_constituents_returns_data(self, fmp_client, mock_session):
        """Test get_historical_sp500_constituents returns historical changes."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_HISTORICAL_SP500_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_historical_sp500_constituents()
        assert result == SAMPLE_HISTORICAL_SP500_RESPONSE
        assert "dateAdded" in result[0]

    def test_get_nasdaq_constituents_returns_data(self, fmp_client, mock_session):
        """Test get_nasdaq_constituents returns NASDAQ 100 members."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_NASDAQ_CONSTITUENTS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_nasdaq_constituents()
        assert result == SAMPLE_NASDAQ_CONSTITUENTS_RESPONSE

    def test_get_historical_nasdaq_constituents_returns_data(self, fmp_client, mock_session):
        """Test get_historical_nasdaq_constituents returns historical changes."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_HISTORICAL_SP500_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_historical_nasdaq_constituents()
        assert mock_session.get.called


class TestCorporateEventsAndMarketContext:
    """Tests for corporate events and market context methods."""

    def test_get_stock_splits_returns_data(self, fmp_client, mock_session):
        """Test get_stock_splits returns split history."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_STOCK_SPLITS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_stock_splits("AAPL")
        assert result == SAMPLE_STOCK_SPLITS_RESPONSE
        assert "numerator" in result[0]

    def test_get_stock_splits_returns_dataframe(self, fmp_client, mock_session):
        """Test get_stock_splits returns DataFrame when requested."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_STOCK_SPLITS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_stock_splits("AAPL", return_type="df")
        assert isinstance(result, pd.DataFrame)

    def test_get_dividends_returns_data(self, fmp_client, mock_session):
        """Test get_dividends returns dividend history."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_DIVIDENDS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_dividends("AAPL")
        assert result == SAMPLE_DIVIDENDS_RESPONSE
        assert "dividend" in result[0]

    def test_get_historical_sector_performance_returns_data(self, fmp_client, mock_session):
        """Test get_historical_sector_performance returns sector data."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SECTOR_PERFORMANCE_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_historical_sector_performance()
        assert result == SAMPLE_SECTOR_PERFORMANCE_RESPONSE
        assert "sector" in result[0]

    def test_get_index_historical_price_returns_data(self, fmp_client, mock_session):
        """Test get_index_historical_price returns index price history."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_HISTORICAL_PRICE_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_index_historical_price("^GSPC")
        assert result == SAMPLE_HISTORICAL_PRICE_RESPONSE

    def test_get_index_historical_price_with_date_range(self, fmp_client, mock_session):
        """Test get_index_historical_price with date range."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_HISTORICAL_PRICE_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_index_historical_price(
            "^IXIC", date_from="2024-01-01", date_to="2024-01-31"
        )
        assert mock_session.get.called


class TestStockScreening:
    """Tests for stock screening method."""

    def test_get_screened_stocks_returns_data(self, fmp_client, mock_session):
        """Test get_screened_stocks returns filtered stocks."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SCREENED_STOCKS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_screened_stocks()
        assert result == SAMPLE_SCREENED_STOCKS_RESPONSE
        assert len(result) == 2

    def test_get_screened_stocks_with_market_cap_filter(self, fmp_client, mock_session):
        """Test get_screened_stocks with market cap filters."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SCREENED_STOCKS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_screened_stocks(
            market_cap_more_than=1000000000,
            market_cap_lower_than=3000000000000,
        )
        assert mock_session.get.called

    def test_get_screened_stocks_with_sector_filter(self, fmp_client, mock_session):
        """Test get_screened_stocks with sector filter."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SCREENED_STOCKS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_screened_stocks(sector="Technology")
        assert all(stock["sector"] == "Technology" for stock in result)

    def test_get_screened_stocks_with_price_filter(self, fmp_client, mock_session):
        """Test get_screened_stocks with price filters."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SCREENED_STOCKS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_screened_stocks(
            price_more_than=10.0,
            price_lower_than=500.0,
        )
        assert mock_session.get.called

    def test_get_screened_stocks_with_multiple_filters(self, fmp_client, mock_session):
        """Test get_screened_stocks with multiple filters combined."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SCREENED_STOCKS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_screened_stocks(
            market_cap_more_than=1000000000,
            volume_more_than=1000000,
            sector="Technology",
            exchange="NASDAQ",
            is_actively_trading=True,
            limit=50,
        )
        assert mock_session.get.called

    def test_get_screened_stocks_returns_dataframe(self, fmp_client, mock_session):
        """Test get_screened_stocks returns DataFrame when requested."""
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = SAMPLE_SCREENED_STOCKS_RESPONSE
        fmp_client.session = mock_session
        result = fmp_client.get_screened_stocks(return_type="df")
        assert isinstance(result, pd.DataFrame)
        assert "symbol" in result.columns


class TestCacheOperations:
    """Tests for cache operations."""

    def test_clear_cache(self, fmp_client):
        """Test clear_cache method."""
        # Create a mock cache with clear method
        fmp_client.session.cache = Mock()
        fmp_client.clear_cache()
        fmp_client.session.cache.clear.assert_called_once()


class TestErrorHandling:
    """Tests for error handling."""

    def test_http_error_raises_exception(self, fmp_client, mock_session):
        """Test that non-200/429 status codes raise RequestException."""
        import requests
        mock_session.get.return_value.status_code = 500
        mock_session.get.return_value.text = "Internal Server Error"
        fmp_client.session = mock_session
        with pytest.raises(requests.RequestException):
            fmp_client.get_quote("AAPL")

    def test_http_404_raises_exception(self, fmp_client, mock_session):
        """Test that 404 status code raises RequestException."""
        import requests
        mock_session.get.return_value.status_code = 404
        mock_session.get.return_value.text = "Not Found"
        fmp_client.session = mock_session
        with pytest.raises(requests.RequestException):
            fmp_client.get_company_profile("INVALID_SYMBOL")
