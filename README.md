# FMP Client

A Python client for the [Financial Modeling Prep (FMP)](https://financialmodelingprep.com/) API with built-in caching, retry logic, and DataFrame support.

## Features

- **SQLite Caching**: Automatic response caching with configurable TTL
- **Retry Logic**: Automatic retries for transient errors with exponential backoff
- **DataFrame Support**: Return data as pandas DataFrames or raw JSON
- **Flexible Configuration**: API key via parameter, config file, or environment variable
- **Type Hints**: Full type annotations for IDE support

## Installation

```bash
pip install fmp-client
```

Or install from source:

```bash
git clone https://github.com/yourusername/fmp-client.git
cd fmp-client
pip install -e .
```

## Quick Start

```python
from fmp_client import FMPClient

# Initialize with API key
client = FMPClient(api_key="your-fmp-api-key")

# Get a stock quote
quote = client.get_quote("AAPL")
print(quote)

# Get company profile as DataFrame
profile = client.get_company_profile("NVDA", return_type="df")
print(profile)
```

## Configuration

### Option 1: Direct API Key

```python
client = FMPClient(api_key="your-api-key")
```

### Option 2: Environment Variable

```bash
export FMP_API_KEY="your-api-key"
```

```python
client = FMPClient()  # Reads from FMP_API_KEY
```

### Option 3: Config File

Create a `config.yaml`:

```yaml
fmp:
  api_key: "your-api-key"
  cache:
    backend: "sqlite"
    name: "fmp_cache"
    expire_after: 3600  # 1 hour
```

```python
client = FMPClient(config_path="config.yaml")
```

### Option 4: Config Dict

```python
config = {
    "fmp": {
        "api_key": "your-api-key",
        "cache": {
            "expire_after": 600
        }
    }
}
client = FMPClient(config=config)
```

## API Methods

### Search

```python
# Search by symbol
results = client.search_symbol("AAPL", limit=5)

# Search by company name
results = client.search_company_name("Apple", limit=5, exchange="NASDAQ")
```

### Quotes and Prices

```python
# Current quote
quote = client.get_quote("AAPL")

# Historical prices (dividend-adjusted)
history = client.get_eod_adj("AAPL", date_from="2024-01-01", date_to="2024-12-01")
```

### Company Fundamentals

```python
# Company profile
profile = client.get_company_profile("NVDA")

# Enterprise values
ev = client.get_enterprise_values("NVDA", limit=4, period="quarter")

# Financial ratios
ratios = client.get_financial_ratios("NVDA", period="FY")
```

### Growth and Financials

```python
# Financial growth metrics
growth = client.get_financial_growth("NVDA", limit=4, period="quarter")

# Earnings data
earnings = client.get_earnings("NVDA", limit=3)

# Revenue segmentation
segments = client.get_revenue_product_segmentation("NVDA", period="annual")
```

### Analyst Data

```python
# Price target consensus
targets = client.get_price_target_consensus("NVDA")

# Stock news
news = client.get_stock_news("NVDA", limit=10)

# Price target news
pt_news = client.get_price_target_news("NVDA", limit=10)
```

### Stock Screening

```python
# Screen for growth stocks
stocks = client.get_screened_stocks(
    market_cap_more_than=1_000_000_000,  # $1B+
    price_more_than=5,
    price_lower_than=500,
    sector="Technology",
    country="US",
    is_actively_trading=True,
    limit=100
)
```

## Return Types

All methods support two return formats:

```python
# JSON (default) - returns dict or list
data = client.get_quote("AAPL")

# DataFrame - returns pandas DataFrame
df = client.get_quote("AAPL", return_type="df")
```

## Caching

The client uses SQLite-based caching by default:

```python
# Custom cache settings
client = FMPClient(
    api_key="your-key",
    cache_backend="sqlite",
    cache_name="my_cache",
    cache_expire_after=3600  # 1 hour
)

# Clear cache manually
client.clear_cache()
```

## Error Handling

```python
from fmp_client import FMPClient, TooManyRequestsException
import requests

client = FMPClient(api_key="your-key")

try:
    quote = client.get_quote("AAPL")
except TooManyRequestsException:
    print("Rate limit exceeded - wait before retrying")
except requests.RequestException as e:
    print(f"API request failed: {e}")
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/fmp_client

# Linting
ruff check src/fmp_client
```

## License

MIT License
