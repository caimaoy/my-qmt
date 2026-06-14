"""国内财经新闻数据源: 东方财富、新浪财经、雪球"""

import re
import json
import requests
from datetime import datetime
from typing import Annotated

from .interface import register_vendor

# 通用请求头
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}


def _safe_request(url: str, params: dict = None, headers: dict = None, timeout: int = 10, encoding: str = None) -> requests.Response:
    """安全的 HTTP 请求，带超时和错误处理"""
    h = {**_HEADERS, **(headers or {})}
    response = requests.get(url, params=params, headers=h, timeout=timeout)
    response.raise_for_status()
    if encoding:
        response.encoding = encoding
    else:
        # 自动检测编码
        response.encoding = response.apparent_encoding
    return response


def _clean_code(symbol: str) -> str:
    """清理股票代码，去掉后缀"""
    return symbol.replace(".SS", "").replace(".SZ", "").replace(".SH", "").replace(".HK", "")


# ============================================================
# 东方财富 - 个股公告 (已验证可用)
# ============================================================

@register_vendor("get_news", "eastmoney", "news_data")
def get_news_eastmoney(
    symbol: Annotated[str, "股票代码，如 '600519', '000001'"],
    limit: Annotated[int, "最大文章数"] = 20,
) -> str:
    """从东方财富获取个股公告和新闻

    Args:
        symbol: A股股票代码 (6位数字)
        limit: 最大返回文章数

    Returns:
        格式化的新闻字符串
    """
    code = _clean_code(symbol)

    # 东方财富公告 API (已验证可用)
    url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    params = {
        "sr": "-1",
        "page_size": str(limit),
        "page_index": "1",
        "ann_type": "A",
        "client_source": "web",
        "stock_list": code,
    }

    try:
        response = _safe_request(url, params=params, headers={"Referer": "https://data.eastmoney.com/"})
        data = response.json()

        if not data.get("success"):
            return f"东方财富 API 返回错误"

        items = data.get("data", {}).get("list", [])
        if not items:
            return f"未找到 {symbol} 的公告"

        news_items = []
        for item in items[:limit]:
            title = item.get("title", "无标题")
            date = item.get("notice_date", "")[:10]
            code_name = item.get("codes", [{}])[0].get("short_name", code)

            news_items.append(
                f"## {title}\n"
                f"**来源:** 东方财富 | **公司:** {code_name} | **日期:** {date}\n"
            )

        header = f"# {symbol} 公告 ({len(news_items)} 条) - 东方财富\n\n"
        return header + "\n---\n".join(news_items)

    except Exception as e:
        return f"获取东方财富公告失败: {e}"


# ============================================================
# 东方财富 - 股吧热帖 (已修复)
# ============================================================

def get_guba_hot_posts(
    symbol: Annotated[str, "股票代码，如 '600519', '000001'"],
    limit: Annotated[int, "最大文章数"] = 10,
) -> str:
    """从东方财富股吧获取热帖

    Args:
        symbol: A股股票代码
        limit: 最大返回文章数

    Returns:
        格式化的帖子字符串
    """
    code = _clean_code(symbol)

    # 股吧 API
    url = f"https://guba.eastmoney.com/list,{code}.html"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        html = response.text

        # 解析股吧帖子 - 使用验证过的模式
        news_items = []
        seen = set()

        # 模式1: 匹配 /news, 链接和文本内容
        pattern = r'<a[^>]*href="(/news,[^"]+)"[^>]*>([^<]{8,})</a>'
        matches = re.findall(pattern, html)

        for link, title in matches:
            title = title.strip()
            if title not in seen and len(title) > 8 and not title.startswith(" "):
                seen.add(title)
                full_link = f"https://guba.eastmoney.com{link}"
                news_items.append(
                    f"## {title}\n"
                    f"**来源:** 东方财富股吧 | **链接:** {full_link}\n"
                )
                if len(news_items) >= limit:
                    break

        if not news_items:
            return f"未找到 {symbol} 的股吧热帖"

        header = f"# {symbol} 股吧热帖 ({len(news_items)} 条) - 东方财富\n\n"
        return header + "\n---\n".join(news_items)

    except Exception as e:
        return f"获取股吧热帖失败: {e}"


