"""A股数据源: AKShare + 腾讯财经 (备用) + SQLite 缓存

数据源优先级:
1. AKShare (东方财富源) - 历史K线、指数成分股
2. 腾讯财经 (备用) - 实时行情、历史K线

缓存:
- 位置: ~/.my_qmt/cache/stock_data.db
- 格式: SQLite 数据库
- 有效期: K线 24小时, 指数成分股 7天
"""

import time
from datetime import datetime, timedelta
from typing import Annotated

import pandas as pd
import requests

from .interface import register_vendor
from .cache import (
    get_cached_kline,
    save_kline_to_cache,
    get_kline_missing_dates,
    get_cached_index_stocks,
    save_index_stocks_to_cache,
    cache_stats,
    cache_clear,
    cache_clear_expired,
)

# ============================================================
# 腾讯财经配置
# ============================================================

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


# ============================================================
# AKShare - 历史K线数据 (带 SQLite 缓存)
# ============================================================

def get_history_kline_akshare(
    symbol: str,
    start_date: str = None,
    end_date: str = None,
    days: int = 120,
    adjust: str = "qfq",
    use_cache: bool = True,
) -> pd.DataFrame:
    """从 AKShare 获取历史K线数据 (带增量缓存)

    Args:
        symbol: 股票代码，如 "600519", "000001"
        start_date: 开始日期，格式 "YYYYMMDD" 或 "YYYY-MM-DD"
        end_date: 结束日期
        days: 获取最近N天数据
        adjust: 复权方式 ("qfq" 前复权, "hfq" 后复权, "" 不复权)
        use_cache: 是否使用缓存

    Returns:
        DataFrame with columns: Open, Close, High, Low, Volume, Amount
    """
    # 处理日期格式
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    else:
        end_date = end_date.replace("/", "-")

    if start_date is None:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    else:
        start_date = start_date.replace("/", "-")

    # 检查缓存
    if use_cache:
        cached = get_cached_kline(symbol, start_date, end_date)
        if cached is not None and not cached.empty:
            return cached

    # 计算需要获取的日期范围 (增量更新)
    if use_cache:
        missing_ranges = get_kline_missing_dates(symbol, start_date, end_date)
    else:
        missing_ranges = [(start_date, end_date)]

    if not missing_ranges:
        return get_cached_kline(symbol, start_date, end_date) or pd.DataFrame()

    # 从 AKShare 获取数据
    try:
        import akshare as ak

        # 使用第一个缺失范围获取数据
        fetch_start = missing_ranges[0][0].replace("-", "")
        fetch_end = missing_ranges[-1][1].replace("-", "")

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=fetch_start,
            end_date=fetch_end,
            adjust=adjust,
        )

        if df.empty:
            return pd.DataFrame()

        # 标准化列名
        df = df.rename(columns={
            "日期": "Date",
            "开盘": "Open",
            "收盘": "Close",
            "最高": "High",
            "最低": "Low",
            "成交量": "Volume",
            "成交额": "Amount",
            "振幅": "Amplitude",
            "涨跌幅": "Change_Pct",
            "涨跌额": "Change",
            "换手率": "Turnover",
        })

        # 设置日期索引
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
        df = df.sort_index()

        # 保存到缓存
        if use_cache:
            save_kline_to_cache(symbol, df)
            # 重新从缓存获取完整数据
            return get_cached_kline(symbol, start_date, end_date) or df

        return df

    except Exception as e:
        # 如果 AKShare 失败，尝试返回缓存数据
        if use_cache:
            cached = get_cached_kline(symbol, start_date, end_date)
            if cached is not None:
                return cached
        return pd.DataFrame()


# ============================================================
# AKShare - 指数成分股 (带 SQLite 缓存)
# ============================================================

def get_index_stocks(index_code: str = "000300") -> list[dict]:
    """获取指数成分股列表 (带缓存)

    Args:
        index_code: 指数代码
            - "000300": 沪深300
            - "000016": 上证50
            - "399006": 创业板指
            - "000905": 中证500

    Returns:
        list[dict] 包含 code, name, weight
    """
    # 检查缓存
    cached = get_cached_index_stocks(index_code)
    if cached is not None:
        return cached

    # 从 AKShare 获取
    try:
        import akshare as ak

        df = ak.index_stock_cons_weight_csindex(symbol=index_code)

        if df.empty:
            return []

        stocks = []
        for _, row in df.iterrows():
            code = str(row.get("成分券代码", "")).zfill(6)
            name = row.get("成分券名称", "")
            weight = row.get("权重", 0)

            if code and name:
                stocks.append({
                    "code": code,
                    "name": name,
                    "weight": float(weight) if weight else 0,
                })

        # 保存到缓存
        if stocks:
            save_index_stocks_to_cache(index_code, stocks)

        return stocks

    except Exception as e:
        return []


