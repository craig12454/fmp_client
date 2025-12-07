"""Sample API responses for testing FMP client endpoints."""

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

SAMPLE_SEARCH_RESPONSE = [
    {"symbol": "AAPL", "name": "Apple Inc.", "currency": "USD", "stockExchange": "NASDAQ"},
    {"symbol": "AAPD", "name": "Direxion Daily AAPL Bear 1X Shares", "currency": "USD", "stockExchange": "NASDAQ"},
]

SAMPLE_EOD_ADJ_RESPONSE = [
    {"date": "2024-01-15", "open": 182.16, "high": 185.33, "low": 181.87, "close": 184.10, "adjClose": 184.10, "volume": 65076000},
    {"date": "2024-01-14", "open": 181.50, "high": 182.55, "low": 180.00, "close": 182.16, "adjClose": 182.16, "volume": 58742000},
]

SAMPLE_ENTERPRISE_VALUES_RESPONSE = [
    {
        "symbol": "AAPL",
        "date": "2024-01-15",
        "stockPrice": 184.10,
        "numberOfShares": 15550000000,
        "marketCapitalization": 2862000000000,
        "minusCashAndCashEquivalents": 61500000000,
        "addTotalDebt": 111000000000,
        "enterpriseValue": 2911500000000,
    }
]

SAMPLE_FINANCIAL_RATIOS_RESPONSE = [
    {
        "symbol": "AAPL",
        "date": "2023-09-30",
        "period": "FY",
        "priceEarningsRatio": 28.5,
        "priceToBookRatio": 45.2,
        "returnOnEquity": 1.56,
        "debtEquityRatio": 1.81,
    }
]

SAMPLE_FINANCIAL_GROWTH_RESPONSE = [
    {
        "symbol": "AAPL",
        "date": "2023-09-30",
        "revenueGrowth": 0.02,
        "netIncomeGrowth": 0.05,
        "epsgrowth": 0.08,
    }
]

SAMPLE_EARNINGS_RESPONSE = [
    {
        "symbol": "AAPL",
        "date": "2024-01-25",
        "epsActual": 2.18,
        "epsEstimated": 2.10,
        "revenueActual": 119580000000,
        "revenueEstimated": 117900000000,
    }
]

SAMPLE_REVENUE_SEGMENTATION_RESPONSE = [
    {"date": "2023-09-30", "iPhone": 200000000000, "Mac": 29000000000, "iPad": 28000000000, "Services": 85000000000}
]

SAMPLE_PRICE_TARGET_CONSENSUS_RESPONSE = [
    {"symbol": "AAPL", "targetHigh": 250.00, "targetLow": 150.00, "targetConsensus": 200.00, "targetMedian": 195.00}
]

SAMPLE_STOCK_NEWS_RESPONSE = [
    {
        "symbol": "AAPL",
        "publishedDate": "2024-01-15T10:30:00.000Z",
        "title": "Apple Announces New Product",
        "text": "Apple Inc. announced a new product...",
        "url": "https://example.com/news/1",
    }
]

SAMPLE_SCREENED_STOCKS_RESPONSE = [
    {"symbol": "AAPL", "companyName": "Apple Inc.", "marketCap": 2862000000000, "sector": "Technology", "price": 184.10},
    {"symbol": "MSFT", "companyName": "Microsoft Corporation", "marketCap": 2800000000000, "sector": "Technology", "price": 380.50},
]

SAMPLE_HISTORICAL_PRICE_RESPONSE = [
    {"date": "2024-01-15", "open": 182.16, "high": 185.33, "low": 181.87, "close": 184.10, "volume": 65076000, "vwap": 183.50},
    {"date": "2024-01-14", "open": 181.50, "high": 182.55, "low": 180.00, "close": 182.16, "volume": 58742000, "vwap": 181.45},
]

SAMPLE_HISTORICAL_MARKET_CAP_RESPONSE = [
    {"symbol": "AAPL", "date": "2024-01-15", "marketCap": 2862000000000},
    {"symbol": "AAPL", "date": "2024-01-14", "marketCap": 2830000000000},
]

SAMPLE_INCOME_STATEMENT_RESPONSE = [
    {
        "symbol": "AAPL",
        "date": "2023-09-30",
        "period": "FY",
        "revenue": 383000000000,
        "netIncome": 96000000000,
        "eps": 6.13,
        "filingDate": "2023-11-03",
    }
]

SAMPLE_BALANCE_SHEET_RESPONSE = [
    {
        "symbol": "AAPL",
        "date": "2023-09-30",
        "period": "FY",
        "totalAssets": 352000000000,
        "totalLiabilities": 290000000000,
        "totalStockholdersEquity": 62000000000,
    }
]

SAMPLE_CASH_FLOW_RESPONSE = [
    {
        "symbol": "AAPL",
        "date": "2023-09-30",
        "period": "FY",
        "operatingCashFlow": 110000000000,
        "capitalExpenditure": -10000000000,
        "freeCashFlow": 100000000000,
    }
]

SAMPLE_KEY_METRICS_RESPONSE = [
    {
        "symbol": "AAPL",
        "date": "2023-09-30",
        "period": "FY",
        "peRatio": 28.5,
        "pbRatio": 45.2,
        "evToEbitda": 22.3,
        "roe": 1.56,
    }
]

SAMPLE_SP500_CONSTITUENTS_RESPONSE = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "subSector": "Consumer Electronics"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "subSector": "Software"},
]

SAMPLE_HISTORICAL_SP500_RESPONSE = [
    {"dateAdded": "2019-06-07", "addedSecurity": "AAPL", "removedSecurity": "XYZ", "reason": "Market cap"},
]

SAMPLE_NASDAQ_CONSTITUENTS_RESPONSE = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
]

SAMPLE_STOCK_SPLITS_RESPONSE = [
    {"symbol": "AAPL", "date": "2020-08-31", "numerator": 4, "denominator": 1},
    {"symbol": "AAPL", "date": "2014-06-09", "numerator": 7, "denominator": 1},
]

SAMPLE_DIVIDENDS_RESPONSE = [
    {"symbol": "AAPL", "date": "2024-01-12", "dividend": 0.24, "recordDate": "2024-01-15", "paymentDate": "2024-02-15"},
]

SAMPLE_SECTOR_PERFORMANCE_RESPONSE = [
    {"date": "2024-01-15", "sector": "Technology", "changesPercentage": 2.5},
    {"date": "2024-01-15", "sector": "Healthcare", "changesPercentage": 1.2},
]
