"""Technical indicators calculation using pandas.

Implements 8 core indicators:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- MACD (Moving Average Convergence Divergence)
- RSI (Relative Strength Index)
- Bollinger Bands
- ATR (Average True Range)
- VWAP (Volume Weighted Average Price)
- OBV (On Balance Volume)
"""

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD (Moving Average Convergence Divergence).

    Returns:
        DataFrame with columns: MACD, Signal, Histogram
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line

    return pd.DataFrame(
        {"MACD": macd_line, "Signal": signal_line, "Histogram": histogram},
        index=series.index,
    )


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def bollinger_bands(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """Bollinger Bands.

    Returns:
        DataFrame with columns: Middle, Upper, Lower
    """
    middle = sma(series, window)
    std = series.rolling(window=window).std()

    return pd.DataFrame(
        {
            "Middle": middle,
            "Upper": middle + (std * num_std),
            "Lower": middle - (std * num_std),
        },
        index=series.index,
    )


def atr(
    high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14
) -> pd.Series:
    """Average True Range (ATR)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=window).mean()


def vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> pd.Series:
    """Volume Weighted Average Price (VWAP).

    VWAP = Cumulative(Price * Volume) / Cumulative(Volume)

    Note: This calculates a running VWAP from the start of the data.
    For intraday VWAP, reset at each trading session.
    """
    typical_price = (high + low + close) / 3
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    return cumulative_tp_vol / cumulative_vol


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On Balance Volume (OBV).

    OBV adds volume on up days and subtracts volume on down days.
    """
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    obv_values = (volume * direction).cumsum()
    return obv_values


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all 8 indicators for a DataFrame with OHLCV columns.

    Args:
        df: DataFrame with columns: Open, High, Low, Close, Volume

    Returns:
        DataFrame with original columns + all indicator columns
    """
    result = df.copy()

    # SMA
    result["SMA_20"] = sma(df["Close"], 20)
    result["SMA_50"] = sma(df["Close"], 50)

    # EMA
    result["EMA_12"] = ema(df["Close"], 12)
    result["EMA_26"] = ema(df["Close"], 26)

    # MACD
    macd_df = macd(df["Close"])
    result["MACD"] = macd_df["MACD"]
    result["MACD_Signal"] = macd_df["Signal"]
    result["MACD_Histogram"] = macd_df["Histogram"]

    # RSI
    result["RSI"] = rsi(df["Close"])

    # Bollinger Bands
    bb = bollinger_bands(df["Close"])
    result["BB_Upper"] = bb["Upper"]
    result["BB_Middle"] = bb["Middle"]
    result["BB_Lower"] = bb["Lower"]

    # ATR
    result["ATR"] = atr(df["High"], df["Low"], df["Close"])

    # VWAP
    result["VWAP"] = vwap(df["High"], df["Low"], df["Close"], df["Volume"])

    # OBV
    result["OBV"] = obv(df["Close"], df["Volume"])

    return result