def get_hs300_stocks() -> list[dict]:
    """获取沪深300成分股"""
    return get_index_stocks("000300")


def get_sz50_stocks() -> list[dict]:
    """获取上证50成分股"""
    return get_index_stocks("000016")


def get_zz500_stocks() -> list[dict]:
    """获取中证500成分股"""
    return get_index_stocks("000905")


# ============================================================
# 腾讯财经 - 实时行情 (不缓存)
# ============================================================

def get_realtime_quote(symbol: str) -> dict:
    """从腾讯财经获取实时行情 (不缓存)

    Args:
        symbol: 股票代码，如 "600519", "000001"

    Returns:
        dict 包含 name, code, price, change_pct, volume 等
    """
    code = symbol.replace(".SS", "").replace(".SZ", "").replace(".SH", "")
    market = "sh" if code.startswith("6") or code.startswith("9") else "sz"
    url = f"https://qt.gtimg.cn/q={market}{code}"

    try:
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.encoding = "gbk"
        text = response.text

        import re
        match = re.search(r'"([^"]+)"', text)
        if not match:
            return {"error": f"无法解析 {symbol} 的行情数据"}

        fields = match.group(1).split("~")
        if len(fields) < 40:
            return {"error": f"数据字段不足"}

        return {
            "name": fields[1],
            "code": fields[2],
            "price": float(fields[3]) if fields[3] else 0,
            "prev_close": float(fields[4]) if fields[4] else 0,
            "open": float(fields[5]) if fields[5] else 0,
            "volume": int(fields[6]) if fields[6] else 0,
            "change": float(fields[31]) if fields[31] else 0,
            "change_pct": float(fields[32]) if fields[32] else 0,
            "high": float(fields[33]) if fields[33] else 0,
            "low": float(fields[34]) if fields[34] else 0,
            "amount": float(fields[37]) if fields[37] else 0,
            "turnover_rate": float(fields[38]) if fields[38] else 0,
            "pe": float(fields[39]) if fields[39] else 0,
            "pb": float(fields[46]) if len(fields) > 46 and fields[46] else 0,
            "market_cap": float(fields[44]) if len(fields) > 44 and fields[44] else 0,  # 总市值 (亿)
            "float_cap": float(fields[45]) if len(fields) > 45 and fields[45] else 0,  # 流通市值 (亿)
            "real_turnover_rate": float(fields[49]) if len(fields) > 49 and fields[49] else 0,
            "total_shares": float(fields[72]) if len(fields) > 72 and fields[72] else 0,
        }

    except Exception as e:
        return {"error": f"获取行情失败: {e}"}


# ============================================================
# 腾讯财经 - 历史K线 (备用)
# ============================================================

def get_history_kline_tencent(
    symbol: str,
    start_date: str = None,
    end_date: str = None,
    days: int = 120,
) -> pd.DataFrame:
    """从腾讯财经获取历史K线数据 (备用)

    Args:
        symbol: 股票代码
        days: 获取最近N天数据

    Returns:
        DataFrame with OHLCV data
    """
    code = symbol.replace(".SS", "").replace(".SZ", "").replace(".SH", "")
    market = "sh" if code.startswith("6") or code.startswith("9") else "sz"

    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {"param": f"{market}{code},day,,,{days},qfq"}

    try:
        response = requests.get(url, headers=_HEADERS, params=params, timeout=10)
        data = response.json()

        kline_key = f"{market}{code}"
        if "data" not in data or kline_key not in data["data"]:
            return pd.DataFrame()

        kline_data = data["data"][kline_key]
        if "qfqday" not in kline_data:
            return pd.DataFrame()

        rows = []
        for item in kline_data["qfqday"]:
            if len(item) >= 6:
                rows.append({
                    "Date": item[0],
                    "Open": float(item[1]),
                    "Close": float(item[2]),
                    "High": float(item[3]),
                    "Low": float(item[4]),
                    "Volume": int(float(item[5])),
                })

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()

        # 按日期范围过滤
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        return df

    except Exception:
        return pd.DataFrame()


