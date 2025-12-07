"""FMP Client - Python client for Financial Modeling Prep API.

A feature-rich Python client for the Financial Modeling Prep (FMP) API
with built-in caching, retry logic, and DataFrame support.

Example:
    >>> from fmp_client import FMPClient
    >>> client = FMPClient(api_key="your-api-key")
    >>> quote = client.get_quote("AAPL")
    >>> profile = client.get_company_profile("NVDA", return_type="df")
"""

from fmp_client.client import FMPClient, TooManyRequestsException

__version__ = "0.1.0"
__all__ = ["FMPClient", "TooManyRequestsException", "__version__"]
