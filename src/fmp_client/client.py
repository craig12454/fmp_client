"""Financial Modeling Prep (FMP) API client with caching and retry logic."""

import logging
import os
import sqlite3
import time
from collections import deque
from datetime import timedelta
from http.client import OK, TOO_MANY_REQUESTS
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests
import yaml
from requests_cache import CachedSession

__all__ = ["FMPClient", "TooManyRequestsException"]

# Configure logging
logger = logging.getLogger(__name__)

# SQLite error messages that indicate transient issues
SQLITE_RETRY_ERRORS = (
    "database is locked",
    "bad parameter",
    "API misuse",
    "disk I/O error",
)


class TooManyRequestsException(requests.RequestException):
    """Exception raised when FMP API rate limit is exceeded (HTTP 429)."""

    def __init__(self) -> None:
        super().__init__("The FMP API rate limit was exceeded")


class FMPClient:
    """Python client for Financial Modeling Prep (FMP) API.

    Features:
        - SQLite-based response caching with configurable TTL
        - Automatic retry logic for transient errors
        - Support for JSON and DataFrame return types
        - Flexible configuration via file, dict, or environment variable

    Example:
        >>> from fmp_client import FMPClient
        >>> client = FMPClient(api_key="your-api-key")
        >>> quote = client.get_quote("AAPL")
        >>> profile = client.get_company_profile("NVDA", return_type="df")
    """

    BASE_URL = "https://financialmodelingprep.com/stable"

    def __init__(
        self,
        api_key: Optional[str] = None,
        config_path: Optional[Union[str, Path]] = None,
        config: Optional[Dict[str, Any]] = None,
        cache_backend: str = "sqlite",
        cache_name: str = "fmp_cache",
        cache_expire_after: int = 300,
        requests_per_minute: int = 300,
        rate_limit_retry: bool = True,
        rate_limit_max_retries: int = 3,
    ) -> None:
        """Initialize the FMP client.

        Args:
            api_key: FMP API key. Takes precedence over config file/env var.
            config_path: Path to YAML config file containing FMP settings.
            config: Dict with configuration (alternative to config_path).
            cache_backend: Cache backend type (default: "sqlite").
            cache_name: Name for the cache database (default: "fmp_cache").
            cache_expire_after: Cache TTL in seconds (default: 300).
            requests_per_minute: Max requests per minute (default: 300 for Starter plan).
            rate_limit_retry: Whether to auto-retry on 429 responses (default: True).
            rate_limit_max_retries: Max retries on 429 before giving up (default: 3).

        Configuration priority:
            1. Direct `api_key` parameter
            2. Config dict/file under `fmp.api_key`
            3. Environment variable `FMP_API_KEY`

        Raises:
            ValueError: If no API key is provided or found.
            FileNotFoundError: If config_path is specified but file not found.
            yaml.YAMLError: If config file is invalid YAML.

        Example config.yaml:
            fmp:
              api_key: "your-api-key"
              cache:
                backend: "sqlite"
                name: "fmp_cache"
                expire_after: 3600
              rate_limit:
                requests_per_minute: 300
                retry: true
                max_retries: 3
        """
        # Load configuration from various sources
        fmp_config = self._load_config(config_path, config)

        # Resolve API key with priority: param > config > env
        self.api_key = (
            api_key
            or fmp_config.get("api_key")
            or os.getenv("FMP_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "API key must be provided via api_key parameter, "
                "config file (fmp.api_key), or FMP_API_KEY environment variable"
            )

        # Extract cache settings (params override config)
        cache_config = fmp_config.get("cache", {})
        self._cache_backend = cache_config.get("backend", cache_backend)
        self._cache_name = cache_config.get("name", cache_name)
        self._cache_expire_after = cache_config.get("expire_after", cache_expire_after)

        # Initialize cached session
        self.session = CachedSession(
            cache_name=self._cache_name,
            backend=self._cache_backend,
            expire_after=timedelta(seconds=self._cache_expire_after),
            allowable_methods=["GET"],
        )
        self.session.params = {"apikey": self.api_key}

        # Enable WAL mode for better concurrent access (SQLite only)
        if self._cache_backend == "sqlite":
            self._configure_sqlite_wal()

        # Extract rate limit settings (params override config)
        rate_limit_config = fmp_config.get("rate_limit", {})
        self._requests_per_minute = rate_limit_config.get(
            "requests_per_minute", requests_per_minute
        )
        self._rate_limit_retry = rate_limit_config.get("retry", rate_limit_retry)
        self._rate_limit_max_retries = rate_limit_config.get(
            "max_retries", rate_limit_max_retries
        )

        # Sliding window rate limiter: track timestamps of recent requests
        self._request_timestamps: deque[float] = deque()
        self._rate_limit_lock = Lock()

        logger.info(
            f"FMPClient initialized with cache backend: {self._cache_backend}, "
            f"expire_after: {self._cache_expire_after}s, "
            f"rate_limit: {self._requests_per_minute} req/min"
        )

    def _load_config(
        self,
        config_path: Optional[Union[str, Path]],
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Load FMP configuration from file or dict."""
        if config is not None:
            return config.get("fmp", config)

        if config_path is not None:
            path = Path(config_path)
            if not path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")
            with open(path) as f:
                full_config = yaml.safe_load(f)
            return full_config.get("fmp", {})

        return {}

    def _configure_sqlite_wal(self) -> None:
        """Configure SQLite WAL mode for better concurrent access."""
        try:
            cache_db_path = f"{self._cache_name}.sqlite"
            conn = sqlite3.connect(cache_db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")  # 5 second timeout
            conn.close()
            logger.debug("SQLite cache configured with WAL mode")
        except Exception as e:
            logger.warning(f"Could not configure SQLite WAL mode: {e}")

    def _check_rate_limit(self) -> None:
        """Wait if necessary to stay within rate limits.

        Uses a sliding window algorithm to track requests over the last minute.
        Thread-safe for concurrent usage.
        """
        with self._rate_limit_lock:
            now = time.time()
            window_start = now - 60.0  # 1 minute window

            # Remove timestamps older than the window
            while self._request_timestamps and self._request_timestamps[0] < window_start:
                self._request_timestamps.popleft()

            # Check if we're at the limit
            if len(self._request_timestamps) >= self._requests_per_minute:
                # Calculate how long to wait
                oldest_in_window = self._request_timestamps[0]
                wait_time = oldest_in_window - window_start + 0.1  # +100ms buffer
                if wait_time > 0:
                    logger.info(f"Rate limit: waiting {wait_time:.2f}s ({len(self._request_timestamps)} requests in last minute)")
                    time.sleep(wait_time)

    def _record_request(self) -> None:
        """Record a timestamp for an actual API request (not cached)."""
        with self._rate_limit_lock:
            self._request_timestamps.append(time.time())
            # Check if we need to slow down for next request
            self._check_rate_limit()

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Make GET request to FMP API with caching, rate limiting, and retry logic.

        Args:
            endpoint: API endpoint path (without base URL).
            params: Query parameters to include.
            max_retries: Maximum retry attempts for transient errors.

        Returns:
            JSON response as dict or list.

        Raises:
            TooManyRequestsException: If rate limit exceeded after retries.
            requests.RequestException: If request fails.
        """
        url = f"{self.BASE_URL}/{endpoint}"
        rate_limit_attempts = 0

        for attempt in range(max_retries + 1):
            try:
                # Check cache first without rate limiting
                response = self.session.get(url, params=params)

                if hasattr(response, "from_cache") and response.from_cache:
                    logger.debug(f"Retrieved {endpoint} from cache")
                    # Cached response - no rate limit needed
                else:
                    # Actual API call - apply rate limiting for next request
                    self._record_request()
                    logger.debug(f"Fetched {endpoint} from API")

                if response.status_code == OK:
                    return response.json()
                elif response.status_code == TOO_MANY_REQUESTS:
                    rate_limit_attempts += 1
                    if self._rate_limit_retry and rate_limit_attempts <= self._rate_limit_max_retries:
                        # Exponential backoff: 2s, 4s, 8s
                        wait_time = 2 ** rate_limit_attempts
                        logger.warning(
                            f"Rate limit hit (429), retry {rate_limit_attempts}/{self._rate_limit_max_retries} "
                            f"in {wait_time}s"
                        )
                        time.sleep(wait_time)
                        continue
                    logger.error("Rate limit exceeded after retries")
                    raise TooManyRequestsException()
                else:
                    logger.error(
                        f"API request failed with status {response.status_code}: {response.text}"
                    )
                    raise requests.RequestException(
                        f"API request failed with status {response.status_code}: {response.text}"
                    )

            except TooManyRequestsException:
                raise
            except requests.RequestException:
                raise
            except Exception as e:
                error_msg = str(e).lower()
                is_sqlite_error = any(err in error_msg for err in SQLITE_RETRY_ERRORS)

                if is_sqlite_error and attempt < max_retries:
                    wait_time = (attempt + 1) * 0.5
                    logger.debug(
                        f"SQLite cache retry {attempt + 1}/{max_retries} in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                    continue
                raise

        # This should never be reached, but satisfy type checker
        raise requests.RequestException("Max retries exceeded")

    def _to_dataframe(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> pd.DataFrame:
        """Convert JSON response to pandas DataFrame."""
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise ValueError("Data must be a list or dict for DataFrame conversion")

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self.session.cache.clear()
        logger.info("Cache cleared")

    # -------------------------------------------------------------------------
    # Search Methods
    # -------------------------------------------------------------------------

    def search_symbol(
        self,
        query: str,
        limit: int = 5,
        exchange: Optional[str] = "NASDAQ",
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Search for stock symbols matching a query string.

        Args:
            query: Search query (e.g., "AAPL" or "Apple").
            limit: Maximum results to return.
            exchange: Exchange to search (e.g., "NASDAQ", "NYSE").
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            List of matching symbols or DataFrame.
        """
        params: Dict[str, Any] = {"query": query, "limit": limit}
        if exchange:
            params["exchange"] = exchange
        data = self._get("search-symbol", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def search_company_name(
        self,
        query: str,
        limit: int = 5,
        exchange: Optional[str] = "NASDAQ",
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Search for companies by name.

        Args:
            query: Company name to search.
            limit: Maximum results to return.
            exchange: Exchange to filter by.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            List of matching companies or DataFrame.
        """
        params: Dict[str, Any] = {"query": query, "limit": limit}
        if exchange:
            params["exchange"] = exchange
        data = self._get("search-name", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Quote and Price Data
    # -------------------------------------------------------------------------

    def get_quote(
        self,
        symbol: str,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get current stock quote.

        Args:
            symbol: Stock ticker symbol.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Quote data including price, volume, day change.
        """
        if not isinstance(symbol, str):
            raise ValueError("The 'symbol' parameter must be a string.")
        data = self._get("quote", params={"symbol": symbol})
        return self._to_dataframe(data) if return_type == "df" else data

    def get_eod_adj(
        self,
        symbol: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get dividend-adjusted end-of-day historical prices.

        Args:
            symbol: Stock ticker symbol.
            date_from: Start date (YYYY-MM-DD format).
            date_to: End date (YYYY-MM-DD format).
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Historical price data.
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        data = self._get("historical-price-eod/dividend-adjusted", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Company Fundamentals
    # -------------------------------------------------------------------------

    def get_company_profile(
        self,
        symbol: str,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get company profile information.

        Args:
            symbol: Stock ticker symbol.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Company profile including sector, industry, description, market cap.
        """
        data = self._get("profile", params={"symbol": symbol})
        return self._to_dataframe(data) if return_type == "df" else data

    def get_enterprise_values(
        self,
        symbol: str,
        limit: int = 4,
        period: str = "quarter",
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get enterprise value metrics.

        Args:
            symbol: Stock ticker symbol.
            limit: Number of periods to return.
            period: "quarter" or "annual".
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Enterprise value data including market cap, debt, cash.
        """
        params = {"symbol": symbol, "limit": limit, "period": period}
        data = self._get("enterprise-values", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def get_financial_ratios(
        self,
        symbol: str,
        limit: int = 1,
        period: str = "FY",
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get financial ratios.

        Args:
            symbol: Stock ticker symbol.
            limit: Number of periods to return.
            period: "FY" for annual, "quarter" for quarterly.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Financial ratios including P/E, P/B, ROE, debt/equity.
        """
        params = {"symbol": symbol, "limit": limit, "period": period}
        data = self._get("ratios", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Growth and Financial Data
    # -------------------------------------------------------------------------

    def get_financial_growth(
        self,
        symbol: str,
        limit: int = 4,
        period: str = "quarter",
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get financial growth metrics.

        Args:
            symbol: Stock ticker symbol.
            limit: Number of periods to return.
            period: "quarter" or "annual".
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Growth metrics including revenue, earnings, EPS growth rates.
        """
        params = {"symbol": symbol, "limit": limit, "period": period}
        data = self._get("financial-growth", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def get_earnings(
        self,
        symbol: str,
        limit: int = 3,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get earnings data.

        Args:
            symbol: Stock ticker symbol.
            limit: Number of earnings reports to return.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Earnings data including EPS, revenue, surprises.
        """
        data = self._get("earnings", params={"symbol": symbol, "limit": limit})
        return self._to_dataframe(data) if return_type == "df" else data

    def get_revenue_product_segmentation(
        self,
        symbol: str,
        period: str = "annual",
        structure: str = "flat",
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get revenue breakdown by product segment.

        Args:
            symbol: Stock ticker symbol.
            period: "annual" or "quarter".
            structure: "flat" or "nested".
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Revenue segmentation data.
        """
        params = {"symbol": symbol, "period": period, "structure": structure}
        data = self._get("revenue-product-segmentation", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Analyst and Market Data
    # -------------------------------------------------------------------------

    def get_price_target_consensus(
        self,
        symbol: str,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get analyst price target consensus.

        Args:
            symbol: Stock ticker symbol.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Consensus price targets (high, low, average).
        """
        data = self._get("price-target-consensus", params={"symbol": symbol})
        return self._to_dataframe(data) if return_type == "df" else data

    def get_stock_news(
        self,
        symbol: str,
        limit: int = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 0,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get stock-related news articles.

        Args:
            symbol: Stock ticker symbol.
            limit: Maximum articles to return.
            date_from: Start date (YYYY-MM-DD).
            date_to: End date (YYYY-MM-DD).
            page: Page number for pagination.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            News articles for the stock.
        """
        params: Dict[str, Any] = {"symbols": symbol, "limit": limit, "page": page}
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        data = self._get("news/stock", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def get_price_target_news(
        self,
        symbol: str,
        limit: int = 50,
        page: int = 0,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get price target news articles.

        Args:
            symbol: Stock ticker symbol.
            limit: Maximum articles to return.
            page: Page number for pagination.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Price target news articles.
        """
        params = {"symbols": symbol, "limit": limit, "page": page}
        data = self._get("news/price-target-news", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Stock Screening
    # -------------------------------------------------------------------------

    def get_screened_stocks(
        self,
        market_cap_more_than: Optional[int] = None,
        market_cap_lower_than: Optional[int] = None,
        volume_more_than: Optional[int] = None,
        volume_lower_than: Optional[int] = None,
        price_more_than: Optional[float] = None,
        price_lower_than: Optional[float] = None,
        beta_more_than: Optional[float] = None,
        beta_lower_than: Optional[float] = None,
        dividend_more_than: Optional[float] = None,
        dividend_lower_than: Optional[float] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        exchange: Optional[str] = None,
        country: Optional[str] = None,
        is_etf: bool = False,
        is_fund: bool = False,
        is_actively_trading: bool = True,
        limit: int = 100,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Screen stocks based on various criteria.

        Args:
            market_cap_more_than: Minimum market cap (e.g., 1000000000 for $1B).
            market_cap_lower_than: Maximum market cap.
            volume_more_than: Minimum average volume.
            volume_lower_than: Maximum average volume.
            price_more_than: Minimum stock price.
            price_lower_than: Maximum stock price.
            beta_more_than: Minimum beta (volatility vs market).
            beta_lower_than: Maximum beta.
            dividend_more_than: Minimum dividend yield (e.g., 0.02 for 2%).
            dividend_lower_than: Maximum dividend yield.
            sector: Filter by sector (e.g., "Technology", "Healthcare").
            industry: Filter by industry.
            exchange: Exchange (e.g., "NASDAQ", "NYSE").
            country: Country code (e.g., "US").
            is_etf: Include ETFs.
            is_fund: Include funds.
            is_actively_trading: Only actively trading stocks.
            limit: Maximum results to return.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            List of stocks matching criteria or DataFrame.
        """
        # Map to FMP API parameter names
        params: Dict[str, Any] = {
            "marketCapMoreThan": market_cap_more_than,
            "marketCapLowerThan": market_cap_lower_than,
            "volumeMoreThan": volume_more_than,
            "volumeLowerThan": volume_lower_than,
            "priceMoreThan": price_more_than,
            "priceLowerThan": price_lower_than,
            "betaMoreThan": beta_more_than,
            "betaLowerThan": beta_lower_than,
            "dividendMoreThan": dividend_more_than,
            "dividendLowerThan": dividend_lower_than,
            "sector": sector,
            "industry": industry,
            "exchange": exchange,
            "country": country,
            "isEtf": is_etf,
            "isFund": is_fund,
            "isActivelyTrading": is_actively_trading,
            "limit": limit,
        }
        # Remove None values so FMP uses its defaults
        params = {k: v for k, v in params.items() if v is not None}

        data = self._get("company-screener", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Historical Price Data (for Backtesting)
    # -------------------------------------------------------------------------

    def get_historical_price_full(
        self,
        symbol: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get full historical EOD prices (up to 5 years on Starter plan).

        Returns OHLCV data with change, changePercent, and vwap.

        Args:
            symbol: Stock ticker symbol.
            date_from: Start date (YYYY-MM-DD format).
            date_to: End date (YYYY-MM-DD format).
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Historical price data with OHLCV and additional metrics.
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        data = self._get("historical-price-eod/full", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def get_historical_market_cap(
        self,
        symbol: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical market capitalization data.

        Essential for point-in-time size screening in backtesting.

        Args:
            symbol: Stock ticker symbol.
            date_from: Start date (YYYY-MM-DD format).
            date_to: End date (YYYY-MM-DD format).
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Historical market cap data.
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        data = self._get("historical-market-capitalization", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Historical Fundamental Data (for Backtesting)
    # -------------------------------------------------------------------------

    def get_income_statement(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 5,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical income statements.

        Includes filingDate for point-in-time accuracy.
        Period: 'annual' on Starter, 'quarter' on Premium+.

        Args:
            symbol: Stock ticker symbol.
            period: "annual" or "quarter".
            limit: Number of periods to return.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Income statement data including revenue, net income, EPS.
        """
        params = {"symbol": symbol, "period": period, "limit": limit}
        data = self._get("income-statement", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def get_balance_sheet(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 5,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical balance sheet statements.

        Args:
            symbol: Stock ticker symbol.
            period: "annual" or "quarter".
            limit: Number of periods to return.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Balance sheet data including assets, liabilities, equity.
        """
        params = {"symbol": symbol, "period": period, "limit": limit}
        data = self._get("balance-sheet-statement", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def get_cash_flow_statement(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 5,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical cash flow statements.

        Args:
            symbol: Stock ticker symbol.
            period: "annual" or "quarter".
            limit: Number of periods to return.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Cash flow data including operating, investing, financing flows.
        """
        params = {"symbol": symbol, "period": period, "limit": limit}
        data = self._get("cash-flow-statement", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def get_key_metrics(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 5,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical key metrics (PE, PB, EV/EBITDA, ROE, etc.).

        Args:
            symbol: Stock ticker symbol.
            period: "annual" or "quarter".
            limit: Number of periods to return.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Key financial metrics including valuation and profitability ratios.
        """
        params = {"symbol": symbol, "period": period, "limit": limit}
        data = self._get("key-metrics", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    def get_income_statement_growth(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 5,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical income statement growth rates.

        Args:
            symbol: Stock ticker symbol.
            period: "annual" or "quarter".
            limit: Number of periods to return.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Growth rates for revenue, net income, EPS, etc.
        """
        params = {"symbol": symbol, "period": period, "limit": limit}
        data = self._get("income-statement-growth", params=params)
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Index Constituents (for Survivorship-Safe Backtesting)
    # -------------------------------------------------------------------------

    def get_sp500_constituents(
        self,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get current S&P 500 constituents.

        Returns:
            List of current S&P 500 member stocks.
        """
        data = self._get("sp500-constituent")
        return self._to_dataframe(data) if return_type == "df" else data

    def get_historical_sp500_constituents(
        self,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical S&P 500 constituent changes.

        Returns additions/removals with dates for survivorship-safe backtesting.

        Returns:
            Historical additions and removals from the S&P 500.
        """
        data = self._get("historical-sp500-constituent")
        return self._to_dataframe(data) if return_type == "df" else data

    def get_nasdaq_constituents(
        self,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get current NASDAQ 100 constituents.

        Returns:
            List of current NASDAQ 100 member stocks.
        """
        data = self._get("nasdaq-constituent")
        return self._to_dataframe(data) if return_type == "df" else data

    def get_historical_nasdaq_constituents(
        self,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical NASDAQ 100 constituent changes.

        Returns:
            Historical additions and removals from the NASDAQ 100.
        """
        data = self._get("historical-nasdaq-constituent")
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Corporate Events (for Price Adjustments)
    # -------------------------------------------------------------------------

    def get_stock_splits(
        self,
        symbol: str,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical stock splits for price adjustment.

        Args:
            symbol: Stock ticker symbol.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Historical stock split data.
        """
        data = self._get("splits", params={"symbol": symbol})
        return self._to_dataframe(data) if return_type == "df" else data

    def get_dividends(
        self,
        symbol: str,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical dividends for total return calculation.

        Args:
            symbol: Stock ticker symbol.
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Historical dividend data.
        """
        data = self._get("dividends", params={"symbol": symbol})
        return self._to_dataframe(data) if return_type == "df" else data

    # -------------------------------------------------------------------------
    # Market Context (for Benchmarking)
    # -------------------------------------------------------------------------

    def get_historical_sector_performance(
        self,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical sector performance.

        Returns:
            Historical performance data by sector.
        """
        data = self._get("historical-sector-performance")
        return self._to_dataframe(data) if return_type == "df" else data

    def get_index_historical_price(
        self,
        symbol: str = "^GSPC",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        return_type: str = "json",
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Get historical index prices (S&P 500, NASDAQ, etc.).

        Args:
            symbol: Index symbol (e.g., "^GSPC" for S&P 500, "^IXIC" for NASDAQ).
            date_from: Start date (YYYY-MM-DD format).
            date_to: End date (YYYY-MM-DD format).
            return_type: "json" for dict/list, "df" for DataFrame.

        Returns:
            Historical index price data.
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        data = self._get("historical-price-eod/full", params=params)
        return self._to_dataframe(data) if return_type == "df" else data