def get_real_turnover_rate(symbol: str) -> float:
    """从腾讯财经获取真实换手率 (基于流通股本)

    Args:
        symbol: 股票代码

    Returns:
        真实换手率 (%)，获取失败返回 0
    """
    code = symbol.replace(".SS", "").replace(".SZ", "").replace(".SH", "")
    market = "sh" if code.startswith("6") or code.startswith("9") else "sz"
    url = f"https://qt.gtimg.cn/q={market}{code}"

    try:
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.encoding = "gbk"
        text = response.text

        import re
        match = re.search(r'"([^"]+)"', text)
        if not match:
            return 0

        fields = match.group(1).split("~")
        if len(fields) < 50:
            return 0

        # 字段 [49] 是真实换手率 (基于流通股本)
        real_turnover = float(fields[49]) if fields[49] else 0
        return real_turnover

    except Exception:
        return 0


def get_stock_capital_info(symbol: str) -> dict:
    """从腾讯财经获取股票股本和市值信息

    Args:
        symbol: 股票代码

    Returns:
        dict 包含 float_shares, total_shares, market_cap, float_cap, real_turnover_rate, free_float_shares
    """
    code = symbol.replace(".SS", "").replace(".SZ", "").replace(".SH", "")
    market = "sh" if code.startswith("6") or code.startswith("9") else "sz"
    url = f"https://qt.gtimg.cn/q={market}{code}"

    try:
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.encoding = "gbk"
        text = response.text

        import re
        match = re.search(r'"([^"]+)"', text)
        if not match:
            return {}

        fields = match.group(1).split("~")
        if len(fields) < 50:
            return {}

        price = float(fields[3]) if fields[3] else 0
        volume = int(fields[6]) if fields[6] else 0  # 成交量 (手)
        total_market_cap = float(fields[44]) if fields[44] else 0  # 总市值 (亿)
        float_market_cap = float(fields[45]) if fields[45] else 0  # 流通市值 (亿)
        total_shares = float(fields[72]) if fields[72] else 0  # 总股本
        real_turnover_rate = float(fields[49]) if len(fields) > 49 and fields[49] else 0

        # 计算流通股本 = 流通市值 / 股价
        float_shares = (float_market_cap * 100000000) / price if price > 0 else 0

        # 计算自由流通股本
        # 真实换手率 = 成交量(股) / 自由流通股本 × 100%
        # 自由流通股本 = 成交量(股) / (真实换手率 / 100)
        free_float_shares = (volume * 100) / (real_turnover_rate / 100) if real_turnover_rate > 0 else 0

        return {
            "float_shares": float_shares,
            "total_shares": total_shares,
            "market_cap": total_market_cap,
            "float_cap": float_market_cap,
            "real_turnover_rate": real_turnover_rate,
            "free_float_shares": free_float_shares,
        }

    except Exception:
        return {}


# ============================================================
# 统一接口 (自动选择数据源)
# ============================================================

def get_stock_data(
    symbol: str,
    start_date: str = None,
    end_date: str = None,
    days: int = 120,
    use_cache: bool = True,
) -> pd.DataFrame:
    """获取股票历史数据 (自动选择数据源)

    优先使用 AKShare，失败时回退到腾讯财经

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        days: 获取最近N天数据
        use_cache: 是否使用缓存

    Returns:
        DataFrame with OHLCV data
    """
    # 尝试 AKShare
    df = get_history_kline_akshare(symbol, start_date, end_date, days, use_cache=use_cache)

    if not df.empty:
        # 获取股本和市值信息
        capital_info = get_stock_capital_info(symbol)
        if capital_info:
            df["Real_Turnover"] = capital_info.get("real_turnover_rate", 0)
            df["Float_Shares"] = capital_info.get("float_shares", 0)
            df["Total_Shares"] = capital_info.get("total_shares", 0)
            df["Market_Cap"] = capital_info.get("market_cap", 0)
            df["Float_Cap"] = capital_info.get("float_cap", 0)
            df["Free_Float_Shares"] = capital_info.get("free_float_shares", 0)
        return df

    # 回退到腾讯财经
    df = get_history_kline_tencent(symbol, start_date, end_date, days)

    if not df.empty:
        # 获取股本和市值信息
        capital_info = get_stock_capital_info(symbol)
        if capital_info:
            df["Real_Turnover"] = capital_info.get("real_turnover_rate", 0)
            df["Float_Shares"] = capital_info.get("float_shares", 0)
            df["Total_Shares"] = capital_info.get("total_shares", 0)
            df["Market_Cap"] = capital_info.get("market_cap", 0)
            df["Float_Cap"] = capital_info.get("float_cap", 0)
            df["Free_Float_Shares"] = capital_info.get("free_float_shares", 0)

    return df


