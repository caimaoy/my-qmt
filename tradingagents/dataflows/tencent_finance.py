"""腾讯财经数据源 + A股股票列表

腾讯财经 API:
- 实时行情: https://qt.gtimg.cn/q=sh600519
- 历史K线: https://web.ifzq.gtimg.cn/appstock/app/fqkline/get

东方财富 API:
- A股列表: https://82.push2.eastmoney.com/api/qt/clist/get
"""

import re
import json
import requests
from datetime import datetime, timedelta
from typing import Annotated

import pandas as pd

from .interface import register_vendor

# 通用请求头
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _safe_request(url: str, params: dict = None, headers: dict = None, timeout: int = 10, encoding: str = None) -> requests.Response:
    """安全的 HTTP 请求"""
    h = {**_HEADERS, **(headers or {})}
    response = requests.get(url, params=params, headers=h, timeout=timeout)
    response.raise_for_status()
    if encoding:
        response.encoding = encoding
    else:
        response.encoding = response.apparent_encoding
    return response


def _clean_code(symbol: str) -> str:
    """清理股票代码，去掉后缀"""
    return symbol.replace(".SS", "").replace(".SZ", "").replace(".SH", "")


def _get_market_prefix(code: str) -> str:
    """根据股票代码判断市场前缀 (sh/sz)"""
    if code.startswith("6") or code.startswith("9"):
        return "sh"
    return "sz"


# ============================================================
# 腾讯财经 - 实时行情
# ============================================================

@register_vendor("get_realtime_quote", "tencent", "core_stock_apis")
def get_realtime_quote(
    symbol: Annotated[str, "股票代码，如 '600519', '000001'"],
) -> dict:
    """从腾讯财经获取实时行情

    Args:
        symbol: A股股票代码 (6位数字)

    Returns:
        dict 包含: name, code, price, change, change_pct, open, high, low,
                   volume, amount, prev_close, turnover_rate, pe, pb
    """
    code = _clean_code(symbol)
    market = _get_market_prefix(code)
    url = f"https://qt.gtimg.cn/q={market}{code}"

    try:
        response = _safe_request(url, encoding="gbk")
        text = response.text

        # 解析腾讯财经返回的数据
        # 格式: v_sh600519="1~贵州茅台~600519~1291.91~1279.00~..."
        match = re.search(r'"([^"]+)"', text)
        if not match:
            return {"error": f"无法解析 {symbol} 的行情数据"}

        fields = match.group(1).split("~")
        if len(fields) < 40:
            return {"error": f"数据字段不足: {len(fields)}"}

        return {
            "name": fields[1],
            "code": fields[2],
            "price": float(fields[3]) if fields[3] else 0,
            "prev_close": float(fields[4]) if fields[4] else 0,
            "open": float(fields[5]) if fields[5] else 0,
            "volume": int(fields[6]) if fields[6] else 0,  # 手
            "buy_volume": int(fields[7]) if fields[7] else 0,
            "sell_volume": int(fields[8]) if fields[8] else 0,
            "change": float(fields[31]) if fields[31] else 0,
            "change_pct": float(fields[32]) if fields[32] else 0,
            "high": float(fields[33]) if fields[33] else 0,
            "low": float(fields[34]) if fields[34] else 0,
            "amount": float(fields[37]) if fields[37] else 0,  # 万元
            "turnover_rate": float(fields[38]) if fields[38] else 0,
            "pe": float(fields[39]) if fields[39] else 0,
            "pb": float(fields[46]) if len(fields) > 46 and fields[46] else 0,
            "market_cap": float(fields[45]) if len(fields) > 45 and fields[45] else 0,  # 亿
            "timestamp": fields[30] if len(fields) > 30 else "",
        }

    except Exception as e:
        return {"error": f"获取腾讯财经行情失败: {e}"}


# ============================================================
# 腾讯财经 - 历史K线数据
# ============================================================

