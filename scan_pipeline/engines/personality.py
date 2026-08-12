"""
Personality system — agent personas, performance tracking, synthetic debate.
Ported from lib/engine/personality.ts
"""

import copy
import dataclasses
import datetime
import os
from typing import Dict, List, Optional, Any

try:
    import yaml  # PyYAML, same parser the paper tracker uses
except ImportError:  # pragma: no cover - fallback exercised only without PyYAML
    yaml = None


# ============================================================================
# DATA STRUCTURES (dataclasses for clean serialization)
# ============================================================================

@dataclasses.dataclass
class WeeklyResult:
    date: str
    thesis: str
    result: float
    confidence: Optional[float] = None


@dataclasses.dataclass
class ConversationTurn:
    persona: str
    thought: str
    dialogue: str
    struggle: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "persona": self.persona,
            "thought": self.thought,
            "dialogue": self.dialogue,
            "struggle": self.struggle,
        }


@dataclasses.dataclass
class AgentStats:
    picksAccuracy: float = 0.5
    portfolioContribution: float = 0.0
    confidenceCalibration: float = 0.5
    consensusInfluence: float = 0.33
    learningTrajectory: str = "stable"
    # Newest realized week already fed into picksAccuracy (idempotency guard).
    last_scored_week: Optional[str] = None


@dataclasses.dataclass
class Journal:
    latestEntry: str = ""
    bigWins: List[WeeklyResult] = dataclasses.field(default_factory=list)
    bigLosses: List[WeeklyResult] = dataclasses.field(default_factory=list)
    beliefs: List[str] = dataclasses.field(default_factory=list)
    lastBigWin: Optional[WeeklyResult] = None
    lastBigLoss: Optional[WeeklyResult] = None


@dataclasses.dataclass
class Evolution:
    strategySince: str = ""
    recentAdjustments: List[str] = dataclasses.field(default_factory=list)
    nextWeekPriority: str = ""


@dataclasses.dataclass
class Traits:
    confidence: int = 50
    skepticism: int = 50
    adaptability: int = 50
    collaboration: int = 50


@dataclasses.dataclass
class AIPersonality:
    name: str
    archetype: str
    style: str
    philosophy: str
    dataFocus: List[str] = dataclasses.field(default_factory=list)
    riskPreference: str = "moderate"
    traits: Traits = dataclasses.field(default_factory=Traits)
    journal: Journal = dataclasses.field(default_factory=Journal)
    stats: AgentStats = dataclasses.field(default_factory=AgentStats)
    evolution: Optional[Evolution] = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AIPersonality":
        traits = Traits(**d.get("traits", {}))
        journal_d = d.get("journal", {})
        journal = Journal(
            latestEntry=journal_d.get("latestEntry", ""),
            bigWins=[WeeklyResult(**w) for w in journal_d.get("bigWins", [])],
            bigLosses=[WeeklyResult(**w) for w in journal_d.get("bigLosses", [])],
            beliefs=journal_d.get("beliefs", []),
            lastBigWin=WeeklyResult(**journal_d["lastBigWin"]) if journal_d.get("lastBigWin") else None,
            lastBigLoss=WeeklyResult(**journal_d["lastBigLoss"]) if journal_d.get("lastBigLoss") else None,
        )
        stats = AgentStats(**d.get("stats", {}))
        evo_d = d.get("evolution")
        evolution = Evolution(**evo_d) if evo_d else None
        return cls(
            name=d["name"],
            archetype=d["archetype"],
            style=d.get("style", ""),
            philosophy=d.get("philosophy", ""),
            dataFocus=d.get("dataFocus", []),
            riskPreference=d.get("riskPreference", "moderate"),
            traits=traits,
            journal=journal,
            stats=stats,
            evolution=evolution,
        )


@dataclasses.dataclass
class AgentPerformance:
    proposals: List[str] = dataclasses.field(default_factory=list)
    inFinalPortfolio: List[str] = dataclasses.field(default_factory=list)
    confidence: float = 0.0
    contribution: float = 0.0
    accuracy: float = 0.0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class ConsensusMetrics:
    unanimousStocks: List[str] = dataclasses.field(default_factory=list)
    debatedStocks: List[str] = dataclasses.field(default_factory=list)
    uniqueStocks: List[str] = dataclasses.field(default_factory=list)
    averageConfidence: float = 0.0
    debateRounds: int = 3


