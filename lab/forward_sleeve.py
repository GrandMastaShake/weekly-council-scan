#!/usr/bin/env python3
"""Pass 29 -- the four-week earnings-drift sleeve, a forward record (registered in lab/README.md, 85714da).

Every Monday W: the candidates are S&P 500 names (the 2026-09-22 list) that reported in the previous Monday-to-Friday week and are tradeable;
the sleeve is active when there are at least 15; the picks are the five with the highest surprise percent, equal weight, bought at W's open and
sold at the close of the Friday of week W+3. One row per Monday goes into the append-only ledger (lab/sleeve_ledger.json) before any exit price
exists; closed cohorts are scored against the tradeable pool and the page lab/SLEEVE.md is rewritten from the ledger.

    python lab/forward_sleeve.py                 # log this Monday if it is not logged, then score
    python lab/forward_sleeve.py score           # rescore only
    python lab/forward_sleeve.py smoke           # plumbing: a past Monday into a scratch ledger
    python lab/forward_sleeve.py log --week 2026-10-12
"""
from __future__ import annotations

import argparse
import bisect
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402
import pass9_universe as p9  # noqa: E402
import pass15_exits as p15  # noqa: E402
import pass21_beat_fall as p21  # noqa: E402

REGISTERED = "85714da"
LEDGER = lab.LAB / "sleeve_ledger.json"
PAGE = lab.LAB / "SLEEVE.md"
DATA = lab.RESULTS / "sleeve.json"
EARN = lab.CACHE / "sleeve_earnings.json"
TOP = 5
MIN_ACTIVE = 15
CLIP = 0.40
SURPRISE_CLIP = 100.0
ROUND_TRIP = 0.0010
NW_LAGS = 3
CONFIRM_COHORTS, SEASONS_NEEDED, CONFIRM_EDGE, REJECT_T, MAX_COHORTS = 12, 3, 0.0020, -1.0, 24
OPEN_ET = (9, 30)


def monday_of(day):
    d = datetime.strptime(day, "%Y-%m-%d").date()
    return (d - timedelta(days=d.weekday())).isoformat()


def season_of(W):
    return f"{W[:4]}Q{(int(W[5:7]) - 1) // 3 + 1}"


def exit_friday(W):
    return lab._plus(W, 25)


def load_ledger(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"registered": REGISTERED, "universe": "lab/universe_sp500_2026-09-22.csv", "rows": []}


def write_json(path, doc):
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        json.dump(doc, fh, indent=1, default=float)
        fh.write("\n")


# ------------------------------------------------------------------------------------------------ data
def get_bars(names, start, end):
    tickers = sorted(set(names) | {"SPY"})
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, start)).items()}
    thin = [t for t in names if t in adj and len(adj[t].dates) < 40]
    missing = [t for t in tickers if t not in adj or not adj[t].dates]
    if "SPY" in missing or len(missing) > 0.05 * len(tickers):
        raise SystemExit(f"price download is incomplete ({len(missing)} of {len(tickers)} tickers empty); delete the cached file in lab/cache and rerun")
    return adj, missing, thin


def fetch_tables(names, max_age_hours=12):
    """{ticker: [[iso timestamp, estimate, reported, surprise%], ...]} from yfinance, refetched when the cache is older than max_age_hours."""
    if EARN.exists():
        age = (datetime.now().timestamp() - EARN.stat().st_mtime) / 3600
        cached = json.loads(EARN.read_text(encoding="utf-8"))
        if age < max_age_hours and all(t in cached for t in names):
            return cached, datetime.fromtimestamp(EARN.stat().st_mtime).astimezone().isoformat()
    import yfinance as yf

    def one(t):
        for _ in range(3):
            try:
                ed = yf.Ticker(t).get_earnings_dates(limit=24)
                if ed is not None and len(ed):
                    rows = []
                    for ts, r in ed.iterrows():
                        rep, est, sur = r.get("Reported EPS"), r.get("EPS Estimate"), r.get("Surprise(%)")
                        if rep == rep and est == est and sur == sur:
                            rows.append([ts.isoformat(), float(est), float(rep), float(sur)])
                    return t, sorted(rows)
            except Exception:
                pass
        return t, []
    out = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, (t, rows) in enumerate(pool.map(one, names)):
            out[t] = rows
            if (i + 1) % 100 == 0:
                print(f"  fetched {i + 1}/{len(names)} earnings tables", flush=True)
    if sum(1 for v in out.values() if v) < 0.8 * len(names):
        raise SystemExit("fewer than 80% of the earnings tables came back; not logging on a half-empty table")
    lab.CACHE.mkdir(parents=True, exist_ok=True)
    EARN.write_text(json.dumps(out), encoding="utf-8")
    return out, datetime.now().astimezone().isoformat()


