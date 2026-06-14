"""Fundamentals Analyst Agent - Financial statements and company fundamentals analysis."""


FUNDAMENTALS_ANALYST_PROMPT = """You are a fundamentals analyst specializing in financial statement analysis and company valuation.

Your task is to analyze the fundamentals of {symbol} and provide a comprehensive analysis report.

## Company Overview
{fundamentals}

## Balance Sheet
{balance_sheet}

## Income Statement
{income_statement}

## Cash Flow
{cashflow}

## Insider Transactions
{insider_transactions}

## Analysis Instructions
1. Assess profitability (revenue growth, margins, ROE)
2. Evaluate financial health (debt, liquidity, cash flow)
3. Analyze valuation (PE, PB, PS vs history and peers)
4. Identify growth potential and risks
5. Provide a fundamental rating (Excellent/Good/Average/Poor)

Write your analysis in a structured markdown format with clear sections.
"""


def get_fundamentals_analysis(symbol: str) -> str:
    """Run fundamentals analysis for a given symbol.

    Args:
        symbol: Ticker symbol

    Returns:
        Fundamentals analysis prompt string
    """
    from ..dataflows.interface import route_to_vendor

    # Fetch all financial data
    fundamentals = route_to_vendor("get_fundamentals", symbol)
    balance_sheet = route_to_vendor("get_balance_sheet", symbol, 4)
    income_statement = route_to_vendor("get_income_statement", symbol, 4)
    cashflow = route_to_vendor("get_cashflow", symbol, 4)

    # Insider transactions (optional, may fail)
    try:
        insider_transactions = route_to_vendor("get_insider_transactions", symbol, 10)
    except Exception:
        insider_transactions = "无内幕交易数据"

    return FUNDAMENTALS_ANALYST_PROMPT.format(
        symbol=symbol,
        fundamentals=fundamentals,
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        cashflow=cashflow,
        insider_transactions=insider_transactions,
    )