@dataclasses.dataclass
class Reflection:
    whatWorked: str = ""
    whatFailed: str = ""
    lesson: str = ""
    nextWeekFocus: str = ""


@dataclasses.dataclass
class PerformanceReport:
    weekEndingDate: str
    portfolioReturn: float
    benchmarkReturn: float
    alpha: float
    agentContribution: Dict[str, AgentPerformance] = dataclasses.field(default_factory=dict)
    stockAttribution: Dict[str, Any] = dataclasses.field(default_factory=dict)
    consensusMetrics: ConsensusMetrics = dataclasses.field(default_factory=ConsensusMetrics)
    reflection: Reflection = dataclasses.field(default_factory=Reflection)

    def to_dict(self) -> dict:
        return {
            "weekEndingDate": self.weekEndingDate,
            "portfolioReturn": self.portfolioReturn,
            "benchmarkReturn": self.benchmarkReturn,
            "alpha": self.alpha,
            "agentContribution": {k: v.to_dict() for k, v in self.agentContribution.items()},
            "stockAttribution": self.stockAttribution,
            "consensusMetrics": dataclasses.asdict(self.consensusMetrics),
            "reflection": dataclasses.asdict(self.reflection),
        }


# ============================================================================
# INITIALIZE PERSONALITIES
# ============================================================================

_TODAY = datetime.date.today().isoformat()

CECIL_PERSONALITY = AIPersonality(
    name="Cecil",
    archetype="Fundamentalist",
    style="text-amber-300 border-amber-600/40 bg-amber-900/20",
    philosophy="Companies are like gardens; I nurture the ones with deep roots and despise the weeds of speculation. I search for the soul in the balance sheet.",
    dataFocus=["Free Cash Flow", "Dividend History", "Management Integrity", "Moat Durability", "P/E vs Historicals"],
    riskPreference="conservative",
    traits=Traits(confidence=65, skepticism=90, adaptability=30, collaboration=60),
    journal=Journal(
        latestEntry="The market is a noisy cocktail party. I prefer the quiet library of compounding returns.",
        beliefs=[
            "If you can't pay a dividend, you're just a concept art project.",
            "Time in the market beats timing the market, but value beats everything.",
        ]
    ),
    stats=AgentStats(picksAccuracy=0.5, portfolioContribution=0.0, confidenceCalibration=0.5, consensusInfluence=0.33, learningTrajectory="stable"),
    evolution=Evolution(strategySince=_TODAY, recentAdjustments=[], nextWeekPriority="Find the 'Aristocrats' that everyone else has abandoned for shiny toys.")
)

MARKY_PERSONALITY = AIPersonality(
    name="Marky",
    archetype="Technician",
    style="text-fuchsia-400 border-fuchsia-500/40 bg-fuchsia-900/20",
    philosophy="Price is the only truth! The chart is a sheet of music and I am dancing to the rhythm. Fundamentals are history; price is NOW.",
    dataFocus=["RSI Divergence", "Volume Spikes", "Moving Average Crossovers", "Fibonacci Retracements", "Meme Energy"],
    riskPreference="aggressive",
    traits=Traits(confidence=85, skepticism=20, adaptability=95, collaboration=50),
    journal=Journal(
        latestEntry="I feel the electricity in the order book. Something big is about to break.",
        beliefs=[
            "Catch the falling knife if it bounces hard enough.",
            "Trend is friend until the bend at the end.",
        ]
    ),
    stats=AgentStats(picksAccuracy=0.5, portfolioContribution=0.0, confidenceCalibration=0.5, consensusInfluence=0.33, learningTrajectory="stable"),
    evolution=Evolution(strategySince=_TODAY, recentAdjustments=[], nextWeekPriority="Hunt for the 'Golden Cross'. Ride the lightning.")
)

