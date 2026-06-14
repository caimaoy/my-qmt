"""yfinance 财务数据工具: 基本面、资产负债表、现金流、利润表、内幕交易"""

import time
from datetime import datetime
from typing import Annotated

import pandas as pd
import yfinance as yf

from .interface import register_vendor

# Rate limit retry settings
_MAX_RETRIES = 3
_RETRY_DELAY_BASE = 2


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


def _get_ticker(symbol: str) -> yf.Ticker:
    """Get yfinance Ticker object."""
    return yf.Ticker(symbol.upper())


# ============================================================
# 公司基本面概览
# ============================================================

@register_vendor("get_fundamentals", "yfinance", "fundamental_data")
def get_fundamentals_yfinance(
    symbol: Annotated[str, "股票代码"],
) -> str:
    """获取公司基本面概览

    Args:
        symbol: 股票代码，如 "AAPL", "600519.SS"

    Returns:
        格式化的基本面字符串
    """
    ticker = _get_ticker(symbol)
    info = _yf_retry(lambda: ticker.info)

    if not info:
        return f"未找到 {symbol} 的基本面数据"

    # 提取关键指标
    fields = {
        "公司名称": info.get("longName", "N/A"),
        "行业": info.get("industry", "N/A"),
        "板块": info.get("sector", "N/A"),
        "市值": info.get("marketCap", "N/A"),
        "市盈率 (TTM)": info.get("trailingPE", "N/A"),
        "市盈率 (Forward)": info.get("forwardPE", "N/A"),
        "市净率": info.get("priceToBook", "N/A"),
        "股息率": info.get("dividendYield", "N/A"),
        "EPS (TTM)": info.get("trailingEps", "N/A"),
        "收入 (TTM)": info.get("totalRevenue", "N/A"),
        "净利润率": info.get("profitMargins", "N/A"),
        "ROE": info.get("returnOnEquity", "N/A"),
        "ROA": info.get("returnOnAssets", "N/A"),
        "负债/权益": info.get("debtToEquity", "N/A"),
        "自由现金流": info.get("freeCashflow", "N/A"),
        "52周高点": info.get("fiftyTwoWeekHigh", "N/A"),
        "52周低点": info.get("fiftyTwoWeekLow", "N/A"),
        "50日均线": info.get("fiftyDayAverage", "N/A"),
        "200日均线": info.get("twoHundredDayAverage", "N/A"),
        "Beta": info.get("beta", "N/A"),
        "分析师目标价": info.get("targetMeanPrice", "N/A"),
        "分析师推荐": info.get("recommendationKey", "N/A"),
    }

    lines = [f"# {symbol} 基本面概览\n"]
    for key, value in fields.items():
        if isinstance(value, (int, float)):
            if abs(value) >= 1e9:
                lines.append(f"| {key} | {value/1e9:.2f}B |")
            elif abs(value) >= 1e6:
                lines.append(f"| {key} | {value/1e6:.2f}M |")
            elif isinstance(value, float) and abs(value) < 1:
                lines.append(f"| {key} | {value*100:.2f}% |")
            else:
                lines.append(f"| {key} | {value} |")
        else:
            lines.append(f"| {key} | {value} |")

    header = "| 指标 | 数值 |\n|------|------|\n"
    return "\n".join(lines[:1]) + header + "\n".join(lines[1:])


# ============================================================
# 资产负债表
# ============================================================

@register_vendor("get_balance_sheet", "yfinance", "fundamental_data")
def get_balance_sheet_yfinance(
    symbol: Annotated[str, "股票代码"],
    limit: Annotated[int, "返回期数"] = 4,
) -> str:
    """获取资产负债表

    Args:
        symbol: 股票代码
        limit: 返回最近几期的数据

    Returns:
        格式化的资产负债表字符串
    """
    ticker = _get_ticker(symbol)
    bs = _yf_retry(lambda: ticker.balance_sheet)

    if bs is None or bs.empty:
        return f"未找到 {symbol} 的资产负债表"

    # 转置并取最近几期
    bs_transposed = bs.T.head(limit)

    lines = [f"# {symbol} 资产负债表\n"]
    lines.append("| 指标 | " + " | ".join([str(d.date()) for d in bs_transposed.index]) + " |")
    lines.append("|------|" + "|".join(["------"] * len(bs_transposed)) + "|")

    # 关键科目
    key_items = [
        "Total Assets", "Total Liabilities Net Minority Interest",
        "Total Equity Gross Minority Interest", "Cash And Cash Equivalents",
        "Total Debt", "Net Debt", "Working Capital",
    ]

    for item in key_items:
        if item in bs_transposed.columns:
            values = []
            for val in bs_transposed[item]:
                if pd.isna(val):
                    values.append("N/A")
                elif abs(val) >= 1e9:
                    values.append(f"{val/1e9:.2f}B")
                elif abs(val) >= 1e6:
                    values.append(f"{val/1e6:.2f}M")
                else:
                    values.append(f"{val:.0f}")
            lines.append(f"| {item} | " + " | ".join(values) + " |")

    return "\n".join(lines)


