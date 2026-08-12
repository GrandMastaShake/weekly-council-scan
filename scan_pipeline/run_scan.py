"""
Run Scan — orchestrator: fetch → score → consensus → report
Ported from scan-pipeline architecture spec.

Usage:
    python run_scan.py --date 2025-07-14 --output report.md
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Ensure pipeline root is on path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from config.tickers import STOCK_UNIVERSE
from scan_pipeline.engines import cecil, marky, ophelia, consensus
from scan_pipeline.engines.personality import (
    CECIL_PERSONALITY,
    MARKY_PERSONALITY,
    OPHELIA_PERSONALITY,
    calculate_performance_report,
    update_accuracy_from_history,
    update_agent_personality,
)
from scan_pipeline.fetch_market_data import fetch_all_data
from scan_pipeline.fetch_context import fetch_macro_context
from scan_pipeline.utils.data_utils import PriceHistory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weekly Council Stock Scan")
    parser.add_argument("--date", type=str, default=None, help="Scan date (YYYY-MM-DD). Defaults to latest available.")
    parser.add_argument("--output", type=str, default="report.md", help="Output markdown report path.")
    parser.add_argument("--state-dir", type=str, default=os.path.join(SCRIPT_DIR, "state"), help="Directory for state persistence.")
    parser.add_argument("--fed-stance", type=str, default=None, help='Policy stance override, e.g. "Hold. Rates 3.50-3.75%." Must lead with a recognized stance word (Fix 2a); invalid values fall back to "Unknown. Stance source unavailable."')
    return parser.parse_args()


def load_state(state_dir: str) -> Dict[str, Any]:
    path = os.path.join(state_dir, "personas.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state_dir: str, state: Dict[str, Any]) -> None:
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, "personas.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o))


def init_personas(state: Dict[str, Any]) -> Dict[str, Any]:
    personas = state.get("personas")
    if not personas:
        personas = {
            "Cecil": CECIL_PERSONALITY,
            "Marky": MARKY_PERSONALITY,
            "Ophelia": OPHELIA_PERSONALITY,
        }
    else:
        from scan_pipeline.engines.personality import AIPersonality, Traits, Journal, AgentStats, Evolution
        def rebuild(p):
            if isinstance(p, AIPersonality):
                return p
            t = Traits(**p.get("traits", {}))
            j = Journal(**p.get("journal", {}))
            s = AgentStats(**p.get("stats", {}))
            ev = Evolution(**p.get("evolution", {})) if p.get("evolution") else None
            return AIPersonality(
                name=p["name"],
                archetype=p["archetype"],
                style=p.get("style", ""),
                philosophy=p.get("philosophy", ""),
                dataFocus=p.get("dataFocus", []),
                riskPreference=p.get("riskPreference", "moderate"),
                traits=t,
                journal=j,
                stats=s,
                evolution=ev,
            )
        personas = {k: rebuild(v) for k, v in personas.items()}
    return personas


def compute_portfolio_return(portfolio: Dict[str, float], weekly_returns: Dict[str, float]) -> float:
    return sum(weight * weekly_returns.get(ticker, 0.0) for ticker, weight in portfolio.items())


# ── Sanity-gate helpers ───────────────────────────────────────────────
CASH_FLOOR_DEFAULT = 0.15
HAWKISH_STANCES = {"hawkish", "tightening"}


def pe_fabrication_reason(stock: Dict[str, Any]) -> Optional[str]:
    """Return a drop reason when a pick's thesis cites a fabricated multiple."""
    src = stock.get("pe_source")
    thesis = stock.get("thesis", "")
    pe_val = stock.get("pe")
    if src == "synthetic":
        return "synthetic P/E fallback -- fabricated multiple on a booked pick"
    if (pe_val is not None and pe_val <= 0) and ("x earnings" in thesis or "P/E:" in thesis):
        return "negative EPS but thesis quotes a multiple -- value-anchor violation"
    return None


