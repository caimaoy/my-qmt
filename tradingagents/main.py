"""TradingAgents - Multi-Agent LLM Trading Framework.

完整 8 Agent 流程:
Phase 1: Analysts (并行)
  - Market Analyst (技术分析)
  - Sentiment Analyst (舆情分析)
  - News Analyst (新闻分析)
  - Fundamentals Analyst (基本面分析)

Phase 2: Research Debate
  - Bull Researcher (看多)
  - Bear Researcher (看空)
  - Research Manager (裁判)

Phase 3: Decision
  - Portfolio Manager (最终决策)
"""

from .agents.market_analyst import get_market_analysis
from .agents.news_analyst import get_news_analysis
from .agents.portfolio_manager import PortfolioDecision, PortfolioRating, parse_rating
from .dataflows.interface import route_to_vendor, set_vendor_config
from .debate.framework import DebateRunner, InvestmentDebateState, RiskDebateState
from .indicators.technical import compute_all_indicators
from .memory.trading_log import TradingMemoryLog


def run_analysis(
    symbol: str,
    trade_date: str,
    max_debate_rounds: int = 1,
    resolve_reflections: bool = True,
) -> dict:
    """Run full trading analysis pipeline.

    Args:
        symbol: Ticker symbol
        trade_date: Analysis date (yyyy-mm-dd)
        max_debate_rounds: Number of debate rounds
        resolve_reflections: Whether to resolve past pending reflections

    Returns:
        Dict with all analysis results and prompts for LLM
    """
    # Phase 0: Resolve pending reflections
    memory = TradingMemoryLog()
    if resolve_reflections:
        memory.resolve_pending()

    # Phase 1: Analyst Reports (返回 prompt，由 opencode subagent 调用 LLM)
    market_report = get_market_analysis(symbol, trade_date)
    news_report = get_news_analysis(symbol)

    # Sentiment Analyst (通过 opencode subagent 调用)
    from .agents.sentiment_analyst import get_sentiment_analysis
    sentiment_report = get_sentiment_analysis(symbol)

    # Fundamentals Analyst (通过 opencode subagent 调用)
    from .agents.fundamentals_analyst import get_fundamentals_analysis
    fundamentals_report = get_fundamentals_analysis(symbol)

    analyst_reports = {
        "Market Analyst": market_report,
        "News Analyst": news_report,
        "Sentiment Analyst": sentiment_report,
        "Fundamentals Analyst": fundamentals_report,
    }

    # Phase 2: Research Debate (Bull vs Bear)
    from .agents.bull_researcher import get_bull_argument
    from .agents.bear_researcher import get_bear_argument

    context = (
        f"## 技术分析\n{market_report}\n\n"
        f"## 新闻分析\n{news_report}\n\n"
        f"## 舆情分析\n{sentiment_report}\n\n"
        f"## 基本面分析\n{fundamentals_report}"
    )

    runner = DebateRunner(max_rounds=max_debate_rounds)
    runner.add_participant("bull", lambda ctx: get_bull_argument(symbol, ctx))
    runner.add_participant("bear", lambda ctx: get_bear_argument(symbol, ctx))
    debate_state = runner.run_investment_debate(context)

    # Phase 3: Research Manager (通过 opencode subagent 调用)
    from .agents.research_manager import get_research_manager_prompt
    research_manager_prompt = get_research_manager_prompt(
        symbol=symbol,
        analyst_reports=analyst_reports,
        debate_summary=debate_state.combined_history,
    )

    # Phase 4: Portfolio Decision
    from .agents.portfolio_manager import get_portfolio_decision

    past_context = memory.get_context(symbol)

    decision_prompt = get_portfolio_decision(
        symbol=symbol,
        analyst_reports=analyst_reports,
        debate_summary=debate_state.combined_history,
        past_context=past_context,
    )

    return {
        "symbol": symbol,
        "trade_date": trade_date,
        "analyst_reports": analyst_reports,
        "debate_state": debate_state,
        "research_manager_prompt": research_manager_prompt,
        "decision_prompt": decision_prompt,
        "past_context": past_context,
    }