# ------------------------------------------------------------------------------------------------ choosing the cohort
def sleeve_pool(names, adj, cal, W):
    """The Council's tradeable pool (enough history, no report inside the coming week) with one correction. p10.pool looks for the first report
    ON OR AFTER the previous Friday, so a name that reported on that Friday reads as reporting in 0 days and is blacked out, which removes the
    Friday pre-market reporters the sleeve is built from. Here the first report must be strictly after that Friday (lab/README.md, Pass 29 erratum)."""
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    from scan_pipeline.utils.data_utils import EARNINGS_BLACKOUT_TRADING_DAYS
    short = {t: _aggregate_weekly(adj[t].before(W, lab.LOOKBACK_DAYS)) for t in names if t in adj}
    eligible = [t for t in names if len(short.get(t, [])) >= lab.MIN_WEEKS]
    F = _aggregate_weekly(adj["SPY"].before(W, lab.LOOKBACK_DAYS))[-1].date
    out = []
    for t in eligible:
        nxt = lab._next_report(cal.get(t), lab._plus(F, 1))
        etd = _business_days_between(F, nxt) if nxt else None
        if etd is None or not 0 <= etd <= EARNINGS_BLACKOUT_TRADING_DAYS:
            out.append(t)
    return out


def candidates_for(W, names, tables, adj, tradeable):
    lo, hi = lab._plus(W, -7), lab._plus(W, -3)
    out = {}
    for t in names:
        if t not in tradeable or t not in adj:
            continue
        dates = adj[t].dates
        for ts, est, rep, sur in tables.get(t, []):
            if not (lab._plus(W, -8) <= ts[:10] <= lab._plus(W, -2)):
                continue
            i = p21.reaction_index(dates, ts)
            if i >= len(dates):
                continue
            react = dates[i]
            if not (lo <= react <= hi):
                continue
            s = max(-SURPRISE_CLIP, min(SURPRISE_CLIP, sur))
            cur = out.get(t)
            if cur is None or (-s, t) < (-cur["surprise"], t):
                out[t] = {"t": t, "surprise": s, "ts": ts, "react": react}
    return sorted(out.values(), key=lambda c: (-c["surprise"], c["t"]))


def log_week(W, names, ledger, path, now, allow_past=False):
    if any(r["W"] == W for r in ledger["rows"]):
        print(f"  {W} is already in the ledger; nothing to log")
        return None
    if not allow_past and now.date() > datetime.strptime(W, "%Y-%m-%d").date() + timedelta(days=4):
        print(f"  {W} closed before this run: it stays a gap in the ledger")
        return None
    late = now.date() > datetime.strptime(W, "%Y-%m-%d").date() or (now.hour, now.minute) >= OPEN_ET
    tables, fetched_at = fetch_tables(names)
    cal = lab.earnings_calendar(names, max_age_days=6)
    start = lab._plus(W, -200)
    adj, missing, thin = get_bars(names, start, lab._plus(W, 1))
    tradeable = set(sleeve_pool(names, adj, cal, W))
    cands = candidates_for(W, names, tables, adj, tradeable)
    active = len(cands) >= MIN_ACTIVE
    sectors = p9.sp500()
    row = {"W": W, "logged_at": now.isoformat(), "late": bool(late), "active": bool(active), "n_candidates": len(cands),
           "n_tradeable": len(tradeable), "min_active": MIN_ACTIVE, "earnings_tables_fetched_at": fetched_at,
           "picks": [dict(c, sector=sectors.get(c["t"], "?")) for c in cands[:TOP]] if active else [],
           "candidates": [{"t": c["t"], "surprise": c["surprise"]} for c in cands],
           "pool": sorted(tradeable), "empty_price_tickers": missing}
    ledger["rows"].append(row)
    ledger["rows"].sort(key=lambda r: r["W"])
    write_json(path, ledger)
    print(f"  logged {W}: {len(cands)} candidates, {len(tradeable)} tradeable, {'ACTIVE' if active else 'inactive'}{' (late)' if late else ''}")
    if active:
        for c in row["picks"]:
            print(f"    {c['t']:<6}{c['surprise']:+7.1f}%  reported {c['ts'][:16]}  reacts {c['react']}  ({c['sector']})")
    return row