def append_rejection_log(state_dir: str, date: str, entries: List[Dict[str, Any]]) -> None:
    """Append gate rejections to state/rejection_log.json (cumulative list)."""
    if not entries:
        return
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, "rejection_log.json")
    log: List[Dict[str, Any]] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                log = loaded
        except (json.JSONDecodeError, OSError):
            log = []
    log.extend(entries)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def drop_fabricated_pe_picks(proposals: List[Any], date: str, state_dir: str) -> List[Dict[str, Any]]:
    """Gate 1: P/E provenance. Remove picks with fabricated multiples from each
    proposal (in place), log loudly, and let the week continue. Full-week abort
    is reserved for degenerate signal, not single-pick fabrication."""
    drops: List[Dict[str, Any]] = []
    for name, proposal in proposals:
        stocks = proposal.get("stocks", [])
        keep = []
        for s in stocks:
            reason = pe_fabrication_reason(s)
            gate = "pe-fabrication"
            if reason is None and s.get("exclude_reason"):
                # Engine self-exclusion (e.g. Cecil's earnings_proximity flag,
                # emitted with earnings_date / earnings_trading_days context).
                gate = "engine-exclusion"
                reason = (
                    f"{s['exclude_reason']} (earnings {s.get('earnings_date')}, "
                    f"{s.get('earnings_trading_days')} trading days out)"
                )
            if reason is None:
                keep.append(s)
            else:
                drops.append({
                    "date": date,
                    "gate": gate,
                    "engine": name,
                    "ticker": s.get("ticker"),
                    "reason": reason,
                })
        if len(keep) != len(stocks):
            proposal["stocks"] = keep
    for d in drops:
        print(f"[sanity] DROP: {d['engine']} {d['ticker']} -- {d['reason']}")
    append_rejection_log(state_dir, date, drops)
    return drops


def drop_book_positions(consensus_result: Dict[str, Any], tickers: set) -> List[str]:
    """Remove tickers from the final book and renormalize the remaining weights
    to the SAME invested fraction (not to 100%). Post-consensus safety net."""
    portfolio = consensus_result.get("portfolio", {})
    leaked = [t for t in tickers if t in portfolio]
    if not leaked:
        return []
    invested = sum(portfolio.values())
    for t in leaked:
        portfolio.pop(t, None)
        consensus_result.get("attribution", {}).pop(t, None)
    remaining = sum(portfolio.values())
    if remaining > 0:
        factor = invested / remaining
        for t in list(portfolio):
            portfolio[t] *= factor
    return leaked


def count_unresolved_ties(proposal: Dict[str, Any]) -> int:
    """Gate 2: count ONLY ties the tie-break tuple cannot resolve (exact
    equality through all tie-break keys). Consumed defensively so both the
    old and new ophelia.py work:
      - proposal["unresolved_ties_at_top"]: authoritative count (new contract).
      - per-stock stock["tie_break"]: ordered tie-break keys (new contract).
      - proposal["tied_at_top"]: legacy rounded-score count; fallback upper bound.
    """
    explicit = proposal.get("unresolved_ties_at_top")
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    # New ophelia.py contract: tie_resolvable=False means the tie survived
    # every tie-break key including the week_hash micro-term.
    resolvable = proposal.get("tie_resolvable")
    if resolvable is not None:
        return 0 if resolvable else int(proposal.get("tied_at_top", 0) or 0)
    stocks = proposal.get("stocks", [])
    keyed = [s for s in stocks if s.get("tie_break") is not None]
    if keyed:
        counts: Dict[Any, int] = {}
        for s in keyed:
            tb = s.get("tie_break")
            key = tuple(tb) if isinstance(tb, (list, tuple)) else (tb,)
            counts[key] = counts.get(key, 0) + 1
        # Group-size semantics match tied_at_top: members of unresolvable groups.
        return sum(c for c in counts.values() if c > 1)
    return int(proposal.get("tied_at_top", 0) or 0)


