"""Market Analyst Agent - Technical analysis using OHLCV data and indicators."""

from datetime import datetime, timedelta

from ..dataflows.interface import route_to_vendor
from ..indicators.technical import compute_all_indicators


MARKET_ANALYST_PROMPT = """You are a skilled market analyst specializing in technical analysis.

Your task is to analyze the stock price data and technical indicators for {symbol} and provide a comprehensive market analysis report.

## Stock Data (OHLCV)
{stock_data}

## Technical Indicators
{indicators}

## Analysis Instructions
1. Identify the current trend (uptrend, downtrend, or sideways)
2. Analyze momentum using MACD and RSI
3. Assess volatility using Bollinger Bands and ATR
4. Identify key support and resistance levels
5. Provide a technical outlook (bullish, bearish, or neutral)

Write your analysis in a structured markdown format with clear sections.
"""


def get_market_analysis(symbol: str, trade_date: str, days: int = 90) -> str:
    """Run market analysis for a given symbol.

    Args:
        symbol: Ticker symbol
        trade_date: Analysis date in yyyy-mm-dd format
        days: Number of days of historical data to fetch

    Returns:
        Market analysis report string
    """
    # Calculate date range
    end_date = trade_date
    start_dt = datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=days)
    start_date = start_dt.strftime("%Y-%m-%d")

    # Fetch OHLCV data
    stock_data = route_to_vendor("get_stock_data", symbol, start_date, end_date)

    if stock_data.startswith("No data"):
        return f"Unable to analyze {symbol}: no data available for the specified period."

    # Parse CSV and compute indicators
    import io
    import pandas as pd

    # Skip comment lines
    lines = [l for l in stock_data.split("\n") if not l.startswith("#") and l.strip()]
    csv_content = "\n".join(lines)

    df = pd.read_csv(io.StringIO(csv_content), index_col=0, parse_dates=True)
    df_indicators = compute_all_indicators(df)

    # Format indicators for display
    indicator_cols = [
        "SMA_20", "SMA_50", "EMA_12", "EMA_26",
        "MACD", "MACD_Signal", "MACD_Histogram",
        "RSI", "BB_Upper", "BB_Middle", "BB_Lower", "ATR",
        "VWAP", "OBV",
    ]
    indicators_str = df_indicators[indicator_cols].tail(10).to_string()

    return MARKET_ANALYST_PROMPT.format(
        symbol=symbol,
        stock_data=stock_data,
        indicators=indicators_str,
    )
