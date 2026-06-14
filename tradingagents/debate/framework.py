"""Debate framework for multi-agent discussions.

Supports two debate modes:
- Investment debate (Bull vs Bear)
- Risk debate (Aggressive vs Conservative vs Neutral)
"""

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class DebateMessage:
    """A single message in a debate."""

    role: str  # e.g., "bull", "bear", "aggressive", "conservative", "neutral"
    content: str
    round_num: int


@dataclass
class InvestmentDebateState:
    """State for Bull vs Bear investment debate."""

    bull_history: list[DebateMessage] = field(default_factory=list)
    bear_history: list[DebateMessage] = field(default_factory=list)
    combined_history: str = ""
    current_response: str = ""
    count: int = 0
    max_rounds: int = 1
    judge_decision: str = ""

    @property
    def is_complete(self) -> bool:
        return self.count >= 2 * self.max_rounds

    def add_message(self, role: str, content: str):
        msg = DebateMessage(role=role, content=content, round_num=self.count)
        if role == "bull":
            self.bull_history.append(msg)
        else:
            self.bear_history.append(msg)
        self.current_response = content
        self.count += 1
        self._update_combined_history()

    def _update_combined_history(self):
        all_msgs = sorted(
            self.bull_history + self.bear_history, key=lambda m: m.round_num
        )
        self.combined_history = "\n\n".join(
            f"**{m.role.upper()} (Round {m.round_num // 2 + 1}):**\n{m.content}"
            for m in all_msgs
        )

    def get_context(self, role: str) -> str:
        """Get debate context for a specific role."""
        own = self.bull_history if role == "bull" else self.bear_history
        other = self.bear_history if role == "bull" else self.bull_history

        context = ""
        if own:
            context += f"Your previous arguments:\n{own[-1].content}\n\n"
        if other:
            context += f"Opponent's latest argument:\n{other[-1].content}\n\n"
        return context


@dataclass
class RiskDebateState:
    """State for 3-way risk debate (Aggressive vs Conservative vs Neutral)."""

    aggressive_history: list[DebateMessage] = field(default_factory=list)
    conservative_history: list[DebateMessage] = field(default_factory=list)
    neutral_history: list[DebateMessage] = field(default_factory=list)
    current_response: str = ""
    latest_speaker: str = ""
    count: int = 0
    max_rounds: int = 1
    judge_decision: str = ""

    _SPEAKER_ORDER = ["aggressive", "conservative", "neutral"]

    @property
    def is_complete(self) -> bool:
        return self.count >= 3 * self.max_rounds

    def add_message(self, role: str, content: str):
        msg = DebateMessage(role=role, content=content, round_num=self.count)
        if role == "aggressive":
            self.aggressive_history.append(msg)
        elif role == "conservative":
            self.conservative_history.append(msg)
        else:
            self.neutral_history.append(msg)
        self.current_response = content
        self.latest_speaker = role
        self.count += 1

    def get_next_speaker(self) -> str:
        """Determine who speaks next."""
        if not self.latest_speaker:
            return self._SPEAKER_ORDER[0]
        idx = self._SPEAKER_ORDER.index(self.latest_speaker)
        return self._SPEAKER_ORDER[(idx + 1) % 3]

    def get_context(self, role: str) -> str:
        """Get debate context for a specific role."""
        histories = {
            "aggressive": self.aggressive_history,
            "conservative": self.conservative_history,
            "neutral": self.neutral_history,
        }
        own = histories[role]
        others = {k: v for k, v in histories.items() if k != role}

        context = ""
        if own:
            context += f"Your previous arguments:\n{own[-1].content}\n\n"
        for other_role, msgs in others.items():
            if msgs:
                context += f"{other_role.capitalize()}'s latest argument:\n{msgs[-1].content}\n\n"
        return context


class DebateRunner:
    """Runs a debate between agents.

    Usage:
        runner = DebateRunner(max_rounds=1)
        runner.add_participant("bull", bull_agent_func)
        runner.add_participant("bear", bear_agent_func)
        result = runner.run_investment_debate(context="...")
    """

    def __init__(self, max_rounds: int = 1):
        self.max_rounds = max_rounds
        self._participants: dict[str, Callable] = {}

    def add_participant(self, role: str, agent_func: Callable[[str], str]):
        """Register a debate participant.

        Args:
            role: Role name (e.g., "bull", "bear")
            agent_func: Function that takes context string and returns response
        """
        self._participants[role] = agent_func

    def run_investment_debate(self, context: str) -> InvestmentDebateState:
        """Run a Bull vs Bear investment debate.

        Args:
            context: Shared context (analyst reports, etc.)

        Returns:
            Final debate state with all arguments
        """
        state = InvestmentDebateState(max_rounds=self.max_rounds)

        while not state.is_complete:
            # Bull's turn
            if state.count % 2 == 0:
                role = "bull"
            else:
                role = "bear"

            agent_func = self._participants[role]
            debate_context = state.get_context(role)
            prompt = f"{context}\n\n{debate_context}\n\nAs the {role} researcher, present your argument."
            response = agent_func(prompt)
            state.add_message(role, response)

        return state

    def run_risk_debate(self, context: str) -> RiskDebateState:
        """Run a 3-way risk debate.

        Args:
            context: Shared context (trader proposal, etc.)

        Returns:
            Final debate state with all arguments
        """
        state = RiskDebateState(max_rounds=self.max_rounds)

        while not state.is_complete:
            role = state.get_next_speaker()
            agent_func = self._participants[role]
            debate_context = state.get_context(role)
            prompt = f"{context}\n\n{debate_context}\n\nAs the {role} analyst, present your risk assessment."
            response = agent_func(prompt)
            state.add_message(role, response)

        return state