# ============================================================
# 批量扫描
# ============================================================

def scan_stocks_by_indicator(
    stocks: list[dict],
    indicator: str = "rsi_below",
    threshold: float = 30,
    days: int = 60,
    limit: int = 50,
    use_cache: bool = True,
) -> list[dict]:
    """扫描股票，根据技术指标筛选

    Args:
        stocks: 股票列表 [{"code": "600519", "name": "贵州茅台"}, ...]
        indicator: 筛选条件
            - rsi_below: RSI < threshold
            - rsi_above: RSI > threshold
            - macd_golden: MACD 金叉
            - macd_dead: MACD 死叉
            - price_below_bb_lower: 价格低于布林带下轨
        threshold: 阈值 (用于 RSI)
        days: 历史数据天数
        limit: 返回结果数量限制
        use_cache: 是否使用缓存

    Returns:
        list[dict] 符合条件的股票列表
    """
    from ..indicators.technical import compute_all_indicators

    results = []
    total = len(stocks)

    for i, stock in enumerate(stocks):
        code = stock["code"]
        name = stock["name"]

        try:
            # 获取历史数据
            df = get_stock_data(code, days=days, use_cache=use_cache)

            if df.empty or len(df) < 20:
                continue

            # 计算指标
            df_indicators = compute_all_indicators(df)
            latest = df_indicators.iloc[-1]
            prev = df_indicators.iloc[-2] if len(df_indicators) > 1 else latest

            # 获取实时价格
            quote = get_realtime_quote(code)
            price = quote.get("price", 0) if "error" not in quote else latest.get("Close", 0)
            change_pct = quote.get("change_pct", 0) if "error" not in quote else 0

            # 根据条件筛选
            match = False
            detail = ""

            if indicator == "rsi_below":
                rsi_val = latest.get("RSI", 50)
                if not pd.isna(rsi_val) and rsi_val < threshold:
                    match = True
                    detail = f"RSI={rsi_val:.2f}"

            elif indicator == "rsi_above":
                rsi_val = latest.get("RSI", 50)
                if not pd.isna(rsi_val) and rsi_val > threshold:
                    match = True
                    detail = f"RSI={rsi_val:.2f}"

            elif indicator == "macd_golden":
                macd_curr = latest.get("MACD", 0)
                macd_prev = prev.get("MACD", 0)
                signal_curr = latest.get("MACD_Signal", 0)
                signal_prev = prev.get("MACD_Signal", 0)

                if (not pd.isna(macd_curr) and not pd.isna(signal_curr) and
                    not pd.isna(macd_prev) and not pd.isna(signal_prev)):
                    if macd_prev <= signal_prev and macd_curr > signal_curr:
                        match = True
                        detail = f"MACD={macd_curr:.4f}, Signal={signal_curr:.4f}"

            elif indicator == "macd_dead":
                macd_curr = latest.get("MACD", 0)
                macd_prev = prev.get("MACD", 0)
                signal_curr = latest.get("MACD_Signal", 0)
                signal_prev = prev.get("MACD_Signal", 0)

                if (not pd.isna(macd_curr) and not pd.isna(signal_curr) and
                    not pd.isna(macd_prev) and not pd.isna(signal_prev)):
                    if macd_prev >= signal_prev and macd_curr < signal_curr:
                        match = True
                        detail = f"MACD={macd_curr:.4f}, Signal={signal_curr:.4f}"

            elif indicator == "price_below_bb_lower":
                close = latest.get("Close", 0)
                bb_lower = latest.get("BB_Lower", 0)
                if not pd.isna(close) and not pd.isna(bb_lower) and close < bb_lower:
                    match = True
                    detail = f"Close={close:.2f}, BB_Lower={bb_lower:.2f}"

            if match:
                results.append({
                    "code": code,
                    "name": name,
                    "price": price,
                    "change_pct": change_pct,
                    "detail": detail,
                })

                if len(results) >= limit:
                    break

        except Exception:
            continue

    return results


