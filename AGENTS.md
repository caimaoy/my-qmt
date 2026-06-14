# Project Guidelines

## Package Manager

This project uses **uv** for Python package management.

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Run scripts
uv run python main.py

# Run with dev dependencies
uv run --dev pytest
```

Do NOT use pip, poetry, or conda.

## Architecture

This is a multi-agent LLM trading framework inspired by TradingAgents. LLM integration is handled via opencode subagent system — no direct LLM API calls in Python.

### Data Layer

- **SQLite cache**: `~/.my_qmt/cache/stock_data.db`
  - 5,102 A-share stocks, 306,050 rows, ~41MB
  - Auto-incremental update (only fetches missing dates)
  - Cache validity: K-line 24h, index constituents 7 days
- **A-share data**: `tradingagents/dataflows/a_share_data.py`
  - AKShare → Tencent Finance fallback chain
  - `get_stock_data(symbol, days=60, use_cache=True)`
  - `scan_stocks_by_indicator(stocks, indicator, threshold, ...)`
- **Indicators**: `tradingagents/indicators/technical.py`
  - 8 indicators: SMA, EMA, MACD, RSI, Bollinger Bands, ATR, VWAP, OBV
  - `compute_all_indicators(df)` returns DataFrame with all indicators
- **Chinese news**: `tradingagents/dataflows/china_news.py`
  - 东方财富/新浪财经/雪球 (A-shares), 新浪港股 (HK stocks)

### Agent System

- **8 agents** in `tradingagents/agents/`:
  - market_analyst, sentiment_analyst, news_analyst, fundamentals_analyst
  - bull_researcher, bear_researcher, research_manager, portfolio_manager
- **Subagent configs**: `.opencode/agents/*.md` (8 files)
- **Skills**:
  - `multi-agent-analysis`: Full 8-agent pipeline
  - `stock-price-api`: Stock price data retrieval
  - `a-share-analysis`: Batch scanning by indicators

### Key Commands

```bash
# Full analysis
uv run python -m tradingagents.main analyze AAPL
uv run python -m tradingagents.main analyze 600519.SS  # A-share

# A-share batch scan (from opencode subagent)
from tradingagents.dataflows.a_share_data import scan_stocks_by_indicator, format_scan_results_markdown
results = scan_stocks_by_indicator(stocks, indicator="rsi_below", threshold=25, days=60, limit=20, use_cache=True)
```

## Conventions

- A-share stock codes: `"600519"` (6 digits, no suffix)
- HK stocks: `"0700.HK"`
- US stocks: `"AAPL"`
- Cache location: `~/.my_qmt/cache/` (user preference, not `~/.tradingagents/`)
