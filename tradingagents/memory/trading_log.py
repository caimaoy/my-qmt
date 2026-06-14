"""Trading memory log - append-only decision log with deferred reflection.

3-phase loop:
1. Store: After each decision, append to log as "pending"
2. Resolve: On next run, fetch actual returns and generate reflection
3. Inject: Past reflections are injected as context for Portfolio Manager
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class TradingEntry:
    """A single trading decision entry."""

    date: str
    ticker: str
    rating: str
    decision_summary: str
    raw_return: float | None = None
    alpha_return: float | None = None
    holding_days: int | None = None
    reflection: str = ""
    status: str = "pending"  # pending, resolved


# 基准指数映射
BENCHMARK_MAP = {
    # 美股
    "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM",
    # A股
    "000001.SS": "000001.SS",  # 上证指数
    "399001.SZ": "399001.SZ",  # 深证成指
    # 港股
    "^HSI": "^HSI",
    # 日股
    "^N225": "^N225",
}


def _get_benchmark(ticker: str) -> str:
    """根据股票代码选择基准指数"""
    if ticker.endswith(".SS") or ticker.endswith(".SZ"):
        return "000001.SS" if ticker.endswith(".SS") else "399001.SZ"
    return "SPY"


def _fetch_returns(ticker: str, entry_date: str, current_date: str | None = None) -> tuple[float | None, float | None]:
    """获取股票和基准的收益率

    Args:
        ticker: 股票代码
        entry_date: 入场日期 (yyyy-mm-dd)
        current_date: 当前日期，默认今天

    Returns:
        (raw_return, alpha_return) 元组
    """
    try:
        import yfinance as yf

        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")

        # 计算持有天数
        start_dt = datetime.strptime(entry_date, "%Y-%m-%d")
        end_dt = datetime.strptime(current_date, "%Y-%m-%d")
        holding_days = (end_dt - start_dt).days

        if holding_days < 1:
            return None, None

        # 获取股票收益
        stock = yf.Ticker(ticker)
        stock_data = stock.history(start=entry_date, end=current_date)

        if stock_data.empty or len(stock_data) < 2:
            return None, None

        stock_return = (stock_data["Close"].iloc[-1] / stock_data["Close"].iloc[0] - 1) * 100

        # 获取基准收益
        benchmark = _get_benchmark(ticker)
        bench = yf.Ticker(benchmark)
        bench_data = bench.history(start=entry_date, end=current_date)

        if bench_data.empty or len(bench_data) < 2:
            return stock_return, None

        bench_return = (bench_data["Close"].iloc[-1] / bench_data["Close"].iloc[0] - 1) * 100
        alpha = stock_return - bench_return

        return round(stock_return, 2), round(alpha, 2)

    except Exception:
        return None, None


def _generate_reflection_prompt(entry: TradingEntry, raw_return: float, alpha_return: float) -> str:
    """生成反思 prompt"""
    return f"""你是一个投资反思助手。请根据以下交易决策和实际结果，生成简洁的反思。

## 交易决策
- 日期: {entry.date}
- 股票: {entry.ticker}
- 评级: {entry.rating}
- 决策摘要: {entry.decision_summary}

## 实际结果
- 原始收益: {raw_return:.2f}%
- 超额收益 (vs 基准): {alpha_return:.2f}%
- 持有天数: {entry.holding_days or '未知'} 天

## 请生成反思 (2-4句话)
1. 方向判断是否正确？
2. 决策逻辑是否经受住检验？
3. 有什么经验教训？

