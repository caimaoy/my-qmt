"""社交媒体数据源: StockTwits, Reddit"""

import json
import requests
from datetime import datetime
from typing import Annotated

from .interface import register_vendor

# 通用请求头
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _safe_request(url: str, params: dict = None, headers: dict = None, timeout: int = 10) -> requests.Response:
    """安全的 HTTP 请求"""
    h = {**_HEADERS, **(headers or {})}
    response = requests.get(url, params=params, headers=h, timeout=timeout)
    response.raise_for_status()
    return response


# ============================================================
# StockTwits - 散户情绪
# ============================================================

@register_vendor("get_sentiment", "stocktwits", "sentiment_data")
def fetch_stocktwits_messages(
    symbol: Annotated[str, "股票代码，如 'AAPL', 'NVDA'"],
    limit: Annotated[int, "最大消息数"] = 30,
) -> str:
    """从 StockTwits 获取散户讨论和情绪

    Args:
        symbol: 股票代码
        limit: 最大返回消息数

    Returns:
        格式化的消息字符串
    """
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol.upper()}.json"

    try:
        response = _safe_request(url)
        data = response.json()
        messages = data.get("messages", [])

        if not messages:
            return f"未找到 {symbol} 的 StockTwits 消息"

        # 统计情绪
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        items = []
        for msg in messages[:limit]:
            sentiment = msg.get("entities", {}).get("sentiment", {})
            sentiment_class = sentiment.get("basic", "Neutral") if sentiment else "Neutral"

            if sentiment_class == "Bullish":
                bullish_count += 1
            elif sentiment_class == "Bearish":
                bearish_count += 1
            else:
                neutral_count += 1

            user = msg.get("user", {}).get("username", "匿名")
            body = msg.get("body", "")[:200]
            created = msg.get("created_at", "")
            likes = msg.get("likes", {}).get("total", 0)

            items.append(
                f"### @{user} ({sentiment_class})\n"
                f"**时间:** {created}\n"
                f"**内容:** {body}\n"
                f"**点赞:** {likes}\n"
            )

        total = bullish_count + bearish_count + neutral_count
        bull_pct = (bullish_count / total * 100) if total > 0 else 0
        bear_pct = (bearish_count / total * 100) if total > 0 else 0

        header = f"# {symbol} StockTwits 散户情绪\n\n"
        summary = (
            f"**总消息数:** {total}\n"
            f"**看多:** {bullish_count} ({bull_pct:.1f}%) | "
            f"**看空:** {bearish_count} ({bear_pct:.1f}%) | "
            f"**中性:** {neutral_count}\n\n"
        )

        return header + summary + "\n---\n".join(items)

    except Exception as e:
        return f"获取 StockTwits 数据失败: {e}"


# ============================================================
# Reddit - 投资社区讨论
# ============================================================

@register_vendor("get_sentiment", "reddit", "sentiment_data")
def fetch_reddit_posts(
    symbol: Annotated[str, "股票代码，如 'AAPL', 'NVDA'"],
    subreddits: list[str] | None = None,
    limit: Annotated[int, "每个 subreddit 的最大帖子数"] = 10,
) -> str:
    """从 Reddit 获取投资社区讨论

    Args:
        symbol: 股票代码
        subreddits: subreddit 列表，默认 ["wallstreetbets", "stocks", "investing"]
        limit: 每个 subreddit 的最大帖子数

    Returns:
        格式化的帖子字符串
    """
    if subreddits is None:
        subreddits = ["wallstreetbets", "stocks", "investing"]

    all_posts = []
    ticker = symbol.upper().replace(".", "")

    for subreddit in subreddits:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            "q": f"${ticker} OR {ticker}",
            "sort": "new",
            "limit": limit,
            "t": "week",  # 最近一周
        }
        headers = {
            "User-Agent": "TradingAgents/1.0",
        }

        try:
            response = _safe_request(url, params=params, headers=headers)
            data = response.json()
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")[:300]
                score = post_data.get("score", 0)
                num_comments = post_data.get("num_comments", 0)
                created = datetime.fromtimestamp(post_data.get("created_utc", 0)).strftime("%Y-%m-%d %H:%M")
                permalink = post_data.get("permalink", "")

                all_posts.append(
                    f"## {title}\n"
                    f"**来源:** r/{subreddit} | **时间:** {created}\n"
                    f"**评分:** {score} | **评论:** {num_comments}\n"
                    f"**内容:** {selftext}\n"
                    f"**链接:** https://reddit.com{permalink}\n"
                )

        except Exception:
            continue

    if not all_posts:
        return f"未找到 {symbol} 的 Reddit 讨论"

    header = f"# {symbol} Reddit 讨论 ({len(all_posts)} 条)\n\n"
    return header + "\n---\n".join(all_posts)


# ============================================================
# 聚合: 获取所有舆情数据
# ============================================================

def get_sentiment_aggregated(
    symbol: str,
    market: str = "us",
    limit: int = 15,
) -> str:
    """聚合所有舆情数据源

    Args:
        symbol: 股票代码
        market: 市场 ("us" 或 "cn")
        limit: 每个源的最大条数

    Returns:
        聚合后的舆情字符串
    """
    results = []

    if market == "us":
        # 美股: StockTwits + Reddit
        try:
            stw = fetch_stocktwits_messages(symbol, limit)
            if not stw.startswith("获取") and not stw.startswith("未找到"):
                results.append(stw)
        except Exception:
            pass

        try:
            reddit = fetch_reddit_posts(symbol, limit=limit)
            if not reddit.startswith("获取") and not reddit.startswith("未找到"):
                results.append(reddit)
        except Exception:
            pass
    else:
        # A股: 东方财富股吧 + 雪球
        from .china_news import get_guba_hot_posts, get_news_xueqiu

        try:
            guba = get_guba_hot_posts(symbol, limit)
            if not guba.startswith("获取") and not guba.startswith("未找到"):
                results.append(guba)
        except Exception:
            pass

        try:
            xq = get_news_xueqiu(symbol, limit)
            if not xq.startswith("获取") and not xq.startswith("未找到"):
                results.append(xq)
        except Exception:
            pass

    if not results:
        return f"未找到 {symbol} 的舆情数据"

    return "\n\n===\n\n".join(results)