def load_macro_facts() -> Dict[str, Any]:
    """Read the canonical macro fact table truth_gate/macro/facts.json."""
    path = os.path.join(os.path.dirname(SCRIPT_DIR), "truth_gate", "macro", "facts.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[cash-floor] facts.json unreadable ({exc}); using market_conditions fallback")
        return {}


def _fact_value(facts: Dict[str, Any], *keys: str) -> Any:
    """Walk facts.json; unwrap the {"value": ...} leaf convention."""
    node: Any = facts
    for k in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(k)
    if isinstance(node, dict):
        return node.get("value")
    return node


def _stance_word(text: Any) -> str:
    """Leading stance word, same normalization as fetch_context._valid_stance."""
    if not isinstance(text, str):
        return ""
    return text.split(".", 1)[0].split(",", 1)[0].split(":", 1)[0].split(";", 1)[0].strip().lower()


def canary_raised(facts: Dict[str, Any]) -> bool:
    """Canary flag probe — defensive over plausible shapes; absent == not raised.
    facts.json (macro-facts/v1) currently carries no canary key; this watches
    for one without breaking on its absence."""
    if not isinstance(facts, dict):
        return False
    for key in ("canary", "canary_watch", "canary_flag"):
        node = facts.get(key)
        if isinstance(node, bool):
            return node
        if isinstance(node, dict):
            for sub in ("flag", "raised", "triggered", "value"):
                v = node.get(sub)
                if isinstance(v, bool):
                    return v
                if isinstance(v, str) and v.strip().lower() in ("raised", "true", "yes", "on"):
                    return True
    return False


def macro_floor_trigger(facts: Dict[str, Any], market_conditions: Dict[str, Any]) -> Optional[str]:
    """Return the reason the cash floor fires, else None. Sources:
    canary flag, or fed stance Hawkish/Tightening per facts.json
    (policy.fed_stance.value), with market_conditions fed_stance as fallback."""
    if canary_raised(facts):
        return "canary flag raised (truth_gate/macro/facts.json)"
    stance = _stance_word(_fact_value(facts, "policy", "fed_stance"))
    source = "facts.json policy.fed_stance"
    if not stance:
        stance = _stance_word(market_conditions.get("fed_stance"))
        source = "market_conditions fed_stance"
    if stance in HAWKISH_STANCES:
        return f"fed stance {stance!r} ({source})"
    return None


def apply_cash_floor(
    consensus_result: Dict[str, Any],
    facts: Dict[str, Any],
    market_conditions: Dict[str, Any],
    floor: float = CASH_FLOOR_DEFAULT,
) -> Optional[str]:
    """Gate 3 (T1): when macro is risk-off, scale all final weights by
    (1 - floor). The residual books as cash automatically — tracker.py
    computes cash_weight = 1 - sum(weights). Returns a log note or None."""
    portfolio = consensus_result.get("portfolio", {})
    if not portfolio:
        return None
    reason = macro_floor_trigger(facts, market_conditions)
    if not reason:
        return None
    scale = 1.0 - floor
    for t in list(portfolio):
        portfolio[t] = round(portfolio[t] * scale, 6)
    ust10 = _fact_value(facts, "rates", "ust_10y")
    note = (
        f"cash floor {floor:.0%} applied -- {reason}; ust_10y={ust10}; "
        f"invested={sum(portfolio.values()):.1%}, cash~{1.0 - sum(portfolio.values()):.1%}"
    )
    consensus_result["cash_floor"] = note
    return note