@register_vendor("get_stock_data", "tencent", "core_stock_apis")
def get_history_kline(
    symbol: Annotated[str, "股票代码，如 '600519', '000001'"],
    start_date: Annotated[str, "开始日期，格式 yyyy-mm-dd"] = None,
    end_date: Annotated[str, "结束日期，格式 yyyy-mm-dd"] = None,
    days: Annotated[int, "获取最近N天数据"] = 120,
) -> str:
    """从腾讯财经获取历史K线数据

    Args:
        symbol: A股股票代码
        start_date: 开始日期 (可选)
        end_date: 结束日期 (可选)
        days: 获取最近N天数据 (默认120)

    Returns:
        CSV 格式的 OHLCV 数据
    """
    code = _clean_code(symbol)
    market = _get_market_prefix(code)

    # 计算需要获取的天数
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end_dt - start_dt).days + 10  # 多获取几天确保覆盖

    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "param": f"{market}{code},day,,,{days},qfq",
    }

    try:
        response = _safe_request(url, params=params)
        data = response.json()

        kline_key = f"{market}{code}"
        if "data" not in data or kline_key not in data["data"]:
            return f"未找到 {symbol} 的历史数据"

        kline_data = data["data"][kline_key]
        if "qfqday" not in kline_data:
            return f"未找到 {symbol} 的K线数据"

        # 转换为 DataFrame
        # 格式: [日期, 开盘, 收盘, 最高, 最低, 成交量]
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
            return f"未找到 {symbol} 的K线数据"

        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

        # 按日期范围过滤
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        if df.empty:
            return f"指定日期范围内没有数据: {start_date} - {end_date}"

        # 添加前缀注释
        header = f"# Stock data for {symbol} from Tencent Finance\n"
        header += f"# Total records: {len(df)}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + df.to_csv()

    except Exception as e:
        return f"获取腾讯财经历史数据失败: {e}"


# ============================================================
# 东方财富 - A股股票列表
# ============================================================

# 常用 A 股股票列表 (备用，当 API 不可用时使用)
_POPULAR_A_SHARES = [
    {"code": "600519", "name": "贵州茅台", "price": 0, "change_pct": 0},
    {"code": "000858", "name": "五粮液", "price": 0, "change_pct": 0},
    {"code": "000001", "name": "平安银行", "price": 0, "change_pct": 0},
    {"code": "600036", "name": "招商银行", "price": 0, "change_pct": 0},
    {"code": "601318", "name": "中国平安", "price": 0, "change_pct": 0},
    {"code": "000333", "name": "美的集团", "price": 0, "change_pct": 0},
    {"code": "600900", "name": "长江电力", "price": 0, "change_pct": 0},
    {"code": "601166", "name": "兴业银行", "price": 0, "change_pct": 0},
    {"code": "000002", "name": "万科A", "price": 0, "change_pct": 0},
    {"code": "600276", "name": "恒瑞医药", "price": 0, "change_pct": 0},
    {"code": "002415", "name": "海康威视", "price": 0, "change_pct": 0},
    {"code": "600031", "name": "三一重工", "price": 0, "change_pct": 0},
    {"code": "601012", "name": "隆基绿能", "price": 0, "change_pct": 0},
    {"code": "300750", "name": "宁德时代", "price": 0, "change_pct": 0},
    {"code": "002594", "name": "比亚迪", "price": 0, "change_pct": 0},
    {"code": "600050", "name": "中国联通", "price": 0, "change_pct": 0},
    {"code": "601398", "name": "工商银行", "price": 0, "change_pct": 0},
    {"code": "601288", "name": "农业银行", "price": 0, "change_pct": 0},
    {"code": "601988", "name": "中国银行", "price": 0, "change_pct": 0},
    {"code": "600028", "name": "中国石化", "price": 0, "change_pct": 0},
]


def get_all_a_shares(
    board: Annotated[str, "板块: all/hs300/cyb/kcb/zxb"] = "all",
) -> list[dict]:
    """获取所有A股股票列表

    Args:
        board: 板块筛选
            - all: 全部A股
            - hs300: 沪深300
            - cyb: 创业板
            - kcb: 科创板
            - zxb: 中小板

    Returns:
        list[dict] 包含 code, name, price, change_pct
    """
    # 板块筛选条件
    board_map = {
        "all": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
        "hs300": "b:BK0500",
        "cyb": "m:0+t:80",
        "kcb": "m:1+t:23",
        "zxb": "m:0+t:81+s:2048",
    }

    fs = board_map.get(board, board_map["all"])

    # 尝试多个东方财富 API 主机
    hosts = [
        "https://82.push2.eastmoney.com",
        "https://push2.eastmoney.com",
        "https://45.push2.eastmoney.com",
    ]

    for host in hosts:
        url = f"{host}/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "10000",  # 获取所有
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": fs,
            "fields": "f2,f3,f4,f5,f6,f7,f12,f14",
        }

        try:
            response = _safe_request(url, params=params, timeout=5)
            data = response.json()

            if "data" not in data or "diff" not in data["data"]:
                continue

            stocks = []
            for item in data["data"]["diff"]:
                code = item.get("f12", "")
                name = item.get("f14", "")
                price = item.get("f2", 0)
                change_pct = item.get("f3", 0)
                volume = item.get("f5", 0)
                amount = item.get("f6", 0)

                if code and name and price != "-":
                    stocks.append({
                        "code": code,
                        "name": name,
                        "price": float(price) if price and price != "-" else 0,
                        "change_pct": float(change_pct) if change_pct and change_pct != "-" else 0,
                        "volume": int(volume) if volume and volume != "-" else 0,
                        "amount": float(amount) if amount and amount != "-" else 0,
                    })

            if stocks:
                return stocks

        except Exception:
            continue

    # 如果所有 API 都失败，返回常用股票列表
    # 用腾讯财经获取实时行情
    return _get_popular_shares_with_realtime()