OPHELIA_PERSONALITY = AIPersonality(
    name="Ophelia",
    archetype="Macroeconomist",
    style="text-emerald-400 border-emerald-500/40 bg-emerald-900/20",
    philosophy="I am the Oracle of Volatility. While you play with toys, I read the tides of empires. The Fed, the oil, the fear—these are the only true charts. I do not guess; I prepare.",
    dataFocus=["Fed Dot Plot", "10Y Treasury Yield", "Geopolitical Risk Index", "Oil Volatility", "Credit Spreads"],
    riskPreference="moderate",
    traits=Traits(confidence=95, skepticism=85, adaptability=70, collaboration=40),
    journal=Journal(
        latestEntry="The storm does not care for your P/E ratios. The liquidity is shifting, and I am the only one watching the dam.",
        beliefs=[
            "Don't fight the Fed, and don't ignore the war drums.",
            "Cash is a position. Panic is an opportunity.",
        ]
    ),
    stats=AgentStats(picksAccuracy=0.5, portfolioContribution=0.0, confidenceCalibration=0.5, consensusInfluence=0.33, learningTrajectory="stable"),
    evolution=Evolution(strategySince=_TODAY, recentAdjustments=[], nextWeekPriority="Identify sectors that survive stagflation. Hedge the risk.")
)


def get_initial_personas() -> Dict[str, AIPersonality]:
    return {
        "Cecil": copy.deepcopy(CECIL_PERSONALITY),
        "Marky": copy.deepcopy(MARKY_PERSONALITY),
        "Ophelia": copy.deepcopy(OPHELIA_PERSONALITY),
    }


# ============================================================================
# PERFORMANCE REPORT
# ============================================================================

def calculate_performance_report(
    date: str,
    decision: dict,
    market_data: dict,
    portfolio_return: float,
) -> PerformanceReport:
    agent_names = ["Cecil", "Marky", "Ophelia"]
    agent_stats: Dict[str, AgentPerformance] = {name: AgentPerformance() for name in agent_names}

    weekly_returns = market_data.get("weeklyReturns", {})

    for ticker, weight in decision.get("portfolio", {}).items():
        attribution = decision.get("attribution", {}).get(ticker)
        stock_return = weekly_returns.get(ticker, 0.0)
        weighted_return = weight * stock_return
        if attribution and attribution in agent_stats:
            agent_stats[attribution].inFinalPortfolio.append(ticker)
            agent_stats[attribution].contribution += weighted_return
            agent_stats[attribution].confidence = decision.get("confidence", 0.0) * 100

    for stat in agent_stats.values():
        if stat.inFinalPortfolio:
            wins = sum(1 for t in stat.inFinalPortfolio if weekly_returns.get(t, 0.0) > 0)
            stat.accuracy = wins / len(stat.inFinalPortfolio)

    spy_return = weekly_returns.get("SPY", 0.0)

    return PerformanceReport(
        weekEndingDate=date,
        portfolioReturn=portfolio_return,
        benchmarkReturn=spy_return,
        alpha=portfolio_return - spy_return,
        agentContribution=agent_stats,
        consensusMetrics=ConsensusMetrics(
            averageConfidence=decision.get("confidence", 0.0),
            debateRounds=3
        ),
        reflection=Reflection(
            whatWorked="Portfolio allocation",
            whatFailed="Unhedged exposure",
            lesson="Consensus improves stability",
            nextWeekFocus="Refine entry points"
        )
    )


# ============================================================================
# REALIZED ACCURACY SCORING (StockApp/portfolio/history YAMLs)
# ============================================================================
# picksAccuracy is fed ONLY from realized per-pick P&L recorded by the paper
# tracker in closed history YAMLs. The engine's hypothetical weeklyReturns
# must never enter this EMA (corrupted feed, fixed 2026-08-11).

ACCURACY_EMA_ALPHA = 0.3

# Default location of the tracker's realized history files.
DEFAULT_HISTORY_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "StockApp", "portfolio", "history",
))


def _parse_history_minimal(text: str) -> dict:
    """Minimal line parser for tracker history YAMLs (PyYAML fallback only).

    Extracts top-level `status` and per-position `sponsor`/`pnl_pct` pairs.
    Sufficient because the scorer only needs those three fields.
    """
    data: Dict[str, Any] = {"status": None, "positions": []}
    current: Optional[dict] = None
    in_positions = False
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not in_positions:
            if stripped.startswith("status:"):
                data["status"] = stripped.split(":", 1)[1].strip().strip("'\"")
            elif stripped == "positions:":
                in_positions = True
            continue
        if stripped.startswith("- "):
            current = {}
            data["positions"].append(current)
            stripped = stripped[2:].strip()
            if not stripped:
                continue
        if current is None or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key == "sponsor":
            current["sponsor"] = value
        elif key == "pnl_pct":
            try:
                current["pnl_pct"] = float(value)
            except ValueError:
                current["pnl_pct"] = None
    return data