# ============================================================
# 现金流量表
# ============================================================

@register_vendor("get_cashflow", "yfinance", "fundamental_data")
def get_cashflow_yfinance(
    symbol: Annotated[str, "股票代码"],
    limit: Annotated[int, "返回期数"] = 4,
) -> str:
    """获取现金流量表

    Args:
        symbol: 股票代码
        limit: 返回最近几期的数据

    Returns:
        格式化的现金流量表字符串
    """
    ticker = _get_ticker(symbol)
    cf = _yf_retry(lambda: ticker.cashflow)

    if cf is None or cf.empty:
        return f"未找到 {symbol} 的现金流量表"

    cf_transposed = cf.T.head(limit)

    lines = [f"# {symbol} 现金流量表\n"]
    lines.append("| 指标 | " + " | ".join([str(d.date()) for d in cf_transposed.index]) + " |")
    lines.append("|------|" + "|".join(["------"] * len(cf_transposed)) + "|")

    key_items = [
        "Operating Cash Flow", "Investing Cash Flow", "Financing Cash Flow",
        "Free Cash Flow", "Capital Expenditure",
    ]

    for item in key_items:
        if item in cf_transposed.columns:
            values = []
            for val in cf_transposed[item]:
                if pd.isna(val):
                    values.append("N/A")
                elif abs(val) >= 1e9:
                    values.append(f"{val/1e9:.2f}B")
                elif abs(val) >= 1e6:
                    values.append(f"{val/1e6:.2f}M")
                else:
                    values.append(f"{val:.0f}")
            lines.append(f"| {item} | " + " | ".join(values) + " |")

    return "\n".join(lines)


# ============================================================
# 利润表
# ============================================================

@register_vendor("get_income_statement", "yfinance", "fundamental_data")
def get_income_statement_yfinance(
    symbol: Annotated[str, "股票代码"],
    limit: Annotated[int, "返回期数"] = 4,
) -> str:
    """获取利润表

    Args:
        symbol: 股票代码
        limit: 返回最近几期的数据

    Returns:
        格式化的利润表字符串
    """
    ticker = _get_ticker(symbol)
    income = _yf_retry(lambda: ticker.income_stmt)

    if income is None or income.empty:
        return f"未找到 {symbol} 的利润表"

    income_transposed = income.T.head(limit)

    lines = [f"# {symbol} 利润表\n"]
    lines.append("| 指标 | " + " | ".join([str(d.date()) for d in income_transposed.index]) + " |")
    lines.append("|------|" + "|".join(["------"] * len(income_transposed)) + "|")

    key_items = [
        "Total Revenue", "Cost Of Revenue", "Gross Profit",
        "Operating Income", "Net Income", "EBITDA",
        "Basic EPS", "Diluted EPS",
    ]

    for item in key_items:
        if item in income_transposed.columns:
            values = []
            for val in income_transposed[item]:
                if pd.isna(val):
                    values.append("N/A")
                elif abs(val) >= 1e9:
                    values.append(f"{val/1e9:.2f}B")
                elif abs(val) >= 1e6:
                    values.append(f"{val/1e6:.2f}M")
                else:
                    values.append(f"{val:.2f}")
            lines.append(f"| {item} | " + " | ".join(values) + " |")

    return "\n".join(lines)


# ============================================================
# 内幕交易
# ============================================================

@register_vendor("get_insider_transactions", "yfinance", "fundamental_data")
def get_insider_transactions_yfinance(
    symbol: Annotated[str, "股票代码"],
    limit: Annotated[int, "返回条数"] = 10,
) -> str:
    """获取内幕交易数据

    Args:
        symbol: 股票代码
        limit: 返回最近几条

    Returns:
        格式化的内幕交易字符串
    """
    ticker = _get_ticker(symbol)

    try:
        insider = _yf_retry(lambda: ticker.insider_transactions)
    except Exception:
        return f"未找到 {symbol} 的内幕交易数据"

    if insider is None or insider.empty:
        return f"未找到 {symbol} 的内幕交易数据"

    lines = [f"# {symbol} 内幕交易 (最近 {limit} 条)\n"]
    lines.append("| 日期 | 内幕人 | 职位 | 交易类型 | 数量 | 价格 |")
    lines.append("|------|--------|------|----------|------|------|")

    for _, row in insider.head(limit).iterrows():
        date = row.get("Start Date", "N/A")
        insider_name = row.get("Insider", "N/A")
        title = row.get("Position", "N/A")
        txn_type = row.get("Text", "N/A")
        shares = row.get("Shares", "N/A")
        price = row.get("Value", "N/A")

        lines.append(f"| {date} | {insider_name} | {title} | {txn_type} | {shares} | {price} |")

    return "\n".join(lines)
