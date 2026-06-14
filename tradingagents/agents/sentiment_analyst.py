"""Sentiment Analyst Agent - Social media and retail investor sentiment analysis."""


SENTIMENT_ANALYST_PROMPT = """You are a sentiment analyst specializing in social media and retail investor sentiment.

Your task is to analyze the sentiment around {symbol} from social media and investor discussions.

## Social Media Data
{social_data}

## Analysis Instructions
1. Analyze the bullish/bearish/neutral sentiment ratio
2. Identify hot topics and key discussions
3. Detect any unusual sentiment signals (extreme optimism/pessimism)
4. Assess the reliability of sentiment data
5. Provide a sentiment outlook (bullish, bearish, or neutral)

Write your analysis in a structured markdown format with clear sections.
"""


def get_sentiment_analysis(symbol: str) -> str:
    """Run sentiment analysis for a given symbol.

    Args:
        symbol: Ticker symbol

    Returns:
        Sentiment analysis prompt string
    """
    from ..dataflows.social_media import fetch_stocktwits_messages, fetch_reddit_posts
    from ..dataflows.china_news import get_guba_hot_posts, get_news_xueqiu

    # Determine market and fetch appropriate data
    code = symbol.replace(".SS", "").replace(".SZ", "").replace(".HK", "")

    social_data = ""

    if code.startswith("6") or code.startswith("0") or code.startswith("3"):
        # A股: 东方财富股吧 + 雪球
        try:
            guba = get_guba_hot_posts(symbol, limit=20)
            if not guba.startswith("获取") and not guba.startswith("未找到"):
                social_data += guba + "\n\n"
        except Exception:
            pass

        try:
            xq = get_news_xueqiu(symbol, limit=10)
            if not xq.startswith("获取") and not xq.startswith("未找到"):
                social_data += xq
        except Exception:
            pass
    else:
        # 美股/港股: StockTwits + Reddit
        try:
            stw = fetch_stocktwits_messages(symbol, limit=20)
            if not stw.startswith("获取") and not stw.startswith("未找到"):
                social_data += stw + "\n\n"
        except Exception:
            pass

        try:
            reddit = fetch_reddit_posts(symbol, limit=10)
            if not reddit.startswith("获取") and not reddit.startswith("未找到"):
                social_data += reddit
        except Exception:
            pass

    if not social_data:
        social_data = f"未找到 {symbol} 的舆情数据"

    return SENTIMENT_ANALYST_PROMPT.format(
        symbol=symbol,
        social_data=social_data,
    )