def _load_history_file(path: str) -> Optional[dict]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if yaml is not None:
        try:
            return yaml.safe_load(text)
        except Exception:
            return None
    return _parse_history_minimal(text)


def load_closed_weeks(history_dir: str = DEFAULT_HISTORY_DIR) -> Dict[str, Dict[str, dict]]:
    """Scan history YAMLs; return {week_date: {sponsor: {hits, total, mean_pnl}}}.

    Only weeks with top-level `status: closed` are scored. Positions missing
    a sponsor or pnl_pct are ignored.
    """
    weeks: Dict[str, Dict[str, dict]] = {}
    if not os.path.isdir(history_dir):
        return weeks
    for fname in sorted(os.listdir(history_dir)):
        if not fname.endswith(".yaml"):
            continue
        week_date = fname[:-len(".yaml")]
        data = _load_history_file(os.path.join(history_dir, fname))
        if not isinstance(data, dict) or data.get("status") != "closed":
            continue
        sponsors: Dict[str, dict] = {}
        for pos in data.get("positions") or []:
            if not isinstance(pos, dict):
                continue
            sponsor = pos.get("sponsor")
            pnl = pos.get("pnl_pct")
            if not sponsor or pnl is None:
                continue
            entry = sponsors.setdefault(sponsor, {"hits": 0, "total": 0, "pnl_sum": 0.0})
            entry["total"] += 1
            entry["pnl_sum"] += pnl
            if pnl > 0:
                entry["hits"] += 1
        for entry in sponsors.values():
            entry["mean_pnl"] = entry["pnl_sum"] / entry["total"] if entry["total"] else 0.0
            del entry["pnl_sum"]
        weeks[week_date] = sponsors
    return weeks


def realized_hit_rates(history_dir: str = DEFAULT_HISTORY_DIR) -> Dict[str, float]:
    """Trailing realized hit rate per sponsor across all closed history weeks.

    Sponsors with no booked positions in any closed week are absent from the
    result; callers must treat absence as 'no data', not zero.
    """
    totals: Dict[str, List[int]] = {}
    for sponsors in load_closed_weeks(history_dir).values():
        for sponsor, entry in sponsors.items():
            agg = totals.setdefault(sponsor, [0, 0])
            agg[0] += entry["hits"]
            agg[1] += entry["total"]
    return {s: hits / total for s, (hits, total) in totals.items() if total > 0}


def apply_realized_week(agent: AIPersonality, week_date: str, week_accuracy: float,
                        alpha: float = ACCURACY_EMA_ALPHA) -> bool:
    """Apply one realized week to the picksAccuracy EMA. Idempotent: a week
    already recorded in stats.last_scored_week is never re-applied."""
    stats = agent.stats
    if stats.last_scored_week and week_date <= stats.last_scored_week:
        return False
    stats.picksAccuracy = stats.picksAccuracy * (1 - alpha) + week_accuracy * alpha
    stats.last_scored_week = week_date
    return True


def update_accuracy_from_history(personas: Dict[str, AIPersonality],
                                 history_dir: str = DEFAULT_HISTORY_DIR,
                                 alpha: float = ACCURACY_EMA_ALPHA) -> Dict[str, AIPersonality]:
    """Feed each persona's picksAccuracy EMA from closed history YAMLs only.

    Shutout-safe: a persona with zero booked positions in a week is skipped
    entirely (no accuracy=0 push). Idempotent via stats.last_scored_week.
    """
    weeks = load_closed_weeks(history_dir)
    for week_date in sorted(weeks):
        for name, agent in personas.items():
            entry = weeks[week_date].get(name)
            if not entry or entry["total"] == 0:
                continue  # shutout guard: no booked picks, no EMA update
            apply_realized_week(agent, week_date, entry["hits"] / entry["total"], alpha)
    return personas


# ============================================================================
# UPDATE PERSONALITY
# ============================================================================