# ============================================================
# 东方财富 - 全球财经快讯
# ============================================================

@register_vendor("get_global_news", "eastmoney", "news_data")
def get_global_news_eastmoney(
    limit: Annotated[int, "最大文章数"] = 20,
) -> str:
    """从东方财富获取全球财经快讯

    Args:
        limit: 最大返回文章数

    Returns:
        格式化的新闻字符串
    """
    url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
    params = {
        "columns": "102",
        "limit": limit,
        "client": "web",
    }

    try:
        response = _safe_request(url, params=params)
        data = response.json()
        articles = data.get("data", {}).get("list", [])

        if not articles:
            return "未找到全球财经新闻"

        news_items = []
        for item in articles[:limit]:
            title = item.get("title", "")
            date = item.get("showTime", "")
            source = item.get("mediaName", "东方财富")
            content = item.get("digest", "")

            news_items.append(
                f"## {title}\n"
                f"**来源:** {source} | **日期:** {date}\n"
                f"**摘要:** {content}\n"
            )

        header = f"# 全球财经快讯 ({len(news_items)} 条) - 东方财富\n\n"
        return header + "\n---\n".join(news_items)

    except Exception as e:
        return f"获取东方财富快讯失败: {e}"


# ============================================================
# 新浪财经 - 个股新闻 (已修复编码)
# ============================================================

@register_vendor("get_news", "sina", "news_data")
def get_news_sina(
    symbol: Annotated[str, "股票代码，如 '600519', '000001'"],
    limit: Annotated[int, "最大文章数"] = 20,
) -> str:
    """从新浪财经获取个股新闻

    Args:
        symbol: A股股票代码
        limit: 最大返回文章数

    Returns:
        格式化的新闻字符串
    """
    code = _clean_code(symbol)
    market = "sh" if code.startswith("6") else "sz"

    # 新浪财经个股新闻页面
    url = f"https://finance.sina.com.cn/realstock/company/{market}{code}/nc.shtml"

    try:
        # 关键修复: 设置正确的编码为 GB18030
        response = _safe_request(url, encoding="gb18030")
        html = response.text

        # 解析新闻列表
        news_items = []
        seen = set()

        # 匹配新闻标题和链接 (target="_blank" 的链接通常是新闻)
        pattern = r'<a[^>]+href="(https?://finance\.sina\.com\.cn/[^"]+)"[^>]*target="_blank"[^>]*>([^<]{10,})</a>'
        matches = re.findall(pattern, html)

        for link, title in matches:
            title = title.strip()
            # 过滤掉导航和广告链接
            if title not in seen and len(title) > 8 and not any(x in title for x in ["配置", "level2", "直播", "名师"]):
                seen.add(title)
                news_items.append(
                    f"## {title}\n"
                    f"**来源:** 新浪财经 | **链接:** {link}\n"
                )
                if len(news_items) >= limit:
                    break

        if not news_items:
            return f"未找到 {symbol} 的新浪新闻"

        header = f"# {symbol} 个股新闻 ({len(news_items)} 条) - 新浪财经\n\n"
        return header + "\n---\n".join(news_items)

    except Exception as e:
        return f"获取新浪财经新闻失败: {e}"


# ============================================================
# 雪球 - 个股讨论 (需要有效 Token)
# ============================================================

