"""Research Manager Agent - Judges bull/bear debate and produces investment plan."""


RESEARCH_MANAGER_PROMPT = """You are the Research Manager, responsible for judging the bull/bear debate and producing a structured investment plan.

## Analyst Reports
{analyst_reports}

## Bull/Bear Debate
{debate_summary}

## Instructions
1. Evaluate the quality of bull and bear arguments (data support, logic, foresight)
2. Weigh the arguments against analyst reports
3. Synthesize a structured investment recommendation
4. Assign a 5-tier rating: Strong Buy, Buy, Hold, Reduce, Sell

Write your evaluation in a structured markdown format with:
1. Debate judgment (scoring each side's arguments)
2. Comprehensive evaluation (weighting: Fundamentals 30%, Technical 20%, News/Sentiment 20%, Debate 30%)
3. Investment recommendation with reasoning
4. Strategic actions (position size, stop loss, target price)
"""


def get_research_manager_prompt(
    symbol: str,
    analyst_reports: dict[str, str],
    debate_summary: str,
) -> str:
    """Generate research manager prompt.

    Args:
        symbol: Ticker symbol
        analyst_reports: Dict of analyst name -> report
        debate_summary: Summary of the bull/bear debate

    Returns:
        Research manager prompt string
    """
    # Format analyst reports
    reports_str = ""
    for name, report in analyst_reports.items():
        reports_str += f"### {name}\n{report}\n\n"

    return RESEARCH_MANAGER_PROMPT.format(
        symbol=symbol,
        analyst_reports=reports_str,
        debate_summary=debate_summary,
    )