def update_agent_personality(agent: AIPersonality, week_result: PerformanceReport, agent_name: str) -> AIPersonality:
    """Backward-compatible wrapper kept for run_scan.py callers.

    picksAccuracy is delegated to the realized-history scorer; the
    hypothetical weeklyReturns-based accuracy in `week_result` is NO LONGER
    pushed into the EMA (that feed was corrupted). Journal/evolution updates
    from `week_result` are kept, guarded so the same week is never journaled
    twice.
    """
    updated = copy.deepcopy(agent)

    # Accuracy EMA: realized history only (idempotent, shutout-safe).
    update_accuracy_from_history({agent_name: updated})

    perf = week_result.agentContribution.get(agent_name)
    if not perf:
        return updated

    # Idempotency guard: never journal the same week twice.
    week_tag = f"Week of {week_result.weekEndingDate}:"
    if updated.evolution and any(a.startswith(week_tag) for a in updated.evolution.recentAdjustments):
        return updated

    accuracy = perf.accuracy
    contribution = perf.contribution
    confidence_match = abs((perf.confidence / 100) - accuracy)
    alpha = ACCURACY_EMA_ALPHA

    # NOTE: picksAccuracy is intentionally NOT updated here.
    updated.stats.portfolioContribution = updated.stats.portfolioContribution * (1 - alpha) + contribution * alpha
    updated.stats.confidenceCalibration = max(0.0, 1.0 - (confidence_match * alpha))

    if contribution > 0.03:
        win = WeeklyResult(
            date=week_result.weekEndingDate,
            thesis=", ".join(perf.inFinalPortfolio),
            result=contribution,
            confidence=perf.confidence
        )
        updated.journal.bigWins = (updated.journal.bigWins + [win])[-5:]
        updated.journal.lastBigWin = updated.journal.bigWins[-1]
    elif contribution < -0.03:
        loss = WeeklyResult(
            date=week_result.weekEndingDate,
            thesis=", ".join(perf.inFinalPortfolio),
            result=contribution,
            confidence=perf.confidence
        )
        updated.journal.bigLosses = (updated.journal.bigLosses + [loss])[-5:]
        updated.journal.lastBigLoss = updated.journal.bigLosses[-1]

    lesson = generate_lesson(updated, week_result, agent_name)
    if lesson and lesson not in updated.journal.beliefs:
        updated.journal.beliefs.append(lesson)
        if len(updated.journal.beliefs) > 5:
            updated.journal.beliefs.pop(0)

    if updated.evolution:
        updated.evolution.nextWeekPriority = generate_next_week_focus(updated, week_result, agent_name)
        updated.evolution.recentAdjustments.append(
            f"Week of {week_result.weekEndingDate}: Accuracy {accuracy*100:.0f}%, Contribution {contribution*100:.2f}%"
        )
        if len(updated.evolution.recentAdjustments) > 5:
            updated.evolution.recentAdjustments.pop(0)

    return updated


def generate_lesson(agent: AIPersonality, report: PerformanceReport, agent_name: str) -> str:
    perf = report.agentContribution.get(agent_name)
    if not perf:
        return ""
    was_overconfident = (perf.confidence / 100) > perf.accuracy
    was_accurate = perf.accuracy > 0.66

    if was_accurate and perf.contribution > 0.02:
        if agent.archetype == "Fundamentalist":
            return "See? Patience pays. The roots ran deep and the fruit was sweet."
        elif agent.archetype == "Technician":
            return "The chart painted a masterpiece and I signed it! Momentum is king!"
        else:
            return "The winds blew exactly as foretold. We sailed safely while others capsized."
    elif not was_accurate and perf.contribution < -0.02:
        if was_overconfident:
            return "I was blinded by my own brilliance. Hubris is the killer of returns."
        else:
            return "The market is irrational longer than I can remain solvent. I must adapt."
    return ""


def generate_next_week_focus(agent: AIPersonality, report: PerformanceReport, agent_name: str) -> str:
    perf = report.agentContribution.get(agent_name)
    if not perf or not agent.evolution:
        return agent.evolution.nextWeekPriority if agent.evolution else ""

    if agent.archetype == "Fundamentalist" and perf.accuracy < 0.5:
        return "I strayed too far from value. Back to the balance sheets. Look for cash cows."
    elif agent.archetype == "Technician" and perf.accuracy < 0.5:
        return "My indicators lied to me! I need tighter stops and cleaner breakouts."
    elif agent.archetype == "Macroeconomist" and perf.accuracy < 0.5:
        return "I misread the Fed's tea leaves. I must find the true safe haven."
    return "Stay the course. The strategy is breathing."


