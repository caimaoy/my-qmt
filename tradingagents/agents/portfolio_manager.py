"""Portfolio Manager Agent - Final decision maker."""

from dataclasses import dataclass
from enum import Enum


class PortfolioRating(Enum):
    """5-tier portfolio rating."""
    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"


@dataclass
class PortfolioDecision:
    """Structured portfolio decision."""
    rating: PortfolioRating
    executive_summary: str
    investment_thesis: str
    price_target: str | None = None
    time_horizon: str | None = None


PORTFOLIO_MANAGER_PROMPT = """You are the Portfolio Manager, responsible for making the final investment decision.

## Analyst Reports
{analyst_reports}

## Research Debate Summary
{debate_summary}

## Past Decisions and Reflections
{past_context}

## Instructions
1. Review all analyst reports and the research debate
2. Consider past decisions and their outcomes
3. Make a final investment decision using one of these ratings:
   - **Buy**: Strong conviction, expect significant upside
   - **Overweight**: Moderate conviction, expect above-average returns
   - **Hold**: Neutral, maintain current position
   - **Underweight**: Moderate concern, expect below-average returns
   - **Sell**: Strong concern, expect significant downside

4. Provide your decision in this exact format:

## Decision
**Rating:** [Buy/Overweight/Hold/Underweight/Sell]

## Executive Summary
[2-3 sentence summary of your decision]

## Investment Thesis
[Detailed reasoning for your decision, 3-5 paragraphs]

## Price Target (optional)
[Your price target with reasoning]

## Time Horizon (optional)
[Recommended holding period]
"""


def get_portfolio_decision(
    symbol: str,
    analyst_reports: dict[str, str],
    debate_summary: str,
    past_context: str = "",
) -> PortfolioDecision:
    """Generate a portfolio decision.

    Args:
        symbol: Ticker symbol
        analyst_reports: Dict of analyst name -> report
        debate_summary: Summary of the research debate
        past_context: Past decisions and reflections

    Returns:
        PortfolioDecision with rating and analysis
    """
    # Format analyst reports
    reports_str = ""
    for name, report in analyst_reports.items():
        reports_str += f"### {name}\n{report}\n\n"

    prompt = PORTFOLIO_MANAGER_PROMPT.format(
        analyst_reports=reports_str,
        debate_summary=debate_summary,
        past_context=past_context or "No past decisions available.",
    )

    return prompt


def parse_rating(text: str) -> PortfolioRating:
    """Extract rating from portfolio manager's markdown response.

    Uses deterministic heuristic - no LLM call needed.
    """
    text_upper = text.upper()

    # Look for rating in the decision section
    for line in text.split("\n"):
        line_upper = line.upper().strip()
        if "**RATING:**" in line_upper or "RATING:" in line_upper:
            for rating in PortfolioRating:
                if rating.value.upper() in line_upper:
                    return rating

    # Fallback: search entire text
    for rating in PortfolioRating:
        if rating.value.upper() in text_upper:
            return rating

    return PortfolioRating.HOLD  # Default if no rating found