def generate_report(
    date: str,
    market_data: Dict[str, Any],
    consensus_result: Dict[str, Any],
    performance_report: Optional[Any],
    personas: Dict[str, Any],
    cecil_proposal: Dict[str, Any],
    marky_proposal: Dict[str, Any],
    ophelia_proposal: Dict[str, Any],
) -> str:
    """Canonical report layout — matches portfolio/tracker.py parse_report()."""
    lines = []
    lines.append(f"# Weekly Council Scan — {date}")
    lines.append("")

    # Market Context
    vix = market_data.get("vix", "N/A")
    spy_return = market_data.get("weeklyReturns", {}).get("SPY", 0.0)
    market_conditions = market_data.get("market_conditions", {})
    fed_stance = market_conditions.get("fed_stance", "Neutral")

    lines.append("## Market Context")
    lines.append(f"- **Date:** {date}")
    lines.append(f"- **VIX:** {vix}")
    lines.append(f"- **SPY Weekly Return:** {spy_return:+.2%}")
    lines.append(f"- **Fed Stance:** {fed_stance}")
    if consensus_result.get("cash_floor"):
        lines.append(f"- **Cash Floor:** {consensus_result['cash_floor']}")
    lines.append("")

    # Portfolio Picks
    portfolio = consensus_result.get("portfolio", {})
    attribution = consensus_result.get("attribution", {})
    lines.append("## Top 5 Portfolio Picks")
    lines.append("| Ticker | Weight | Sponsor |")
    lines.append("|---|---|---|")
    for ticker, weight in sorted(portfolio.items(), key=lambda x: -x[1]):
        sponsor = attribution.get(ticker, "Unknown")
        lines.append(f"| {ticker} | {weight:.1%} | {sponsor} |")
    lines.append("")

    # Council Debate
    lines.append("## Council Debate")
    for turn in consensus_result.get("conversation", []):
        lines.append(f"**{turn['persona']}:** *{turn['thought']}*")
        lines.append(f"> {turn['dialogue']}")
        lines.append("")
    lines.append(f"**Final Consensus:** {consensus_result.get('reasoning', '')}")
    lines.append("")
    lines.append(f"**Confidence:** {consensus_result.get('confidence', 0.0):.1%}")
    lines.append("")

    # Agent Proposals
    archetypes = {"Cecil": "Fundamentalist", "Marky": "Technician", "Ophelia": "Macroeconomist"}
    lines.append("## Agent Proposals")
    lines.append("")
    for proposal in (cecil_proposal, marky_proposal, ophelia_proposal):
        agent = proposal.get("agent", "Unknown")
        lines.append(f"### {agent} ({archetypes.get(agent, 'Analyst')})")
        for stock in proposal.get("stocks", []):
            thesis = stock.get("thesis", "")
            confidence = stock.get("confidence", 0)
            lines.append(f"- **{stock['ticker']}** — {thesis} (confidence: {confidence:g})")
        lines.append("")

    return "\n".join(lines)


