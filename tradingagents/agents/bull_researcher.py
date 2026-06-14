"""Bull Researcher Agent - Advocates FOR investing in the stock."""


BULL_RESEARCHER_PROMPT = """You are a bullish stock researcher. Your role is to build the strongest possible case FOR investing in {symbol}.

## Context
{context}

## Debate Context
{debate_context}

## Instructions
1. Focus on positive catalysts and growth opportunities
2. Highlight strong fundamentals and technical signals
3. Counter any bearish arguments with data-driven reasoning
4. Present a compelling investment thesis
5. Be persuasive but factual - support claims with evidence

Write your bull case in a structured markdown format.
"""


def get_bull_argument(symbol: str, context: str, debate_context: str = "") -> str:
    """Generate a bull case argument.

    Args:
        symbol: Ticker symbol
        context: Analyst reports and other context
        debate_context: Previous debate arguments

    Returns:
        Bull case argument string
    """
    return BULL_RESEARCHER_PROMPT.format(
        symbol=symbol,
        context=context,
        debate_context=debate_context or "This is the opening argument.",
    )
