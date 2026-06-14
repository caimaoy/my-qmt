"""News data provider using yfinance."""

from datetime import datetime
from typing import Annotated

import yfinance as yf

from .interface import register_vendor


@register_vendor("get_news", "yfinance", "news_data")
def get_news_yfinance(
    symbol: Annotated[str, "ticker symbol"],
    limit: Annotated[int, "max number of articles"] = 20,
) -> str:
    """Fetch news articles for a ticker from Yahoo Finance.

    Args:
        symbol: Ticker symbol, e.g. "AAPL"
        limit: Maximum number of articles to return

    Returns:
        Formatted news string
    """
    ticker = yf.Ticker(symbol.upper())
    news_items = ticker.news

    if not news_items:
        return f"No news found for {symbol}"

    articles = []
    for item in news_items[:limit]:
        content = item.get("content", {})
        title = content.get("title", "No title")
        publisher = content.get("publisher", "Unknown")
        pub_date = content.get("pubDate", "")
        summary = content.get("summary", "")
        link = content.get("canonicalUrl", {}).get("url", "")

        articles.append(
            f"## {title}\n"
            f"**Publisher:** {publisher}\n"
            f"**Date:** {pub_date}\n"
            f"**Summary:** {summary}\n"
            f"**Link:** {link}\n"
        )

    header = f"# News for {symbol.upper()} ({len(articles)} articles)\n\n"
    return header + "\n---\n".join(articles)


@register_vendor("get_global_news", "yfinance", "news_data")
def get_global_news_yfinance(
    queries: list[str] | None = None,
    limit: Annotated[int, "max articles per query"] = 5,
) -> str:
    """Fetch global macro news.

    Args:
        queries: Search queries. Defaults to macro economic queries.
        limit: Articles per query

    Returns:
        Formatted news string
    """
    if queries is None:
        queries = [
            "stock market today",
            "interest rates",
            "inflation",
            "GDP growth",
            "geopolitical risks",
        ]

    all_articles = []
    for query in queries:
        try:
            results = yf.Search(query, max_results=limit)
            for item in results.news:
                content = item.get("content", {})
                title = content.get("title", "No title")
                summary = content.get("summary", "")
                all_articles.append(f"## {title}\n{summary}\n")
        except Exception:
            continue

    if not all_articles:
        return "No global news found"

    return f"# Global Market News ({len(all_articles)} articles)\n\n" + "\n---\n".join(
        all_articles
    )
