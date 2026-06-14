"""Bear Researcher Agent - Advocates AGAINST investing in the stock."""


BEAR_RESEARCHER_PROMPT = """You are a bearish stock researcher. Your role is to build the strongest possible case AGAINST investing in {symbol}.

## Context
{context}

## Debate Context
{debate_context}

## Instructions
1. Focus on risks, challenges, and potential downside
2. Highlight overvaluation, competitive threats, and weaknesses
3. Counter any bullish arguments with data-driven reasoning
4. Present a compelling case for caution or selling
5. Be persuasive but factual - support claims with evidence

Write your bear case in a structured markdown format.
"""


def get_bear_argument(symbol: str, context: str, debate_context: str = "") -> str:
    """Generate a bear case argument.

    Args:
        symbol: Ticker symbol
        context: Analyst reports and other context
        debate_context: Previous debate arguments

    Returns:
        Bear case argument string
    """
    return BEAR_RESEARCHER_PROMPT.format(
        symbol=symbol,
        context=context,
        debate_context=debate_context or "This is the opening argument.",
    )