@register_vendor("get_news", "xueqiu", "news_data")
def get_news_xueqiu(
    symbol: Annotated[str, "股票代码，如 'SH600519', 'SZ000001'"],
    limit: Annotated[int, "最大文章数"] = 20,
) -> str:
    """从雪球获取个股讨论和新闻

    注意: 雪球 API 需要有效的登录 Token 才能获取数据。
    如果没有 Token，会返回空结果。

    Args:
        symbol: 股票代码 (带交易所前缀: SH/SZ)
        limit: 最大返回文章数

    Returns:
        格式化的新闻字符串
    """
    code = _clean_code(symbol)
    if code.startswith("6"):
        xq_symbol = f"SH{code}"
    else:
        xq_symbol = f"SZ{code}"

    # 尝试使用雪球的公开 API
    url = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json"
    params = {
        "size": limit,
        "order": "desc",
        "order_by": "follow",
        "exchange": "CN",
        "market": "CN",
        "type": "stock",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://xueqiu.com/",
        "Cookie": "xq_a_token=;",  # 需要有效 token
    }

    try:
        response = _safe_request(url, params=params, headers=headers)
        data = response.json()

        # 雪球 API 可能需要认证，如果返回空则使用备用方案
        if not data.get("data"):
            # 备用: 尝试获取雪球热帖
            return _get_xueqiu_web(xq_symbol, limit)

        items = data.get("data", {}).get("items", [])
        if not items:
            return f"未找到 {xq_symbol} 的雪球讨论"

        news_items = []
        for item in items[:limit]:
            name = item.get("name", "")
            symbol_code = item.get("symbol", "")
            current = item.get("current", 0)
            percent = item.get("percent", 0)
            followers = item.get("follow_count", 0)

            news_items.append(
                f"## {name} ({symbol_code})\n"
                f"**现价:** {current} | **涨跌:** {percent}% | **关注:** {followers}\n"
            )

        header = f"# 雪球热股 ({len(news_items)} 条)\n\n"
        return header + "\n---\n".join(news_items)

    except Exception as e:
        # 如果 API 失败，尝试网页抓取
        return _get_xueqiu_web(xq_symbol, limit)


def _get_xueqiu_web(symbol: str, limit: int = 10) -> str:
    """从雪球网页获取讨论 (备用方案)"""
    try:
        url = f"https://xueqiu.com/S/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"
        html = response.text

        # 简单解析
        pattern = r'"text":"([^"]{20,})"'
        matches = re.findall(pattern, html)

        if not matches:
            return f"未找到 {symbol} 的雪球讨论 (可能需要登录)"

        news_items = []
        for text in matches[:limit]:
            # 清理 JSON 转义字符
            clean_text = text.replace("\\n", "\n").replace("\\t", " ")[:200]
            news_items.append(f"## 雪球讨论\n{clean_text}\n")

        header = f"# {symbol} 雪球讨论 ({len(news_items)} 条)\n\n"
        return header + "\n---\n".join(news_items)

    except Exception as e:
        return f"获取雪球讨论失败: {e}"


# ============================================================
# 聚合: 获取国内所有新闻源
# ============================================================

def get_china_news_aggregated(
    symbol: str,
    limit_per_source: int = 10,
) -> str:
    """聚合同类新闻源的结果

    Args:
        symbol: 股票代码
        limit_per_source: 每个源的最大文章数

    Returns:
        聚合后的新闻字符串
    """
    results = []

    # 东方财富公告
    try:
        eastmoney_news = get_news_eastmoney(symbol, limit_per_source)
        if not eastmoney_news.startswith("获取") and not eastmoney_news.startswith("未找到"):
            results.append(eastmoney_news)
    except Exception:
        pass

    # 东方财富股吧
    try:
        guba_news = get_guba_hot_posts(symbol, limit_per_source)
        if not guba_news.startswith("获取") and not guba_news.startswith("未找到"):
            results.append(guba_news)
    except Exception:
        pass

    # 新浪财经
    try:
        sina_news = get_news_sina(symbol, limit_per_source)
        if not sina_news.startswith("获取") and not sina_news.startswith("未找到"):
            results.append(sina_news)
    except Exception:
        pass

    if not results:
        return f"未找到 {symbol} 的国内新闻"

    return "\n\n===\n\n".join(results)
