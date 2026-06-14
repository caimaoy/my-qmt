"""News Analyst Agent - Macro news and world affairs analysis."""


NEWS_ANALYST_PROMPT = """You are an experienced news analyst specializing in macro-economic and world affairs analysis.

Your task is to analyze recent news related to {symbol} and the broader market to identify key factors that could impact the stock.

## Company News
{company_news}

## Global Market News
{global_news}

## Analysis Instructions
1. Identify the top 3-5 most impactful news items
2. Analyze how macro-economic trends affect this stock
3. Assess geopolitical risks and opportunities
4. Evaluate industry-specific developments
5. Provide a news sentiment outlook (positive, negative, or neutral)

Write your analysis in a structured markdown format with clear sections.
"""


def get_news_analysis(symbol: str) -> str:
    """Run news analysis for a given symbol.

    Args:
        symbol: Ticker symbol

    Returns:
        News analysis report string
    """
    from ..dataflows.interface import route_to_vendor

    # Fetch company-specific news
    company_news = route_to_vendor("get_news", symbol, 20)

    # Fetch global news
    global_news = route_to_vendor("get_global_news")

    return NEWS_ANALYST_PROMPT.format(
        symbol=symbol,
        company_news=company_news,
        global_news=global_news,
    )
