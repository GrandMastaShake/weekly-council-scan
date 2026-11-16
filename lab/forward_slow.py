#!/usr/bin/env python3
"""Pass 35 -- the slow book: Cecil's engine picks held four weeks, a forward record.

Every Monday W the routine logs the Cecil-solo engine's proposals on the
frozen S&P 500 list (point-in-time P/E, the engine's own earnings blackout),
equal weight, bought at W's open and sold at the close of the Friday of W+3.
No stop, no exit rule, no cash. Cohorts overlap; each is scored on its own
against the whole tradeable pool held the same way, as the Pass 29 sleeve is.
The ledger (lab/slow_ledger.json) is append-only.

Registered in lab/README.md (Pass 35) before its first cohort.

    python lab/forward_slow.py          # log this Monday if it is not logged, score, rewrite SLOW.md
    python lab/forward_slow.py score    # rescore only
    python lab/forward_slow.py smoke P  # plumbing: log to a scratch ledger at path P, write no page
"""
from __future__ import annotations

import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import forward_sleeve as fs  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass15_exits as p15  # noqa: E402

LEDGER = lab.LAB / "slow_ledger.json"
PAGE = lab.LAB / "SLOW.md"
DATA = lab.RESULTS / "slow.json"
HOLD_WEEKS = 4
CONFIRM_EDGE = 0.0015
CONFIRM_COHORTS, MAX_COHORTS, SEASONS_NEEDED, REJECT_T = 12, 24, 3, -1.0
ROUND_TRIP = 0.0010


def cecil_picks(W, names):
    """The Cecil-solo engine's book for week W on `names`, from data before W."""
    import council_room_v2 as v2
    import pass11_cecil_themes as p11
    cal = lab.earnings_calendar(names, max_age_days=6)
    v2.eps_history(sorted(names), max_age_days=6)
    rows = lab.run(verbose=False, knobs={"solo": "Cecil", "pe_builder": p11.pe_builder},
                   weeks=[(W, W, None)], start=lab._plus(W, -100), earnings=cal, names=names)
    return [b["ticker"] for b in rows[0]["book"]], cal


def log_week(W, names, ledger, path, now):
    if any(r["W"] == W for r in ledger["rows"]):
        print(f"  {W} is already in the ledger; nothing to log")
        return
    if now.date().isoformat() > lab._plus(W, 4):
        print(f"  {W} closed before this run: it stays a gap in the ledger")
        return
    late = now.date().isoformat() > W or (now.hour, now.minute) >= fs.OPEN_ET
    picks, cal = cecil_picks(W, names)
    adj, missing, _ = fs.get_bars(names, lab._plus(W, -200), lab._plus(W, 1))
    tradeable = sorted(fs.sleeve_pool(names, adj, cal, W))
    sectors = p9.sp500()
    ledger["rows"].append({"W": W, "logged_at": now.isoformat(), "late": bool(late),
                           "picks": [{"t": t, "sector": sectors.get(t, "?")} for t in picks],
                           "n_tradeable": len(tradeable), "pool": tradeable, "empty_price_tickers": missing})
    ledger["rows"].sort(key=lambda r: r["W"])
    fs.write_json(path, ledger)
    print(f"  logged {W}: {', '.join(picks)} ({len(tradeable)} tradeable){' (late)' if late else ''}")


def score_rows(ledger, adj, latest):
    out = []
    for r in ledger["rows"]:
        W, ex = r["W"], fs.exit_friday(r["W"])
        closed = latest >= ex
        end = min(ex, latest)
        base = {"W": W, "season": fs.season_of(W), "late": r["late"], "picks": [p["t"] for p in r["picks"]],
                "status": "closed" if closed else "open", "exit": ex}
        pool = {t: fs.clipped_hold(adj, t, W, end) for t in r["pool"]}
        pool = {t: x for t, x in pool.items() if x is not None}
        pick = {t: fs.clipped_hold(adj, t, W, end) for t in base["picks"]}
        have = {t: x for t, x in pick.items() if x is not None}
        spy = fs.hold_to(adj["SPY"], W, end)
        if not base["picks"] or len(have) < len(base["picks"]) or len(pool) < 30 or spy is None:
            out.append(dict(base, unscored="no picks" if not base["picks"] else "missing prices or the week has not started"))
            continue
        pm, bm = statistics.fmean(have.values()), statistics.fmean(pool.values())
        wk1_end = min(lab._plus(W, 4), latest)
        one = [fs.clipped_hold(adj, t, W, wk1_end) for t in base["picks"]]
        pool1 = [x for x in (fs.clipped_hold(adj, t, W, wk1_end) for t in r["pool"]) if x is not None]
        out.append(dict(base, pick_return=pm, pool_return=bm, spy_return=spy, edge=pm - bm,
                        edge_per_week=(pm - bm) / HOLD_WEEKS, edge_per_week_net=(pm - bm - ROUND_TRIP) / HOLD_WEEKS,
                        vs_spy=pm - spy, pick_returns=have,
                        first_week_edge=(statistics.fmean(one) - statistics.fmean(pool1)) if all(x is not None for x in one) and pool1 else None))
    return out