def scan_multiple_conditions(
    stocks: list[dict],
    conditions: list[dict],
    days: int = 60,
    limit: int = 50,
    use_cache: bool = True,
) -> list[dict]:
    """扫描股票，同时满足多个条件

    Args:
        stocks: 股票列表
        conditions: 条件列表 [{"indicator": "rsi_below", "threshold": 30}, ...]
        days: 历史数据天数
        limit: 返回结果数量限制
        use_cache: 是否使用缓存

    Returns:
        list[dict] 符合所有条件的股票列表
    """
    from ..indicators.technical import compute_all_indicators

    results = []
    total = len(stocks)

    for i, stock in enumerate(stocks):
        code = stock["code"]
        name = stock["name"]

        try:
            # 获取历史数据
            df = get_stock_data(code, days=days, use_cache=use_cache)

            if df.empty or len(df) < 20:
                continue

            # 计算指标
            df_indicators = compute_all_indicators(df)
            latest = df_indicators.iloc[-1]
            prev = df_indicators.iloc[-2] if len(df_indicators) > 1 else latest

            # 检查所有条件
            all_match = True
            details = []

            for cond in conditions:
                indicator = cond["indicator"]
                threshold = cond.get("threshold", 0)

                if indicator == "rsi_below":
                    rsi_val = latest.get("RSI", 50)
                    if pd.isna(rsi_val) or rsi_val >= threshold:
                        all_match = False
                        break
                    details.append(f"RSI={rsi_val:.2f}")

                elif indicator == "rsi_above":
                    rsi_val = latest.get("RSI", 50)
                    if pd.isna(rsi_val) or rsi_val <= threshold:
                        all_match = False
                        break
                    details.append(f"RSI={rsi_val:.2f}")

                elif indicator == "macd_golden":
                    macd_curr = latest.get("MACD", 0)
                    macd_prev = prev.get("MACD", 0)
                    signal_curr = latest.get("MACD_Signal", 0)
                    signal_prev = prev.get("MACD_Signal", 0)

                    if (pd.isna(macd_curr) or pd.isna(signal_curr) or
                        pd.isna(macd_prev) or pd.isna(signal_prev)):
                        all_match = False
                        break

                    if not (macd_prev <= signal_prev and macd_curr > signal_curr):
                        all_match = False
                        break
                    details.append(f"MACD金叉")

            if all_match:
                # 获取实时价格
                quote = get_realtime_quote(code)
                price = quote.get("price", 0) if "error" not in quote else latest.get("Close", 0)
                change_pct = quote.get("change_pct", 0) if "error" not in quote else 0

                results.append({
                    "code": code,
                    "name": name,
                    "price": price,
                    "change_pct": change_pct,
                    "detail": " | ".join(details),
                })

                if len(results) >= limit:
                    break

        except Exception:
            continue

    return results


# ============================================================
# 输出格式化
# ============================================================

def format_scan_results_markdown(results: list[dict], title: str = "扫描结果") -> str:
    """格式化扫描结果为 Markdown 表格"""
    if not results:
        return "未找到符合条件的股票"

    lines = [f"# {title}\n"]
    lines.append(f"**结果数量:** {len(results)}\n\n")

    lines.append("| 代码 | 名称 | 现价 | 涨跌幅 | 指标详情 |")
    lines.append("|------|------|------|--------|----------|")

    for r in results:
        lines.append(f"| {r['code']} | {r['name']} | {r['price']:.2f} | {r['change_pct']:.2f}% | {r['detail']} |")

    return "\n".join(lines)


def format_scan_results_html(results: list[dict], title: str = "扫描结果") -> str:
    """格式化扫描结果为 HTML 表格"""
    if not results:
        return "<p>未找到符合条件的股票</p>"

    html = f"""
<h2>{title}</h2>
<p><strong>结果数量:</strong> {len(results)}</p>

<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
<thead>
<tr style="background-color: #f0f0f0;">
<th>代码</th><th>名称</th><th>现价</th><th>涨跌幅</th><th>指标详情</th>
</tr>
</thead>
<tbody>
"""

    for r in results:
        change_color = "red" if r["change_pct"] > 0 else "green" if r["change_pct"] < 0 else "black"
        html += f"""<tr>
<td>{r['code']}</td>
<td>{r['name']}</td>
<td>{r['price']:.2f}</td>
<td style="color: {change_color};">{r['change_pct']:.2f}%</td>
<td>{r['detail']}</td>
</tr>
"""

    html += "</tbody></table>"
    return html


# ============================================================
# 缓存管理 (导出)
# ============================================================

def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    return cache_stats()


def clear_cache(pattern: str = None):
    """清除缓存

    Args:
        pattern: 清除模式
            - None: 清除所有缓存
            - "kline": 只清除K线数据
            - "index": 只清除指数成分股
    """
    cache_clear(pattern)


def clear_expired_cache():
    """清除过期缓存"""
    cache_clear_expired()
