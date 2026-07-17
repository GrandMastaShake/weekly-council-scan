#!/usr/bin/env python3
"""
Paper Portfolio Tracker — Market Consciousness Orchestra

Tracks the Council's weekly picks as if they were actually traded.
- Records entry prices on Monday (from scan report context)
- Tracks through Friday close
- Checks stop losses during the week
- Calculates P&L, Sharpe, max drawdown, alpha vs SPY
- Updates the scoreboard with actual returns

Usage:
    python portfolio/tracker.py --open 2026-07-21  # Open new week
    python portfolio/tracker.py --close 2026-07-21 # Close previous week
    python portfolio/tracker.py --full 2026-07-21  # Close prior + open new
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# --- Paths ---
REPO_ROOT = Path(__file__).parent.parent
PORTFOLIO_DIR = REPO_ROOT / "portfolio"
HISTORY_DIR = PORTFOLIO_DIR / "history"
REPORTS_DIR = REPO_ROOT / "reports"
SCORECARDS_DIR = REPO_ROOT / "scorecards"
SCOREBOARD_PATH = REPO_ROOT / "scoreboard.md"
METRICS_PATH = PORTFOLIO_DIR / "metrics.json"
CURRENT_PATH = PORTFOLIO_DIR / "current.yaml"

for d in [PORTFOLIO_DIR, HISTORY_DIR, SCORECARDS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# --- Price Fetching ---

def fetch_yf_price(ticker: str, date: datetime) -> Optional[float]:
    """Fetch closing price for a ticker on a given date using yfinance."""
    try:
        import yfinance as yf
        start = (date - timedelta(days=5)).strftime("%Y-%m-%d")
        end = (date + timedelta(days=1)).strftime("%Y-%m-%d")
        data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if data.empty:
            return None
        # Find closest date
        date_str = date.strftime("%Y-%m-%d")
        if date_str in data.index.strftime("%Y-%m-%d"):
            return float(data.loc[data.index.strftime("%Y-%m-%d") == date_str]["Close"].iloc[0])
        # Fallback to nearest prior trading day
        for i in range(1, 5):
            fallback = (date - timedelta(days=i)).strftime("%Y-%m-%d")
            if fallback in data.index.strftime("%Y-%m-%d"):
                return float(data.loc[data.index.strftime("%Y-%m-%d") == fallback]["Close"].iloc[0])
        return None
    except Exception as e:
        print(f"Warning: Could not fetch price for {ticker} on {date}: {e}")
        return None


def fetch_week_prices(tickers: List[str], start_date: datetime, end_date: datetime) -> Dict[str, Dict[str, float]]:
    """Fetch daily prices for a list of tickers over a date range."""
    try:
        import yfinance as yf
        all_prices = {}
        for t in tickers:
            try:
                data = yf.download(
                    t,
                    start=(start_date - timedelta(days=2)).strftime("%Y-%m-%d"),
                    end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                    progress=False,
                    auto_adjust=True
                )
                if not data.empty:
                    all_prices[t] = {
                        idx.strftime("%Y-%m-%d"): float(row["Close"])
                        for idx, row in data.iterrows()
                    }
            except Exception as e:
                print(f"Warning: Could not fetch week data for {t}: {e}")
                all_prices[t] = {}
        return all_prices
    except ImportError:
        print("Warning: yfinance not available. Using placeholder prices.")
        return {t: {} for t in tickers}


# --- Report Parsing ---

def parse_report(report_path: Path) -> Dict:
    """Parse a weekly report markdown file and extract picks and market context."""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {
        "date": None,
        "vix": None,
        "spy_return": None,
        "picks": [],
        "fed_stance": None,
    }

    # Extract date
    date_match = re.search(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", content)
    if date_match:
        result["date"] = date_match.group(1)

    # Extract VIX
    vix_match = re.search(r"\*\*VIX:\*\*\s*([\d.]+)", content)
    if vix_match:
        result["vix"] = float(vix_match.group(1))

    # Extract SPY return
    spy_match = re.search(r"\*\*SPY Weekly Return:\*\*\s*([\-+\d.]+)%", content)
    if spy_match:
        result["spy_return"] = float(spy_match.group(1))

    # Extract Fed stance
    fed_match = re.search(r"\*\*Fed Stance:\*\*\s*(.+)", content)
    if fed_match:
        result["fed_stance"] = fed_match.group(1).strip()

    # Extract picks table
    picks_section = re.search(
        r"## Top 5 Portfolio Picks\n\|.*?\n\|.*?\n((?:\|.*?\n)+",
        content,
        re.DOTALL,
    )
    if picks_section:
        for line in picks_section.group(1).strip().split("\n"):
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]
            if len(parts) >= 3 and parts[0] not in ("Ticker", "---"):
                weight_str = parts[1].replace("%", "").strip()
                try:
                    weight = float(weight_str) / 100.0
                except ValueError:
                    weight = 0.0
                result["picks"].append({
                    "ticker": parts[0].upper(),
                    "weight": weight,
                    "sponsor": parts[2],
                })

    # Extract agent proposals for thesis/stop data
    # Look for individual pick lines in agent sections
    for agent in ["Cecil", "Marky", "Ophelia"]:
        agent_section = re.search(
            rf"### {agent}\s*\(.*?\)\n(.*?)(?=### |## |\Z)",
            content,
            re.DOTALL,
        )
        if agent_section:
            for pick in result["picks"]:
                if pick["sponsor"] == agent:
                    # Try to find thesis line for this ticker
                    ticker_pattern = rf"\*\*{pick['ticker']}\*\*\s*—\s*(.+?)(?:\n|$)"
                    thesis_match = re.search(ticker_pattern, agent_section.group(1), re.IGNORECASE)
                    if thesis_match:
                        pick["thesis"] = thesis_match.group(1).strip()

    return result


# --- Position Management ---

def open_positions(week_date_str: str, report_data: Dict) -> Dict:
    """Record new positions for the week."""
    # Fetch Monday prices for entry
    monday = datetime.strptime(week_date_str, "%Y-%m-%d")
    tickers = [p["ticker"] for p in report_data["picks"]]
    prices = {}
    for t in tickers:
        prices[t] = fetch_yf_price(t, monday)

    # Fetch SPY entry price
    spy_price = fetch_yf_price("SPY", monday)

    positions = []
    for pick in report_data["picks"]:
        entry_price = prices.get(pick["ticker"])
        positions.append({
            "ticker": pick["ticker"],
            "weight": pick["weight"],
            "sponsor": pick["sponsor"],
            "thesis": pick.get("thesis", ""),
            "entry_price": entry_price,
            "entry_date": week_date_str,
            "stop_loss": None,  # Will be set from journal if available
            "target": None,
            "direction": "long",
            "status": "open",
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
        })

    current = {
        "week": week_date_str,
        "status": "open",
        "positions": positions,
        "spy_entry": spy_price,
        "vix_at_entry": report_data.get("vix"),
        "fed_stance": report_data.get("fed_stance"),
        "total_weight": sum(p["weight"] for p in positions),
        "cash_weight": 1.0 - sum(p["weight"] for p in positions),
    }

    with open(CURRENT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(current, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return current


def close_positions(week_date_str: str) -> Optional[Dict]:
    """Close the current week's positions and calculate P&L."""
    if not CURRENT_PATH.exists():
        print("No current.yaml found. Nothing to close.")
        return None

    with open(CURRENT_PATH, "r", encoding="utf-8") as f:
        current = yaml.safe_load(f)

    if not current or current.get("status") != "open":
        print("No open positions to close.")
        return None

    # Friday is typically 4 days after Monday (or 5 for some)
    monday = datetime.strptime(current["week"], "%Y-%m-%d")
    friday = monday + timedelta(days=4)
    # If Friday is a weekend, go back to nearest trading day
    while friday.weekday() >= 5:
        friday -= timedelta(days=1)

    tickers = [p["ticker"] for p in current["positions"]]
    week_prices = fetch_week_prices(tickers, monday, friday)

    # Also fetch SPY exit price
    spy_exit = fetch_yf_price("SPY", friday)

    for pos in current["positions"]:
        t = pos["ticker"]
        entry = pos["entry_price"]

        # Check for stop loss during the week
        stop_hit = False
        stop_date = None
        if entry and pos.get("stop_loss"):
            for date_str, price in week_prices.get(t, {}).items():
                if price <= pos["stop_loss"]:
                    stop_hit = True
                    stop_date = date_str
                    pos["exit_price"] = price
                    pos["exit_date"] = date_str
                    pos["exit_reason"] = "stop_loss"
                    break

        if not stop_hit:
            # Use Friday close
            friday_str = friday.strftime("%Y-%m-%d")
            if friday_str in week_prices.get(t, {}):
                pos["exit_price"] = week_prices[t][friday_str]
                pos["exit_date"] = friday_str
                pos["exit_reason"] = "week_end"
            else:
                # Fallback to last available price in the week
                available = week_prices.get(t, {})
                if available:
                    last_date = max(available.keys())
                    pos["exit_price"] = available[last_date]
                    pos["exit_date"] = last_date
                    pos["exit_reason"] = "last_available"
                else:
                    pos["exit_price"] = entry
                    pos["exit_date"] = friday_str
                    pos["exit_reason"] = "no_data"

        # Calculate P&L
        if entry and pos["exit_price"]:
            pos["pnl_pct"] = round((pos["exit_price"] - entry) / entry * 100, 2)
        else:
            pos["pnl_pct"] = 0.0

        pos["status"] = "closed"

    # Calculate weighted portfolio return
    weighted_return = sum(p["weight"] * (p["pnl_pct"] or 0) for p in current["positions"])

    # Calculate SPY return for the week
    spy_entry = current.get("spy_entry")
    spy_return = None
    if spy_entry and spy_exit:
        spy_return = round((spy_exit - spy_entry) / spy_entry * 100, 2)

    # Calculate alpha
    alpha = None
    if spy_return is not None:
        alpha = round(weighted_return - spy_return, 2)

    current["status"] = "closed"
    current["weighted_return"] = round(weighted_return, 2)
    current["spy_return"] = spy_return
    current["alpha"] = alpha
    current["spy_exit"] = spy_exit
    current["close_date"] = friday.strftime("%Y-%m-%d")
    current["hit_rate"] = round(
        sum(1 for p in current["positions"] if (p["pnl_pct"] or 0) > 0) / len(current["positions"]), 2
        if current["positions"] else 0
    )

    # Archive to history
    history_file = HISTORY_DIR / f"{current['week']}.yaml"
    with open(history_file, "w", encoding="utf-8") as f:
        yaml.dump(current, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Clear current
    CURRENT_PATH.unlink()

    return current


# --- Metrics ---

def calculate_metrics() -> Dict:
    """Calculate rolling metrics from history."""
    history_files = sorted(HISTORY_DIR.glob("*.yaml"))
    if not history_files:
        return {}

    weeks = []
    for hf in history_files:
        with open(hf, "r", encoding="utf-8") as f:
            weeks.append(yaml.safe_load(f))

    returns = [w.get("weighted_return", 0) or 0 for w in weeks]
    spy_returns = [w.get("spy_return", 0) or 0 for w in weeks if w.get("spy_return") is not None]
    alphas = [w.get("alpha", 0) or 0 for w in weeks if w.get("alpha") is not None]

    # Hit rate (all-time)
    all_positions = []
    for w in weeks:
        all_positions.extend(w.get("positions", []))
    hit_rate = (
        sum(1 for p in all_positions if (p.get("pnl_pct") or 0) > 0) / len(all_positions)
        if all_positions else 0
    )

    # Sharpe ratio (assuming 4-week rolling, risk-free rate ~4.5%/52)
    rf_weekly = 4.5 / 52
    sharpe = None
    if len(returns) >= 4:
        recent = returns[-4:]
        avg = sum(recent) / len(recent)
        std = math.sqrt(sum((r - avg) ** 2 for r in recent) / len(recent)) if len(recent) > 1 else 0
        if std > 0:
            sharpe = round((avg - rf_weekly) / std * math.sqrt(52), 2)

    # Max drawdown
    cumulative = [1.0]
    for r in returns:
        cumulative.append(cumulative[-1] * (1 + r / 100))
    peak = cumulative[0]
    max_dd = 0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_dd:
            max_dd = dd

    # Per-agent metrics
    agent_pnl = {}
    for w in weeks:
        for p in w.get("positions", []):
            agent = p.get("sponsor", "Unknown")
            if agent not in agent_pnl:
                agent_pnl[agent] = {"returns": [], "hits": 0, "total": 0}
            agent_pnl[agent]["returns"].append(p.get("pnl_pct", 0) or 0)
            agent_pnl[agent]["total"] += 1
            if (p.get("pnl_pct") or 0) > 0:
                agent_pnl[agent]["hits"] += 1

    agent_summary = {}
    for agent, data in agent_pnl.items():
        agent_summary[agent] = {
            "avg_return": round(sum(data["returns"]) / len(data["returns"]), 2) if data["returns"] else 0,
            "hit_rate": round(data["hits"] / data["total"], 2) if data["total"] else 0,
            "total_picks": data["total"],
        }

    metrics = {
        "total_weeks": len(weeks),
        "avg_weekly_return": round(sum(returns) / len(returns), 2) if returns else 0,
        "avg_spy_return": round(sum(spy_returns) / len(spy_returns), 2) if spy_returns else 0,
        "avg_alpha": round(sum(alphas) / len(alphas), 2) if alphas else 0,
        "hit_rate": round(hit_rate, 2),
        "sharpe_4w": sharpe,
        "max_drawdown": round(max_dd * 100, 2),
        "agent_summary": agent_summary,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return metrics


# --- Markdown Generation ---

def generate_scorecard(week_data: Dict) -> str:
    """Generate a markdown scorecard for the week."""
    week = week_data["week"]
    positions = week_data.get("positions", [])

    lines = [
        f"# Scorecard — Week of {week}",
        "",
        f"**Council Grade:** {week_data.get('weighted_return', 0)}% | **SPY:** {week_data.get('spy_return', 'N/A')}% | **Alpha:** {week_data.get('alpha', 'N/A')}%",
        f"**Hit Rate:** {week_data.get('hit_rate', 0)} | **VIX at Entry:** {week_data.get('vix_at_entry', 'N/A')} | **Fed:** {week_data.get('fed_stance', 'N/A')}",
        "",
        "## Positions",
        "",
        "| Ticker | Weight | Sponsor | Entry | Exit | P&L % | Exit Reason |",
        "|--------|--------|---------|-------|------|-------|-------------|",
    ]

    for p in positions:
        entry = f"${p['entry_price']:.2f}" if p.get('entry_price') else "N/A"
        exit_p = f"${p['exit_price']:.2f}" if p.get('exit_price') else "N/A"
        pnl = f"{p['pnl_pct']:.2f}%" if p.get('pnl_pct') is not None else "N/A"
        lines.append(
            f"| {p['ticker']} | {p['weight']*100:.1f}% | {p['sponsor']} | {entry} | {exit_p} | {pnl} | {p.get('exit_reason', 'N/A')} |"
        )

    lines.extend([
        "",
        "## Per-Agent Breakdown",
        "",
    ])

    agent_stats = {}
    for p in positions:
        a = p["sponsor"]
        if a not in agent_stats:
            agent_stats[a] = {"return": 0, "weight": 0, "hits": 0, "total": 0}
        agent_stats[a]["return"] += (p.get("pnl_pct") or 0) * p["weight"]
        agent_stats[a]["weight"] += p["weight"]
        agent_stats[a]["total"] += 1
        if (p.get("pnl_pct") or 0) > 0:
            agent_stats[a]["hits"] += 1

    for agent, stats in agent_stats.items():
        hit_rate = stats["hits"] / stats["total"] if stats["total"] else 0
        lines.append(f"- **{agent}**: Weighted return = {stats['return']:.2f}%, Hit rate = {hit_rate:.0%}, Weight allocated = {stats['weight']*100:.1f}%")

    lines.extend([
        "",
        "---",
        f"*Generated by Paper Portfolio Tracker on {datetime.now().strftime('%Y-%m-%d')}*",
    ])

    return "\n".join(lines)


def update_scoreboard(week_data: Dict) -> str:
    """Append a row to the Historical Scoreboard table in scoreboard.md."""
    if not SCOREBOARD_PATH.exists():
        print("Warning: scoreboard.md not found. Skipping update.")
        return ""

    with open(SCOREBOARD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    week = week_data["week"]
    grade = week_data.get("weighted_return", 0)
    hit_rate = week_data.get("hit_rate", 0)

    # Find best and worst pick
    positions = week_data.get("positions", [])
    best = max(positions, key=lambda p: p.get("pnl_pct") or 0) if positions else None
    worst = min(positions, key=lambda p: p.get("pnl_pct") or 0) if positions else None

    best_str = f"{best['ticker']} ({best['pnl_pct']:.2f}%)" if best else "N/A"
    worst_str = f"{worst['ticker']} ({worst['pnl_pct']:.2f}%)" if worst else "N/A"

    lead = "TBD"  # Would need metrics to calculate
    flagged = "TBD"

    cash_pct = round(week_data.get("cash_weight", 0) * 100, 1)

    row = f"| {week} | {grade}% | {hit_rate:.0%} | {lead} | {flagged} | {best_str} | {worst_str} | {cash_pct}% |"

    # Find the table and append row
    table_pattern = r"(\| Week Ending \| Council Grade \| Hit Rate \| Lead Councilor \| Flagged Blindspot \| Best Pick \| Worst Pick \| Cash % \|)\n(\|.*?\|)"
    match = re.search(table_pattern, content)
    if match:
        # Insert after the header row (second match group is the separator)
        insert_after = match.end(2)
        content = content[:insert_after] + "\n" + row + content[insert_after:]

        with open(SCOREBOARD_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated scoreboard.md with week {week}.")
    else:
        print("Warning: Could not find Historical Scoreboard table in scoreboard.md.")

    return content


# --- Main Entry Points ---

def full_cycle(week_date_str: str, report_path: Optional[Path] = None):
    """Close previous week, then open new week."""
    # Step 1: Close previous week if open
    closed = close_positions(week_date_str)
    if closed:
        scorecard = generate_scorecard(closed)
        scorecard_path = SCORECARDS_DIR / f"{closed['week']}-scorecard.md"
        with open(scorecard_path, "w", encoding="utf-8") as f:
            f.write(scorecard)
        print(f"Scorecard written to {scorecard_path}")

        update_scoreboard(closed)
        calculate_metrics()

    # Step 2: Open new week
    if report_path is None:
        report_path = REPORTS_DIR / f"{week_date_str}-report.md"
    if not report_path.exists():
        print(f"Report not found: {report_path}. Cannot open new positions.")
        return

    report_data = parse_report(report_path)
    current = open_positions(week_date_str, report_data)
    print(f"Opened {len(current['positions'])} positions for week {week_date_str}.")
    print(f"  Cash weight: {current['cash_weight']*100:.1f}%")
    print(f"  SPY entry: ${current['spy_entry']:.2f}" if current['spy_entry'] else "  SPY entry: N/A")


def main():
    parser = argparse.ArgumentParser(description="Paper Portfolio Tracker")
    parser.add_argument("--open", metavar="DATE", help="Open positions for week DATE (YYYY-MM-DD)")
    parser.add_argument("--close", metavar="DATE", help="Close positions for week DATE (YYYY-MM-DD)")
    parser.add_argument("--full", metavar="DATE", help="Close prior week + open new week for DATE")
    parser.add_argument("--report", metavar="PATH", help="Path to report markdown file (optional)")
    parser.add_argument("--metrics", action="store_true", help="Recalculate metrics only")
    args = parser.parse_args()

    if args.metrics:
        calculate_metrics()
        print(f"Metrics updated: {METRICS_PATH}")
        return

    if args.close:
        closed = close_positions(args.close)
        if closed:
            scorecard = generate_scorecard(closed)
            scorecard_path = SCORECARDS_DIR / f"{closed['week']}-scorecard.md"
            with open(scorecard_path, "w", encoding="utf-8") as f:
                f.write(scorecard)
            update_scoreboard(closed)
            calculate_metrics()

    if args.open:
        report_path = Path(args.report) if args.report else REPORTS_DIR / f"{args.open}-report.md"
        if not report_path.exists():
            print(f"Report not found: {report_path}")
            sys.exit(1)
        report_data = parse_report(report_path)
        open_positions(args.open, report_data)

    if args.full:
        report_path = Path(args.report) if args.report else REPORTS_DIR / f"{args.full}-report.md"
        full_cycle(args.full, report_path)


if __name__ == "__main__":
    main()