def verdict(closed):
    vals = [c["edge_per_week"] for c in closed]
    n = len(vals)
    seasons = sorted({c["season"] for c in closed})
    by = {s: statistics.fmean(c["edge_per_week"] for c in closed if c["season"] == s) for s in seasons}
    t = p15.nw_t(vals, 3) if n >= 3 else None
    mean = statistics.fmean(vals) if vals else None
    out = {"closed": n, "seasons": seasons, "mean_edge_per_week": mean, "nw_t": t, "by_season": by}
    if n >= CONFIRM_COHORTS and len(seasons) >= SEASONS_NEEDED and mean >= CONFIRM_EDGE and t is not None and t >= 2 \
            and sum(1 for v in by.values() if v > 0) >= 2:
        out["status"] = "CONFIRMED"
    elif (n >= CONFIRM_COHORTS and mean <= 0) or (n >= 8 and t is not None and t <= REJECT_T):
        out["status"] = "REJECTED"
    elif n >= MAX_COHORTS:
        out["status"] = "FINAL: not confirmed"
    elif n < 8:
        out["status"] = f"too early ({n} closed cohorts; 12 across three quarters are needed)"
    else:
        out["status"] = f"keep running ({n} closed cohorts, {len(seasons)} quarter{'s' if len(seasons) != 1 else ''})"
    return out


def write_page(rows, v, generated, latest):
    P = lambda x, d=2: "--" if x is None else f"{100 * x:+.{d}f}%"  # noqa: E731
    tt = "" if v["nw_t"] is None else " (Newey-West t {:+.2f})".format(v["nw_t"])
    out = ["# The slow book", "",
           "Cecil's engine picks on the frozen S&P 500 list, equal weight, bought Monday and held four weeks; no stop,",
           "no exits (Pass 35). `lab/forward_slow.py` regenerates this page each Monday from `lab/slow_ledger.json`,",
           "which is append-only; edits by hand are overwritten.", "",
           f"Last run: {generated}. Prices through {latest}.", "",
           f"**Status: {v['status']}.** Closed cohorts: {v['closed']}. Mean edge per week of holding: {P(v['mean_edge_per_week'], 3)}{tt}.", "",
           "Confirmed needs 12 closed cohorts in three quarters, a mean edge of +0.15% a week of holding, t of 2 and two positive",
           "quarters; rejected at zero or below with 12, or t at -1 or lower with 8. Before that this page shows direction, not proof.", "",
           "| Monday | Picks | Status | Exit | Picks | Pool | SPY | Edge / wk | First week's edge |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "unscored" in r:
            out.append(f"| {r['W']}{' (late)' if r['late'] else ''} | {', '.join(r['picks']) or '--'} | {r['status']} | {r['exit']} | {r['unscored']} | | | | |")
        else:
            out.append(f"| {r['W']}{' (late)' if r['late'] else ''} | {', '.join(r['picks'])} | {r['status']} | {r['exit']} | {P(r['pick_return'])} | "
                       f"{P(r['pool_return'])} | {P(r['spy_return'])} | {P(r['edge_per_week'], 3)} | {P(r['first_week_edge'])} |")
    out += ["", "Open cohorts are marked to the latest close. \"Late\" means the row was logged after that Monday's open, which is how this",
            "job runs; the picks use only data from before the Monday."]
    return "\n".join(out) + "\n"


def main(argv):
    mode = argv[1] if len(argv) > 1 else "run"
    names = sorted(p9.sp500())
    path = Path(argv[2]) if mode == "smoke" else LEDGER
    ledger = fs.load_ledger(path) if path.exists() else {"registered": "lab/README.md, Pass 35", "universe": "lab/universe_sp500_2026-09-22.csv", "rows": []}
    now = datetime.now().astimezone()
    if mode in ("run", "smoke"):
        log_week(fs.monday_of(now.date().isoformat()), names, ledger, path, now)
    if not ledger["rows"]:
        print("  no rows yet")
        return 0
    first = ledger["rows"][0]["W"]
    adj, _, _ = fs.get_bars(names, lab._plus(first, -10), lab._plus(now.date().isoformat(), 1))
    latest = adj["SPY"].dates[-1]
    rows = score_rows(ledger, adj, latest)
    v = verdict([r for r in rows if r["status"] == "closed" and "edge_per_week" in r])
    text = write_page(rows, v, now.strftime("%Y-%m-%d %H:%M"), latest)
    print(text)
    if mode != "smoke":
        with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        fs.write_json(DATA, {"generated": now.isoformat(), "latest": latest, "verdict": v, "rows": rows})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