请直接输出反思内容，不要添加额外格式。"""


class TradingMemoryLog:
    """Append-only markdown decision log with deferred reflection.

    3-phase deferred reflection:
    Phase A (Store): After each decision, append as "pending"
    Phase B (Resolve): On next run, fetch returns, generate reflection
    Phase C (Inject): Past reflections injected as context for PM

    Usage:
        log = TradingMemoryLog("~/.tradingagents/memory/trading_memory.md")
        log.append(date="2024-01-15", ticker="AAPL", rating="Buy", summary="Strong momentum")
        context = log.get_context(ticker="AAPL", max_entries=5)
    """

    def __init__(self, log_path: str = "~/.tradingagents/memory/trading_memory.md"):
        self.log_path = Path(log_path).expanduser()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[TradingEntry] = []
        self._load()

    def _load(self):
        """Load entries from the log file."""
        if not self.log_path.exists():
            return

        content = self.log_path.read_text()
        for line in content.split("\n"):
            line = line.strip()
            if not line.startswith("|") or "---" in line or "Date" in line:
                continue
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 6:
                entry = TradingEntry(
                    date=parts[0],
                    ticker=parts[1],
                    rating=parts[2],
                    decision_summary=parts[3],
                    raw_return=float(parts[4]) if parts[4] != "-" else None,
                    alpha_return=float(parts[5]) if parts[5] != "-" else None,
                    holding_days=int(parts[6]) if len(parts) > 6 and parts[6] != "-" else None,
                    reflection=parts[7] if len(parts) > 7 else "",
                    status="resolved" if parts[4] != "-" else "pending",
                )
                self._entries.append(entry)

    def append(
        self,
        date: str,
        ticker: str,
        rating: str,
        summary: str,
    ):
        """Append a new trading decision (Phase A: Store).

        Args:
            date: Decision date (yyyy-mm-dd)
            ticker: Ticker symbol
            rating: Portfolio rating (Buy/Hold/Sell/etc.)
            summary: Decision summary
        """
        entry = TradingEntry(
            date=date,
            ticker=ticker,
            rating=rating,
            decision_summary=summary,
        )
        self._entries.append(entry)
        self._save()

    def resolve_pending(
        self,
        current_date: str | None = None,
        llm_func=None,
    ) -> int:
        """Resolve pending entries by fetching returns and generating reflections (Phase B).

        Args:
            current_date: Current date for return calculation (default: today)
            llm_func: LLM function for generating reflections (optional)
                      Signature: llm_func(prompt: str) -> str

        Returns:
            Number of entries resolved
        """
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")

        resolved_count = 0

        for entry in self._entries:
            if entry.status != "pending":
                continue

            # 计算持有天数
            try:
                start_dt = datetime.strptime(entry.date, "%Y-%m-%d")
                end_dt = datetime.strptime(current_date, "%Y-%m-%d")
                holding_days = (end_dt - start_dt).days
            except ValueError:
                continue

            # 至少持有 1 天才能计算收益
            if holding_days < 1:
                continue

            # 获取收益率
            raw_return, alpha_return = _fetch_returns(entry.ticker, entry.date, current_date)

            if raw_return is None:
                continue

            # 更新 entry
            entry.raw_return = raw_return
            entry.alpha_return = alpha_return
            entry.holding_days = holding_days

            # 生成反思 (如果有 LLM)
            if llm_func:
                prompt = _generate_reflection_prompt(entry, raw_return, alpha_return)
                try:
                    entry.reflection = llm_func(prompt)
                except Exception:
                    entry.reflection = _generate_default_reflection(raw_return, alpha_return)
            else:
                entry.reflection = _generate_default_reflection(raw_return, alpha_return)

            entry.status = "resolved"
            resolved_count += 1

        if resolved_count > 0:
            self._save()

        return resolved_count

    def get_context(
        self,
        ticker: str,
        max_entries: int = 5,
        max_cross_ticker: int = 3,
    ) -> str:
        """Get past decisions and reflections as context (Phase C: Inject).

        Args:
            ticker: Current ticker (prioritizes same-ticker entries)
            max_entries: Max same-ticker entries
            max_cross_ticker: Max cross-ticker entries

        Returns:
            Formatted context string
        """
        same_ticker = [e for e in self._entries if e.ticker == ticker and e.status == "resolved"]
        cross_ticker = [e for e in self._entries if e.ticker != ticker and e.status == "resolved"]

        context = ""
        if same_ticker:
            recent = same_ticker[-max_entries:]
            context += f"## 过去的决策 ({ticker})\n\n"
            for e in recent:
                context += f"- **{e.date}** | 评级: {e.rating} | 收益: {e.raw_return or '-'}% | 超额: {e.alpha_return or '-'}%\n"
                if e.reflection:
                    context += f"  反思: {e.reflection}\n"

        if cross_ticker:
            recent = cross_ticker[-max_cross_ticker:]
            context += "\n## 跨股票经验\n\n"
            for e in recent:
                context += f"- **{e.date}** | {e.ticker} | 评级: {e.rating} | 收益: {e.raw_return or '-'}%\n"
                if e.reflection:
                    context += f"  反思: {e.reflection}\n"

        return context or "没有过去的决策记录。"

    def _save(self):
        """Save entries to the log file (atomic write)."""
        header = "| Date | Ticker | Rating | Summary | Raw Return | Alpha Return | Holding Days | Reflection |\n"
        header += "|------|--------|--------|---------|------------|--------------|--------------|------------|\n"

        rows = ""
        for e in self._entries:
            rows += (
                f"| {e.date} | {e.ticker} | {e.rating} | {e.decision_summary} "
                f"| {e.raw_return if e.raw_return is not None else '-'} "
                f"| {e.alpha_return if e.alpha_return is not None else '-'} "
                f"| {e.holding_days if e.holding_days is not None else '-'} "
                f"| {e.reflection} |\n"
            )

        content = header + rows

        # Atomic write
        tmp_path = self.log_path.with_suffix(".tmp")
        tmp_path.write_text(content)
        os.replace(tmp_path, self.log_path)


def _generate_default_reflection(raw_return: float, alpha_return: float) -> str:
    """生成默认反思 (无 LLM 时使用)"""
    direction = "正确" if raw_return > 0 else "错误"
    alpha_desc = "跑赢" if alpha_return > 0 else "跑输"

    return (
        f"方向判断{direction}，原始收益 {raw_return:.2f}%，"
        f"{alpha_desc}基准 {abs(alpha_return):.2f}%。"
    )