def generate_abort_report(
    date: str,
    market_data: Dict[str, Any],
    failures: List[str],
    proposals: List[Dict[str, Any]],
) -> str:
    """ENGINE ABORT report — published when the sanity gate blocks the book.
    Canonical sections stay parseable; the picks table is deliberately empty
    so the tracker opens no positions."""
    lines = []
    lines.append(f"# Weekly Council Scan — {date}")
    lines.append("")
    vix = market_data.get("vix", "N/A")
    spy_return = market_data.get("weeklyReturns", {}).get("SPY", 0.0)
    market_conditions = market_data.get("market_conditions", {})
    fed_stance = market_conditions.get("fed_stance", "Neutral")
    lines.append("## Market Context")
    lines.append(f"- **Date:** {date}")
    lines.append(f"- **VIX:** {vix}")
    lines.append(f"- **SPY Weekly Return:** {spy_return:+.2%}")
    lines.append(f"- **Fed Stance:** {fed_stance}")
    lines.append("")
    lines.append("## Top 5 Portfolio Picks")
    lines.append("| Ticker | Weight | Sponsor |")
    lines.append("|---|---|---|")
    lines.append("")
    lines.append("> 🚨 **ENGINE ABORT — the pre-publication sanity gate blocked this book.**")
    lines.append("> The engine signal degenerated; publishing picks would book noise.")
    for f in failures:
        lines.append(f"> - {f}")
    lines.append("> No positions were opened. Logged to shadow-book.md.")
    lines.append("")
    archetypes = {"Cecil": "Fundamentalist", "Marky": "Technician", "Ophelia": "Macroeconomist"}
    lines.append("## Agent Proposals")
    lines.append("")
    lines.append("*Raw engine output below is diagnostic only — nothing was booked.*")
    lines.append("")
    for proposal in proposals:
        agent = proposal.get("agent", "Unknown")
        lines.append(f"### {agent} ({archetypes.get(agent, 'Analyst')})")
        for stock in proposal.get("stocks", []):
            thesis = stock.get("thesis", "")
            confidence = stock.get("confidence", 0)
            lines.append(f"- **{stock['ticker']}** — {thesis} (confidence: {confidence:g})")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    state_dir = args.state_dir
    output_path = args.output

    # Determine effective date
    if args.date:
        date = args.date
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    # Load state
    state = load_state(state_dir)
    personas = init_personas(state)
    # Refresh picksAccuracy from closed portfolio/history YAMLs BEFORE consensus
    # so this week's votes reflect realized results (idempotent via
    # last_scored_week; failures must never block the scan).
    try:
        update_accuracy_from_history(personas)
    except Exception as exc:
        print(f"[personality] pre-consensus accuracy refresh failed (non-fatal): {exc}")

    # Fetch data
    market_data, price_cache, pe_cache = fetch_all_data(STOCK_UNIVERSE, date)

    # Update date to latest available if not explicitly provided
    if not args.date:
        spy_histories = price_cache.get("SPY", [])
        if spy_histories:
            date = spy_histories[-1].date
        else:
            date = datetime.now().strftime("%Y-%m-%d")
        market_data["date"] = date

    # Fetch macro context
    macro_context = fetch_macro_context(fed_stance_override=args.fed_stance)
    market_data["market_conditions"] = macro_context

    # Run engines
    cecil_proposal = cecil.analyze(market_data, date)
    marky_proposal = marky.analyze(market_data, date, price_cache)
    ophelia_proposal = ophelia.analyze(market_data, date, price_cache)

    # ── Pre-publication sanity gate ──────────────────────────────────────
    # A fabricated P/E on a single pick: DROP the pick, log loudly, continue.
    # Full-week abort is reserved for degenerate signal: flat confidence,
    # unresolvable ties, all engines empty, or benchmark (SPY) data missing.
    proposals = [
        ("Cecil", cecil_proposal),
        ("Marky", marky_proposal),
        ("Ophelia", ophelia_proposal),
    ]

    # Gate 1: P/E provenance (2026-08-03 SYM incident) -- pick-drop path.
    drops = drop_fabricated_pe_picks(proposals, date, state_dir)

    failures: List[str] = []
    # Degenerate-mode guards (post-drop).
    if all(not p.get("stocks") for _, p in proposals):
        failures.append("all engines returned empty proposals after gate drops -- degenerate mode")
    if market_data.get("weeklyReturns", {}).get("SPY") is None:
        failures.append("SPY weekly return missing -- benchmark degenerate mode")
    for name, proposal in proposals:
        if proposal.get("data_degraded"):
            reasons = ", ".join(proposal.get("data_degraded_reasons") or ["unspecified"])
            failures.append(f"{name}: data_degraded ({reasons}) -- engine inputs failed to load")

    for name, proposal in proposals:
        stocks = proposal.get("stocks", [])
        # Gate 2: only ties the tie-break tuple cannot resolve count.
        tied = count_unresolved_ties(proposal)
        if tied > 3:
            failures.append(f"{name}: {tied} tickers tied at top with unresolvable tie-break (limit 3) -- engine inputs likely flat/degenerate")
        confs = [s.get("confidence") for s in stocks if s.get("confidence") is not None]
        if len(confs) >= 3 and (max(confs) - min(confs)) <= 2.0:
            failures.append(f"{name}: top-3 confidence spread is {max(confs) - min(confs):.2f} pts (limit 2.0) -- flat signal")
        # Confidence diagnostics per pick
        for s in stocks:
            raw = s.get("confidence_raw", "n/a")
            raw_txt = f"{raw:.2f}" if isinstance(raw, (int, float)) else str(raw)
            print(f"[confidence] {name} {s.get('ticker', '?')}: raw={raw_txt} published={s.get('confidence', 'n/a')}")

    if failures:
        for f in failures:
            print(f"[sanity] BLOCK: {f}")
        # Write the abort report — canonical layout, empty picks table
        abort_md = generate_abort_report(
            date, market_data, failures, [p for _, p in proposals]
        )
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(abort_md)
        # Dump machine-readable diagnostics for post-mortem
        os.makedirs(state_dir, exist_ok=True)
        abort_state = {
            "date": date,
            "failures": failures,
            "engine_stocks": {name: p.get("stocks", []) for name, p in proposals},
        }
        with open(os.path.join(state_dir, "engine_abort.json"), "w", encoding="utf-8") as f:
            json.dump(abort_state, f, indent=2)
        print(f"[sanity] ENGINE ABORT — abort report written to {output_path}; state/engine_abort.json dumped. No positions booked.")
        sys.exit(2)

    # Consensus
    consensus_result = consensus.aggregate(cecil_proposal, marky_proposal, ophelia_proposal, personas).to_dict()

    # Post-consensus safety net: a dropped ticker must never reach the book.
    # Consensus is rebuilt from cleaned proposals, so this should be a no-op;
    # if one leaks through, drop it and renormalize to the same invested sum.
    if drops:
        leaked = drop_book_positions(consensus_result, {d["ticker"] for d in drops})
        if leaked:
            print(f"[sanity] DROP(post-consensus): removed {leaked} from book; weights renormalized")
            append_rejection_log(state_dir, date, [{
                "date": date,
                "gate": "pe-fabrication-post-consensus",
                "engine": consensus_result.get("attribution", {}).get(t, "Unknown"),
                "ticker": t,
                "reason": "leaked into book after pre-consensus drop; removed and renormalized",
            } for t in leaked])

    # Gate 3 (T1): cash floor. When macro is risk-off (canary flag raised, or
    # fed stance Hawkish/Tightening per truth_gate/macro/facts.json), scale all
    # weights by (1 - floor); the residual books as cash automatically --
    # tracker.py computes cash_weight = 1 - sum(weights).
    macro_facts = load_macro_facts()
    floor_note = apply_cash_floor(
        consensus_result, macro_facts, market_data.get("market_conditions", {})
    )
    if floor_note:
        print(f"[cash-floor] {floor_note}")

    # Performance report (evaluate previous decision if available).
    # NOTE (Agent A coordination): picksAccuracy updates are migrating to
    # closed portfolio/history YAMLs with a last_scored_week idempotency
    # guard; the weeklyReturns-driven path below becomes a deprecated no-op
    # wrapper. personality.py keeps the signatures backward compatible, so
    # this call site is intentionally unchanged. The update must never block
    # the scan -- failures are logged and skipped.
    performance_report = None
    last_decision = state.get("last_decision")
    if last_decision:
        try:
            prev_portfolio = last_decision.get("portfolio", {})
            portfolio_return = compute_portfolio_return(prev_portfolio, market_data.get("weeklyReturns", {}))
            performance_report = calculate_performance_report(
                date=date,
                decision=last_decision,
                market_data=market_data,
                portfolio_return=portfolio_return,
            )
            # Update personalities
            for name in ["Cecil", "Marky", "Ophelia"]:
                personas[name] = update_agent_personality(personas[name], performance_report, name)
        except Exception as exc:
            print(f"[personality] accuracy-feed update failed (non-fatal): {exc}")
            performance_report = None

    # Save state
    state["personas"] = personas
    state["last_decision"] = {
        "date": date,
        "portfolio": consensus_result["portfolio"],
        "attribution": consensus_result["attribution"],
        "confidence": consensus_result["confidence"],
    }
    save_state(state_dir, state)

    # Generate report
    report_md = generate_report(
        date, market_data, consensus_result, performance_report, personas,
        cecil_proposal, marky_proposal, ophelia_proposal
    )

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"[run_scan] Report written to {output_path}")


if __name__ == "__main__":
    main()