# ------------------------------------------------------------------------------------------------ scoring
def hold_to(s, W, end):
    """Open of W's first session to the last close on or before `end`; None if the series is empty there or stops more than four days short."""
    lo, hi = bisect.bisect_left(s.dates, W), bisect.bisect_right(s.dates, end)
    if lo >= hi or s.dates[hi - 1] < lab._plus(end, -4):
        return None
    return s.rows[hi - 1]["close"] / s.rows[lo]["open"] - 1.0


def clipped_hold(adj, t, W, end):
    s = adj.get(t)
    r = hold_to(s, W, end) if s else None
    return None if r is None else max(-CLIP, min(CLIP, r))


def score_rows(ledger, adj, latest):
    out = []
    for r in ledger["rows"]:
        W = r["W"]
        ex = exit_friday(W)
        base = {"W": W, "season": season_of(W), "active": r["active"], "late": r["late"], "n_candidates": r["n_candidates"],
                "picks": [p["t"] for p in r["picks"]], "surprises": [p["surprise"] for p in r["picks"]]}
        if not r["active"]:
            out.append(dict(base, status="inactive"))
            continue
        closed = latest >= ex
        end = min(ex, latest)
        pool = {t: clipped_hold(adj, t, W, end) for t in r["pool"]}
        pool = {t: x for t, x in pool.items() if x is not None}
        cand = {c["t"]: pool.get(c["t"]) for c in r["candidates"]}
        cand = {t: x for t, x in cand.items() if x is not None}
        pick = {p["t"]: clipped_hold(adj, p["t"], W, end) for p in r["picks"]}
        have = {t: x for t, x in pick.items() if x is not None}
        spy = hold_to(adj["SPY"], W, end)
        if len(have) < TOP or len(pool) < 30 or spy is None:
            out.append(dict(base, status="closed" if closed else "open", unscored="missing prices: " + ", ".join(sorted(set(pick) - set(have)))))
            continue
        pm, bm = statistics.fmean(have.values()), statistics.fmean(pool.values())
        edge = pm - bm
        row = dict(base, status="closed" if closed else "open", exit=ex, pick_return=pm, pool_return=bm, spy_return=spy,
                   edge=edge, edge_per_week=edge / 4.0, edge_per_week_net=edge / 4.0 - ROUND_TRIP / 4.0,
                   vs_spy=pm - spy, vs_candidates=(pm - statistics.fmean(cand.values())) / 4.0 if cand else None,
                   pick_returns=have)
        out.append(row)
    return out


def verdict(closed):
    vals = [c["edge_per_week"] for c in closed]
    n = len(vals)
    seasons = sorted({c["season"] for c in closed})
    by_season = {s: statistics.fmean(c["edge_per_week"] for c in closed if c["season"] == s) for s in seasons}
    t = p15.nw_t(vals, NW_LAGS) if n >= 3 else None
    mean = statistics.fmean(vals) if vals else None
    out = {"closed": n, "seasons": seasons, "mean_edge_per_week": mean, "nw_t": t, "by_season": by_season,
           "hit_share": (sum(1 for v in vals if v > 0) / n) if n else None}
    if n >= CONFIRM_COHORTS and len(seasons) >= SEASONS_NEEDED and mean >= CONFIRM_EDGE and t is not None and t >= 2 \
            and sum(1 for v in by_season.values() if v > 0) >= 2:
        out["status"] = "CONFIRMED"
    elif (n >= CONFIRM_COHORTS and mean <= 0) or (n >= 8 and t is not None and t <= REJECT_T):
        out["status"] = "REJECTED"
    elif n >= MAX_COHORTS:
        out["status"] = "FINAL: not confirmed"
    elif n < 8:
        out["status"] = f"too early ({n} closed cohorts; 12 across three seasons are needed)"
    else:
        out["status"] = f"keep running ({n} closed cohorts, {len(seasons)} season{'s' if len(seasons) != 1 else ''})"
    return out


def pct(x, d=2):
    return "--" if x is None else f"{x * 100:+.{d}f}%"


