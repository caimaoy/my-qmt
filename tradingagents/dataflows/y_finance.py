"""yfinance data provider for stock prices and news."""

import time
from datetime import datetime
from typing import Annotated

import pandas as pd
import yfinance as yf

from .interface import register_vendor

# Rate limit retry settings
_MAX_RETRIES = 3
_RETRY_DELAY_BASE = 2  # exponential backoff base


def _yf_retry(func, max_retries=_MAX_RETRIES):
    """Retry wrapper for yfinance with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(_RETRY_DELAY_BASE ** attempt)
                continue
            raise


@register_vendor("get_stock_data", "yfinance", "core_stock_apis")
def get_YFin_data_online(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Fetch OHLCV data from Yahoo Finance via yfinance.

    Args:
        symbol: Ticker symbol, e.g. "AAPL", "0700.HK", "600519.SS"
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format

    Returns:
        CSV string with OHLCV data
    """
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    ticker = yf.Ticker(symbol.upper())
    data = _yf_retry(lambda: ticker.history(start=start_date, end=end_date))

    if data.empty:
        return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"

    # Remove timezone info
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    # Round numeric columns
    numeric_columns = ["Open", "High", "Low", "Close", "Adj Close"]
    for col in numeric_columns:
        if col in data.columns:
            data[col] = data[col].round(2)

    csv_string = data.to_csv()
    header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(data)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    return header + csv_string


@register_vendor("get_stock_data_cached", "yfinance", "core_stock_apis")
def load_ohlcv(symbol: str, curr_date: str, years: int = 5) -> pd.DataFrame:
    """Load OHLCV data with caching for technical indicator calculation.

    Args:
        symbol: Ticker symbol
        curr_date: Current date in yyyy-mm-dd format (filters data <= this date)
        years: Number of years of historical data to fetch

    Returns:
        DataFrame with OHLCV data
    """
    from datetime import timedelta

    end_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=years * 365)

    ticker = yf.Ticker(symbol.upper())
    data = _yf_retry(
        lambda: ticker.history(
            start=start_dt.strftime("%Y-%m-%d"),
            end=curr_date,
        )
    )

    if data.empty:
        return pd.DataFrame()

    # Remove timezone
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    # Filter to <= curr_date
    data = data[data.index <= curr_date]

    return data