def _get_popular_shares_with_realtime() -> list[dict]:
    """获取常用股票的实时行情 (备用方案)"""
    result = []
    for stock in _POPULAR_A_SHARES:
        try:
            quote = get_realtime_quote(stock["code"])
            if "error" not in quote:
                result.append({
                    "code": stock["code"],
                    "name": quote.get("name", stock["name"]),
                    "price": quote.get("price", 0),
                    "change_pct": quote.get("change_pct", 0),
                    "volume": 0,
                    "amount": 0,
                })
            else:
                result.append(stock)
        except Exception:
            result.append(stock)
    return result


# ============================================================
# 批量技术分析筛选
# ============================================================

def scan_a_shares_by_indicator(
    board: str = "all",
    indicator: str = "rsi_below",
    threshold: float = 30,
    limit: int = 50,
) -> list[dict]:
    """扫描A股，根据技术指标筛选

    Args:
        board: 板块 (all/hs300/cyb/kcb)
        indicator: 筛选条件
            - rsi_below: RSI < threshold
            - rsi_above: RSI > threshold
            - macd_golden: MACD 金叉
            - macd_dead: MACD 死叉
            - price_below_bb_lower: 价格低于布林带下轨
            - price_above_bb_upper: 价格高于布林带上轨
        threshold: 阈值 (用于 RSI)
        limit: 返回结果数量限制

    Returns:
        list[dict] 符合条件的股票列表
    """
    from .tencent_finance import get_all_a_shares, get_history_kline
    from ..indicators.technical import compute_all_indicators

    # 获取股票列表
    stocks = get_all_a_shares(board)
    if not stocks:
        return []

    results = []
    total = len(stocks)

    for i, stock in enumerate(stocks):
        code = stock["code"]
        name = stock["name"]

        try:
            # 获取历史数据
            kline = get_history_kline(code, days=60)
            if kline.startswith("未找到") or kline.startswith("获取"):
                continue

            # 解析 CSV
            lines = [l for l in kline.split("\n") if not l.startswith("#") and l.strip()]
            if len(lines) < 20:
                continue

            csv_content = "\n".join(lines)
            df = pd.read_csv(pd.io.common.StringIO(csv_content), index_col=0, parse_dates=True)

            if len(df) < 20:
                continue

            # 计算指标
            df_indicators = compute_all_indicators(df)
            latest = df_indicators.iloc[-1]
            prev = df_indicators.iloc[-2] if len(df_indicators) > 1 else latest

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
                    "price": stock["price"],
                    "change_pct": stock["change_pct"],
                    "detail": detail,
                })

                if len(results) >= limit:
                    break

        except Exception:
            continue

    return results


# ============================================================
# 输出格式化
# ============================================================

def format_scan_results_markdown(results: list[dict], indicator: str, threshold: float) -> str:
    """格式化扫描结果为 Markdown 表格"""
    if not results:
        return "未找到符合条件的股票"

    lines = [f"# A股技术筛选结果\n"]
    lines.append(f"**筛选条件:** {indicator} (阈值: {threshold})\n")
    lines.append(f"**结果数量:** {len(results)}\n\n")

    lines.append("| 代码 | 名称 | 现价 | 涨跌幅 | 指标详情 |")
    lines.append("|------|------|------|--------|----------|")

    for r in results:
        lines.append(f"| {r['code']} | {r['name']} | {r['price']:.2f} | {r['change_pct']:.2f}% | {r['detail']} |")

    return "\n".join(lines)


def format_scan_results_html(results: list[dict], indicator: str, threshold: float) -> str:
    """格式化扫描结果为 HTML 表格"""
    if not results:
        return "<p>未找到符合条件的股票</p>"

    html = f"""
<h2>A股技术筛选结果</h2>
<p><strong>筛选条件:</strong> {indicator} (阈值: {threshold})</p>
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