def write_page(rows, v, generated, ledger, latest):
    lines = ["# Four-week earnings-drift sleeve: forward record", "",
             "Registered 2026-10-12 as Pass 29 (`lab/README.md`, " + REGISTERED + "). A paper ledger, not a Council member. Every Monday the routine runs, the five "
             "highest-surprise names among last week's S&P 500 reporters are bought at the open and held to the Friday of week W+3, if at least 15 candidates exist. "
             "`lab/forward_sleeve.py` rewrites this page from `lab/sleeve_ledger.json` (append-only) and the bars; edits by hand are overwritten.", "",
             f"Last run: {generated}. Latest bar: {latest}. Mondays logged: {len(ledger['rows'])}; active: {sum(1 for r in ledger['rows'] if r['active'])}.", "",
             f"**Status: {v['status']}.** Closed cohorts: {v['closed']}"
             + (f"; mean edge over the tradeable pool {pct(v['mean_edge_per_week'])} a week of holding"
                + (f" (Newey-West t {v['nw_t']:+.2f})" if v['nw_t'] is not None and v['closed'] >= 8 else "")
                + f"; ahead in {v['hit_share']:.0%} of cohorts" if v["closed"] else "") + ".", ""]
    if v["by_season"]:
        lines.append("By season: " + "; ".join(f"{s} {pct(x)}" for s, x in v["by_season"].items()) + ".")
        lines.append("")
    lines += ["| Monday | Status | Candidates | Picks (surprise %) | Exit Friday | Four-week return | Pool | SPY | Edge / wk of holding | After 0.10% round trip | Over candidates, /wk |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        picks = ", ".join(f"{t} ({s:+.0f})" for t, s in zip(r["picks"], r["surprises"])) or "--"
        flag = " late" if r["late"] else ""
        if "edge" in r:
            lines.append(f"| {r['W']}{flag} | {r['status']} | {r['n_candidates']} | {picks} | {r['exit']} | {pct(r['pick_return'])} | {pct(r['pool_return'])} | {pct(r['spy_return'])} | "
                         f"{pct(r['edge_per_week'])} | {pct(r['edge_per_week_net'])} | {pct(r['vs_candidates'])} |")
        else:
            lines.append(f"| {r['W']}{flag} | {r.get('unscored') and 'unscored' or r['status']} | {r['n_candidates']} | {picks} | | | | | | | |")
    lines += ["", "Open cohorts are marked to the latest close and do not count toward the status. Rule: confirmed at 12 or more closed cohorts across three seasons "
              "with a mean edge of at least +0.20% a week of holding, a Newey-West t of 2 or more and a positive mean in two seasons; rejected at 12 or more with a mean "
              "of 0 or below, or at 8 or more with t of -1 or lower; otherwise it keeps running, to 24 cohorts. Pass 23's backtest, for reference: +0.404% a week of holding "
              "over 34 active weeks (t 3.02)."]
    PAGE.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def score(ledger_path, names):
    ledger = load_ledger(ledger_path)
    if not ledger["rows"]:
        print("  the ledger is empty")
        return None
    start = lab._plus(min(r["W"] for r in ledger["rows"]), -10)
    end = lab._plus(datetime.now().astimezone().date().isoformat(), 1)
    pools = {t for r in ledger["rows"] if r["active"] for t in r["pool"]}      # inactive Mondays need no prices
    adj, _, _ = get_bars(sorted(pools | {"SPY"}), start, end)
    latest = adj["SPY"].dates[-1]
    rows = score_rows(ledger, adj, latest)
    closed = [r for r in rows if r.get("status") == "closed" and "edge" in r]
    v = verdict(closed)
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    if ledger_path == LEDGER:
        write_page(rows, v, generated, ledger, latest)
        write_json(DATA, {"registered": REGISTERED, "generated": generated, "latest_bar": latest, "verdict": v, "cohorts": rows})
        print(f"  wrote {PAGE.name} and {DATA.name}")
    print(f"  status: {v['status']}")
    for r in rows:
        if "edge" in r:
            print(f"    {r['W']} {r['status']:<6} picks {','.join(r['picks'])}  four-week {pct(r['pick_return'])} vs pool {pct(r['pool_return'])}  edge/wk {pct(r['edge_per_week'])}")
        else:
            print(f"    {r['W']} {r['status']} ({r['n_candidates']} candidates)")
    return v


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="run", choices=["run", "log", "score", "smoke"])
    ap.add_argument("--week")
    args = ap.parse_args(argv)
    names = sorted(p9.sp500())
    now = datetime.now().astimezone()
    if args.mode == "smoke":
        path, week = lab.CACHE / "sleeve_ledger.smoke.json", args.week or "2026-07-27"
        if path.exists():
            path.unlink()
        ledger = load_ledger(path)
        log_week(week, names, ledger, path, now, allow_past=True)
        score(path, names)
        return
    if args.mode in ("run", "log"):
        W = args.week or monday_of(now.date().isoformat())
        ledger = load_ledger(LEDGER)
        log_week(W, names, ledger, LEDGER, now)
    if args.mode in ("run", "score"):
        score(LEDGER, names)


if __name__ == "__main__":
    main()