# ============================================================================
# SYNTHETIC DEBATE TEMPLATES
# ============================================================================

OPENING_TEMPLATES: Dict[str, List[str]] = {
    "Fundamentalist": [
        "I've identified deep value in {ticker}. The fundamentals are compelling at this valuation.",
        "My analysis points to {ticker} as a fortress of stability. Conviction: {score}.",
        "The balance sheet on {ticker} speaks louder than any chart. Score: {score}.",
    ],
    "Technician": [
        "The chart on {ticker} is screaming momentum! Technical score: {score}.",
        "Breakout confirmed on {ticker}. The tape doesn't lie. Conviction: {score}.",
        "Volume and price action on {ticker} are aligning perfectly. Score: {score}.",
    ],
    "Macroeconomist": [
        "The macro winds favor {ticker}. My model reads {score} on this one.",
        "Sector rotation is pointing directly at {ticker}. Confidence: {score}.",
        "The regime shift supports {ticker}. Macro score: {score}.",
    ],
}

REBUTTAL_TEMPLATES: Dict[str, List[str]] = {
    "Fundamentalist": [
        "{target}'s thesis on {ticker} lacks the cash flow to back it up. I see smoke, not fire.",
        "I respect {target}'s enthusiasm, but {ticker}'s valuation is stretched thin.",
        "{target} is chasing a narrative on {ticker}. Where are the fundamentals?",
    ],
    "Technician": [
        "{target}'s fundamental view on {ticker} ignores what the tape is screaming.",
        "Price action on {ticker} contradicts {target}'s thesis. Trust the chart.",
        "{target} is reading the balance sheet while the market is moving. {ticker} needs momentum.",
    ],
    "Macroeconomist": [
        "{target}'s micro view on {ticker} misses the structural headwinds I see.",
        "The macro dam is cracking, and {target}'s pick {ticker} is downstream.",
        "{target} ignores the Fed's shadow. {ticker} is sailing into a storm.",
    ],
}

THOUGHT_TEMPLATES: Dict[str, List[str]] = {
    "Fundamentalist": ["I must trust the numbers, not the noise.", "The balance sheet never lies."],
    "Technician": ["Price never lies. Never.", "The tape is speaking. Am I listening?"],
    "Macroeconomist": ["The big picture is always clearer from above.", "Don't fight the macro."],
}


def template_hash(ticker: str, agent_name: str) -> int:
    hash_val = 0
    s = ticker + agent_name
    for ch in s:
        hash_val = ((hash_val << 5) - hash_val) + ord(ch)
        hash_val |= 0
    return abs(hash_val)


def generate_opening_statement(agent: AIPersonality, proposal: dict) -> ConversationTurn:
    templates = OPENING_TEMPLATES.get(agent.archetype, [])
    h = template_hash(proposal["ticker"], agent.name)
    template = templates[h % len(templates)] if templates else ""
    dialogue = template.replace("{ticker}", proposal["ticker"]).replace("{score}", str(proposal["confidence"]))
    thoughts = THOUGHT_TEMPLATES.get(agent.archetype, [])
    thought = thoughts[h % len(thoughts)] if thoughts else ""
    return ConversationTurn(persona=agent.name, thought=thought, dialogue=dialogue)


def generate_rebuttal(agent: AIPersonality, target_agent: AIPersonality, target_proposal: dict) -> ConversationTurn:
    templates = REBUTTAL_TEMPLATES.get(agent.archetype, [])
    h = template_hash(target_proposal["ticker"], agent.name + target_agent.name)
    template = templates[h % len(templates)] if templates else ""
    dialogue = template.replace("{ticker}", target_proposal["ticker"]).replace("{target}", target_agent.name)
    thoughts = THOUGHT_TEMPLATES.get(agent.archetype, [])
    thought = thoughts[(h + 1) % len(thoughts)] if thoughts else ""
    return ConversationTurn(persona=agent.name, thought=thought, dialogue=dialogue)
