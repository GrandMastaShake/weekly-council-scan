#!/usr/bin/env python3
"""Council Room v2 -- Ophelia's three passes and Cecil's reading pass.

The design is lab/council_v2.md. For each Council week this builds exactly what
each pass may see, from the repo as it stood just before that Monday's Council
report, and nothing more:

  ophelia/pass1/brief.md          the README Market Brief (the top of
                                  wiki/synthesis.md the one week the README
                                  had none)
  ophelia/pass2/canary-watch.md, economic-calendar.md,
                sectors/<sector>.md
                                  a light read of every sector wiki: its ETF
                                  snapshot, weekly narrative and council read
  ophelia/pass3/sheet.csv         written after pass 2: the 40 stocks of her
                                  four sectors plus BTC and GLD, point-in-time,
                                  with the four full sector wikis beside it
  cecil/synthesis.md, value.csv   the full synthesis, and his value table for
                                  the 111's stocks

Cecil's table is rebuilt from what can be dated. Trailing P/E uses the reported
EPS of the four quarters before that Monday, EPS growth compares that with the
four quarters before them, and safety comes from prices. Quality (dividends,
leverage, cash flow) stays out rather than being filled with today's numbers.

Scoring: each member's five, equal-weighted, Monday open -> Friday close,
against random fives drawn from the same 111's tradeable names. Marky's five
come from Pass 5 (results/pass5_marky.json), the channel mode.

    python lab/council_room_v2.py build DIR
    python lab/council_room_v2.py pass3 DIR     # after pass 2: each week's sheet
    python lab/council_room_v2.py score DIR
    python lab/council_room_v2.py debate DIR    # the members' logs, for the synthesis agent
    python lab/council_room_v2.py approve DIR   # after the draft: each member's approval folder
    python lab/council_room_v2.py final DIR     # after the votes: the rule, then the scores
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_room as room  # noqa: E402
import engine_lab as lab  # noqa: E402

COUNCIL_START = "2025-06-01"          # shares Pass 4's download
EPS_CACHE = lab.CACHE / "earnings_eps.json"
TOP = 5
SECTOR_WIKIS = {
    "Communication Services": ["communication-services.md"],
    "Consumer Discretionary": ["consumer-discretionary.md"],
    "Consumer Staples": ["consumer-staples.md"],
    "Energy": ["energy.md"],
    "Financials": ["financials.md"],
    "Healthcare": ["healthcare.md"],
    "Industrials": ["industrials.md"],
    "Materials": ["materials.md"],
    "Real Estate": ["real-estate.md"],
    "Technology": ["tech.md", "semiconductors.md"],
}
LIGHT = re.compile(r"SNAPSHOT|WEEKLY NARRATIVE|COUNCIL READ", re.I)


def _watchlist():
    from scan_pipeline.config.tickers import COUNCIL_WATCHLIST_ROWS
    return {r["Ticker"]: r for r in COUNCIL_WATCHLIST_ROWS}


def _sections(md, keep):
    """The '## ' sections of a wiki whose titles match keep, in order."""
    parts = re.split(r"(?m)^(?=## )", md)
    return "".join([parts[0]] + [p for p in parts[1:] if keep.search(p.splitlines()[0])])


def market_brief(readme, synthesis):
    m = re.search(r"(?ms)^## [^\n]*Market Brief[^\n]*\n.*?(?=^## )", readme)
    if m:
        return m.group(0)
    head = re.split(r"(?m)^(?=## )", synthesis)
    return "".join(head[:4])        # no brief that week: the synthesis's opening sections


def eps_history(tickers):
    """{ticker: [(report date, reported EPS)]} from yfinance, cached and merged."""
    cached = {}
    if EPS_CACHE.exists():
        with open(EPS_CACHE, encoding="utf-8") as fh:
            cached = json.load(fh)
    todo = [t for t in tickers if t not in cached]
    if todo:
        from concurrent.futures import ThreadPoolExecutor
        import yfinance as yf

        def one(t):
            for _ in range(3):
                try:
                    df = yf.Ticker(t).get_earnings_dates(limit=24)
                    if df is not None and len(df) and "Reported EPS" in df.columns:
                        rows = [(ix.strftime("%Y-%m-%d"), float(v)) for ix, v in df["Reported EPS"].items()
                                if v == v]
                        return t, sorted(rows)
                except Exception:
                    pass
            return t, []
        with ThreadPoolExecutor(max_workers=6) as pool:
            cached.update(dict(pool.map(one, todo)))
        lab.CACHE.mkdir(parents=True, exist_ok=True)
        with open(EPS_CACHE, "w", encoding="ascii", newline="\n") as fh:
            json.dump(cached, fh, indent=0, sort_keys=True)
    return cached


def _ttm(rows, before, skip=0):
    past = [e for d, e in rows if d < before]
    if len(past) < 4 + skip:
        return None
    return sum(past[len(past) - 4 - skip:len(past) - skip])


def _data():
    from scan_pipeline.config.tickers import COUNCIL_WATCHLIST
    today = date.today()
    last_friday = today - timedelta(days=(today.weekday() - 4) % 7 or 7)
    weeks = lab.council_weeks(last_friday.strftime("%Y-%m-%d"))
    names = list(COUNCIL_WATCHLIST)
    end = lab._plus(weeks[-1][1], 5)
    tickers = sorted(set(names)) + lab.EXTRA
    raw = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, False, end, COUNCIL_START)).items()}
    adj = {t: lab.Series(r) for t, r in lab.bars_by_ticker(lab.download(tickers, True, end, COUNCIL_START)).items()}
    return weeks, names, raw, adj


def _sheet(names, raw, adj, W, wl, cal, eps):
    """Point-in-time facts for each name, ending at the last close before W."""
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    rows = []
    for t in names:
        if t not in raw:
            continue
        wk = _aggregate_weekly(adj[t].before(W, 400)) if t in adj else []
        wr = _aggregate_weekly(raw[t].before(W, 400))
        if len(wk) < lab.MIN_WEEKS:
            continue
        closes = [h.close for h in wk]
        last, F = wr[-1].close, wr[-1].date

        def back(n):
            return round((closes[-1] / closes[-1 - n] - 1) * 100, 2) if len(closes) > n else None
        yr = closes[-52:]
        rets = [closes[i] / closes[i - 1] - 1 for i in range(max(1, len(closes) - 12), len(closes))]
        nxt = lab._next_report(cal.get(t), F)
        etd = _business_days_between(F, nxt) if nxt else None
        info = wl[t]
        cap_now = float(info["MarketCapUSDm"]) if info["MarketCapUSDm"] else None
        ttm, ttm_prev = _ttm(eps.get(t, []), W), _ttm(eps.get(t, []), W, skip=4)
        rows.append({
            "ticker": t, "company": info["Company"], "sector": info["Sector"], "industry": info["Industry"],
            "close": round(last, 2),
            "ret_1w_pct": back(1), "ret_4w_pct": back(4), "ret_12w_pct": back(12),
            "pct_of_52w_high": round(closes[-1] / max(yr) * 100, 1) if len(yr) >= 40 else None,
            "weekly_vol_12w_pct": round(statistics.pstdev(rets) * 100, 2) if len(rets) >= 3 else None,
            "pe_ttm": (round(last / ttm, 1) if ttm and ttm > 0 else ("loss" if ttm is not None else None)),
            "eps_growth_pct": (round((ttm - ttm_prev) / abs(ttm_prev) * 100, 1)
                               if ttm is not None and ttm_prev not in (None, 0) else None),
            "cap_usd_bn_approx": (round(cap_now * last / float(info.get("_px_now") or last) / 1000, 1)
                                  if cap_now else None),
            "next_earnings": nxt, "reports_this_week": etd is not None and 0 <= etd <= 5,
        })
    return rows


def _write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def build(out_dir):
    weeks, names, raw, adj = _data()
    wl = _watchlist()
    px_now = {t: (raw[t].rows[-1]["close"] if t in raw and raw[t].rows else None) for t in names}
    for t in wl:
        wl[t]["_px_now"] = px_now.get(t)
    cal = lab.earnings_calendar(names)
    eps = eps_history([t for t in names if wl[t]["Sector"] != "Macro Assets"])
    out_dir = Path(out_dir)
    manifest = []
    for label, W, _ in weeks:
        commit = room.snapshot_commit(label)
        show = lambda p: room._git("show", f"{commit}:{p}").decode("utf-8", "replace").replace("\r\n", "\n")
        d = out_dir / label
        (d / "ophelia/pass1").mkdir(parents=True, exist_ok=True)
        (d / "ophelia/pass2/sectors").mkdir(parents=True, exist_ok=True)
        (d / "ophelia/pass3").mkdir(parents=True, exist_ok=True)
        (d / "cecil").mkdir(parents=True, exist_ok=True)
        synthesis = show("wiki/synthesis.md")

        def put(path, text):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        put(d / "ophelia/pass1/brief.md", market_brief(show("README.md"), synthesis))
        put(d / "ophelia/pass2/canary-watch.md", show("wiki/canary-watch.md"))
        put(d / "ophelia/pass2/economic-calendar.md", show("wiki/economic-calendar.md"))
        for sector, files in SECTOR_WIKIS.items():
            slug = sector.lower().replace(" ", "-")
            put(d / f"ophelia/pass2/sectors/{slug}.md",
                "\n\n".join(_sections(show(f"wiki/{f}"), LIGHT) for f in files))
            for f in files:
                put(d / f"ophelia/pass3/{f}", show(f"wiki/{f}"))
        put(d / "cecil/synthesis.md", synthesis)
        sheet = _sheet(names, raw, adj, W, wl, cal, eps)
        _write_csv(d / "sheet_all.csv", sheet, list(sheet[0]))
        value = [r for r in sheet if r["sector"] != "Macro Assets"]
        _write_csv(d / "cecil/value.csv", value,
                   ["ticker", "company", "sector", "industry", "close", "pe_ttm", "eps_growth_pct",
                    "weekly_vol_12w_pct", "ret_12w_pct", "cap_usd_bn_approx", "next_earnings",
                    "reports_this_week"])
        manifest.append({"label": label, "monday": W, "commit": commit, "names": len(sheet),
                         "brief_from": "README" if "Market Brief" in (d / "ophelia/pass1/brief.md").read_text(
                             encoding="utf-8").split("\n", 1)[0] else "synthesis"})
        print(f"  {label}  {commit[:7]}  {len(sheet)} names  brief from {manifest[-1]['brief_from']}")
    with open(out_dir / "manifest.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")


def pass3(out_dir):
    """After pass 2: each week's sheet holds her four sectors' stocks plus BTC and GLD."""
    for d in sorted(p for p in Path(out_dir).iterdir() if p.is_dir()):
        p2 = d / "ophelia/pass2/result.json"
        if not p2.exists():
            print(f"  {d.name}: no pass-2 result yet")
            continue
        doc = json.loads(p2.read_text(encoding="utf-8"))
        final = doc["final4"]
        sectors = {x["sector"] if isinstance(x, dict) else x for x in final}
        with open(d / "ophelia/pass3/my_sectors.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"final4": final, "changes": doc.get("changes")}, fh, indent=1)
            fh.write("\n")
        with open(d / "sheet_all.csv", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        keep = [r for r in rows if r["sector"] in sectors or r["sector"] == "Macro Assets"]
        _write_csv(d / "ophelia/pass3/sheet.csv", keep,
                   ["ticker", "company", "sector", "industry", "close", "ret_1w_pct", "ret_4w_pct",
                    "ret_12w_pct", "cap_usd_bn_approx", "next_earnings", "reports_this_week"])
        print(f"  {d.name}: {len(keep)} names for pass 3 ({', '.join(sorted(sectors))})")


def score(out_dir):
    weeks, names, raw, adj = _data()
    # Marky's five: the channel mode (Pass 5) is Council v2's Marky.
    p5 = json.loads((lab.RESULTS / "pass5_marky.json").read_text(encoding="utf-8"))
    marky = {r["week"]: r["channel"]["picks"] for r in p5["weeks"]["council"]}
    cal = lab.earnings_calendar(names)
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    rows = []
    for label, W, _ in weeks:
        d = Path(out_dir) / label

        def picks(path):
            if not path.exists():
                return None
            doc = json.loads(path.read_text(encoding="utf-8"))
            return [str(p["ticker"]).upper() for p in doc.get("picks", [])][:TOP]
        members = {"Ophelia": picks(d / "ophelia/pass3/result.json"),
                   "Cecil": picks(d / "cecil/result.json"), "Marky": marky.get(label)}

        def ret(t):
            s = adj.get(t)
            r = s.week_return(W) if s else None
            return 0.0 if r is None else r
        F = _aggregate_weekly(raw["SPY"].before(W, 92))[-1].date
        tradeable = []
        for t in names:
            nxt = lab._next_report(cal.get(t), F) if t in raw else None
            etd = _business_days_between(F, nxt) if nxt else None
            if t in raw and not (etd is not None and 0 <= etd <= 5):
                tradeable.append(t)
        spy = adj["SPY"].week_return(W) or 0.0
        row = {"week": label, "spy": spy}
        for who, ps in members.items():
            if not ps:
                continue
            ps = [t for t in ps if t in names]
            book = statistics.fmean(ret(t) for t in ps) if ps else 0.0
            rng = random.Random(f"{lab.SEED}-{W}-{who}")
            draws = [statistics.fmean(ret(t) for t in rng.sample(tradeable, len(ps)))
                     for _ in range(lab.RANDOM_DRAWS)] if ps else [0.0]
            row[who] = {"picks": ps, "ret": book, "alpha": book - spy,
                        "vs_random": book - statistics.fmean(draws),
                        "pctile": sum(1 for x in draws if x < book) / len(draws)}
        p2 = d / "ophelia/pass2/result.json"
        if p2.exists():
            from scan_pipeline.config.tickers import COUNCIL_SECTORS
            final = {x["sector"] if isinstance(x, dict) else x
                     for x in json.loads(p2.read_text(encoding="utf-8"))["final4"]}
            stocks = [t for t in names if COUNCIL_SECTORS[t] != "Macro Assets" and t in raw]
            chosen = [t for t in stocks if COUNCIL_SECTORS[t] in final]
            if chosen:
                row["ophelia_sectors"] = {"final4": sorted(final),
                                          "edge": statistics.fmean(ret(t) for t in chosen)
                                          - statistics.fmean(ret(t) for t in stocks)}
        have = [w for w in ("Ophelia", "Cecil", "Marky") if w in row]
        row["overlap"] = {f"{a}-{b}": len(set(row[a]["picks"]) & set(row[b]["picks"]))
                          for i, a in enumerate(have) for b in have[i + 1:]}
        rows.append(row)
        print(f"  {label}  SPY {spy*100:+5.2f}%  " + "  ".join(
            f"{w} {row[w]['ret']*100:+5.2f}% (pctile {row[w]['pctile']:.0%}) {','.join(row[w]['picks'])}"
            for w in have) + f"  overlap {row['overlap']}")
    summary = {}
    for who in ("Ophelia", "Cecil", "Marky"):
        r = [x[who] for x in rows if who in x]
        if r:
            summary[who] = {"weeks": len(r), "mean_alpha": statistics.fmean(x["alpha"] for x in r),
                            "mean_vs_random": statistics.fmean(x["vs_random"] for x in r),
                            "vs_random_t": lab._tstat([x["vs_random"] for x in r]),
                            "mean_pctile": statistics.fmean(x["pctile"] for x in r)}
            s = summary[who]
            print(f"  {who:<8} {s['weeks']} weeks: alpha {s['mean_alpha']*100:+.2f}%/wk, vs random "
                  f"{s['mean_vs_random']*100:+.2f}%/wk (t {s['vs_random_t']:+.2f}), avg pctile {s['mean_pctile']:.0%}")
    edges = [x["ophelia_sectors"]["edge"] for x in rows if "ophelia_sectors" in x]
    if edges:
        summary["Ophelia_sectors"] = {"weeks": len(edges), "mean_edge": statistics.fmean(edges),
                                      "t": lab._tstat(edges), "weeks_positive": sum(1 for e in edges if e > 0)}
        s = summary["Ophelia_sectors"]
        print(f"  Ophelia's four sectors vs the 111's stocks next week: {s['mean_edge']*100:+.2f}%/wk "
              f"(t {s['t']:+.2f}), ahead {s['weeks_positive']}/{s['weeks']}")
    with open(lab.RESULTS / "room_v2_members.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"summary": summary, "weeks": rows}, fh, indent=1, default=float)
        fh.write("\n")


# ---------------------------------------------------------------------------
# The debate: synthesis draft -> each member approves or objects -> final
# ---------------------------------------------------------------------------
LENS = {
    "Ophelia": "the Council's sector strategist: you judge whether a name fits the sector calls you made for this week",
    "Cecil": "the Council's value investor: you judge whether a business is cheap and sound",
    "Marky": "the Council's chart reader: you buy pullbacks in rising channels, with weekly MACD turning up",
}


def _weekdirs(out_dir):
    return sorted(p for p in Path(out_dir).iterdir() if p.is_dir() and p.name[:4].isdigit())


def _marky_top():
    p5 = json.loads((lab.RESULTS / "pass5_marky.json").read_text(encoding="utf-8"))
    return {r["week"]: r["channel"]["top"] for r in p5["weeks"]["council"]}


def _chart_line(t, f):
    if f is None:
        return f"- **{t}**: under 40 weeks of closes; no reading."
    head = "qualifies" if f["qualifies"] else f"does not qualify ({f['why_not']})"
    return (f"- **{t}**: {head}. {abs(f['z']):.1f} widths {'below' if f['z'] < 0 else 'above'} its 26-week "
            f"channel line, which {'rises' if f['slope_year'] >= 0 else 'falls'} {abs(f['slope_year']) * 100:.0f}% "
            f"a year; weekly MACD histogram {'rising' if f['hist_rising'] else 'falling'}, MACD line "
            f"{'above' if f['macd_above_zero'] else 'below'} zero.")


def debate(out_dir):
    """Round 2 inputs: debate/logs.md (each member's five with its reasoning)
    and debate/sheet.csv (the facts for every name in the union)."""
    marky = _marky_top()
    for d in _weekdirs(out_dir):
        o, c = d / "ophelia/pass3/result.json", d / "cecil/result.json"
        if not (o.exists() and c.exists() and marky.get(d.name)):
            print(f"  {d.name}: a member's five is missing")
            continue
        od, cd = json.loads(o.read_text(encoding="utf-8")), json.loads(c.read_text(encoding="utf-8"))
        sectors = json.loads((d / "ophelia/pass3/my_sectors.json").read_text(encoding="utf-8"))
        lines = [f"# The Council's debate logs -- week of {d.name}", "",
                 "Three members with three different jobs picked five names each, working apart and "
                 "without seeing one another's picks.", "",
                 "## Ophelia -- sector rotation", "", "Her four sectors this week:", ""]
        lines += [f"- **{s['sector']}**: {s['thesis']}" for s in sectors["final4"]]
        lines += ["", "Her five:", ""]
        lines += [f"- **{p['ticker']}** ({p.get('sector', '')}): {p['why']}" for p in od["picks"]]
        lines += ["", f"Her summary: {od.get('summary', '')}", "",
                  "## Cecil -- value", "", "His five:", ""]
        lines += [f"- **{p['ticker']}**: {p['why']}" for p in cd["picks"]]
        lines += ["", f"His summary: {cd.get('summary', '')}", "",
                  "## Marky -- the chart: pullbacks in rising channels", "",
                  "His five, the top of his ranking (a numeric screen; he writes no prose):", ""]
        lines += [_chart_line(t["ticker"], t) for t in marky[d.name]]
        union = list(dict.fromkeys([p["ticker"].upper() for p in od["picks"]]
                                   + [p["ticker"].upper() for p in cd["picks"]]
                                   + [t["ticker"] for t in marky[d.name]]))
        (d / "debate").mkdir(exist_ok=True)
        with open(d / "debate/logs.md", "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        with open(d / "sheet_all.csv", encoding="utf-8", newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if r["ticker"] in union]
        _write_csv(d / "debate/sheet.csv", rows, list(rows[0]))
        print(f"  {d.name}: {len(union)} names in the union")


def approve(out_dir):
    """Round 3 inputs, after the synthesis draft: one folder per member, each
    with the draft and only that member's own lens on its names."""
    weeks, names, raw, adj = _data()
    from scan_pipeline.engines.marky import channel_facts
    from scan_pipeline.fetch_market_data import _aggregate_weekly
    mondays = {label: W for label, W, _ in weeks}
    for d in _weekdirs(out_dir):
        dr = d / "debate/draft.json"
        if not dr.exists():
            continue
        draft = json.loads(dr.read_text(encoding="utf-8"))
        book = [b["ticker"].upper() for b in draft["book"]]
        md = [f"# The synthesis draft -- week of {d.name}", "",
              f"Cash: {draft.get('cash', 0) * 100:.0f}%. Rationale: {draft.get('rationale', '')}", ""]
        md += [f"- **{b['ticker']}** {b['weight'] * 100:.0f}% -- backed by {', '.join(b.get('backers', [])) or 'none'}: "
               f"{b['why']}" for b in draft["book"]]
        with open(d / "sheet_all.csv", encoding="utf-8", newline="") as fh:
            sheet = {r["ticker"]: r for r in csv.DictReader(fh)}
        W = mondays[d.name]
        for who in ("Ophelia", "Cecil", "Marky"):
            a = d / "approve" / who.lower()
            a.mkdir(parents=True, exist_ok=True)
            with open(a / "draft.md", "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(md) + "\n")
            rows = [sheet[t] for t in book if t in sheet]
            if who == "Ophelia":
                shutil.copyfile(d / "ophelia/pass3/my_sectors.json", a / "my_sectors.json")
                _write_csv(a / "facts.csv", rows, ["ticker", "company", "sector", "industry", "close",
                                                   "ret_1w_pct", "ret_4w_pct", "ret_12w_pct"])
            elif who == "Cecil":
                _write_csv(a / "value.csv", rows, ["ticker", "company", "sector", "industry", "close", "pe_ttm",
                                                   "eps_growth_pct", "weekly_vol_12w_pct", "ret_12w_pct",
                                                   "cap_usd_bn_approx"])
            else:
                lines = [f"# Marky's chart reading of the draft -- week of {d.name}", ""]
                for t in book:
                    closes = [h.close for h in _aggregate_weekly(raw[t].before(W, 400))] if t in raw else []
                    lines.append(_chart_line(t, channel_facts(closes)))
                with open(a / "chart.md", "w", encoding="utf-8", newline="\n") as fh:
                    fh.write("\n".join(lines) + "\n")
        print(f"  {d.name}: approval folders for {', '.join(book)}")


def final(out_dir):
    """Round 4, by rule: a name two of three members object to is swapped for
    the first unused alternate (which inherits its weight); objections that
    did not carry are kept as dissents. Then everything is scored."""
    weeks, names, raw, adj = _data()
    cal = lab.earnings_calendar(names)
    from scan_pipeline.fetch_market_data import _aggregate_weekly, _business_days_between
    marky = {w: [t["ticker"] for t in top] for w, top in _marky_top().items()}
    rows = []
    for label, W, council_book in weeks:
        d = Path(out_dir) / label
        dr = d / "debate/draft.json"
        votes = {who: d / "approve" / who.lower() / "result.json" for who in ("Ophelia", "Cecil", "Marky")}
        if not dr.exists() or not all(v.exists() for v in votes.values()):
            continue
        draft = json.loads(dr.read_text(encoding="utf-8"))
        objections = {}
        for who, v in votes.items():
            for x in json.loads(v.read_text(encoding="utf-8"))["votes"]:
                if x["vote"] == "object":
                    objections.setdefault(x["ticker"].upper(), []).append((who, x["reason"]))
        alts = [a.upper() for a in draft.get("alternates", [])]
        final_book, swaps, dissents = [], [], []
        for b in draft["book"]:
            t, w = b["ticker"].upper(), float(b["weight"])
            obj = objections.get(t, [])
            if len(obj) >= 2 and alts:
                new = alts.pop(0)
                swaps.append({"out": t, "in": new, "objections": obj})
                final_book.append((new, w))
            else:
                final_book.append((t, w))
                dissents += [{"ticker": t, "member": m, "reason": r} for m, r in obj]
        with open(d / "debate/final.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"week": label, "book": [{"ticker": t, "weight": w} for t, w in final_book],
                       "swaps": swaps, "dissents": dissents}, fh, indent=1)
            fh.write("\n")

        def ret(t):
            s = adj.get(t)
            r = s.week_return(W) if s else None
            return 0.0 if r is None else r
        F = _aggregate_weekly(raw["SPY"].before(W, 92))[-1].date
        tradeable = []
        for t in names:
            nxt = lab._next_report(cal.get(t), F) if t in raw else None
            etd = _business_days_between(F, nxt) if nxt else None
            if t in raw and not (etd is not None and 0 <= etd <= 5):
                tradeable.append(t)
        spy = adj["SPY"].week_return(W) or 0.0

        def scored(book, tag):
            ws = sorted((w for _, w in book), reverse=True)
            r = sum(w * ret(t) for t, w in book)
            rng = random.Random(f"{lab.SEED}-{W}-{tag}")
            draws = [sum(w * ret(t) for t, w in zip(rng.sample(tradeable, len(ws)), ws))
                     for _ in range(lab.RANDOM_DRAWS)] if ws else [0.0]
            return {"book": [(t, round(w, 4)) for t, w in book], "ret": r, "alpha": r - spy,
                    "invested": sum(ws), "vs_random": r - statistics.fmean(draws),
                    "pctile": sum(1 for x in draws if x < r) / len(draws)}
        draft_book = [(b["ticker"].upper(), float(b["weight"])) for b in draft["book"]]
        row = {"week": label, "spy": spy, "draft": scored(draft_book, "draft"),
               "final": scored(final_book, "final"),
               "council": sum(w * ret(t) for t, w in council_book) if council_book else 0.0,
               "swaps": len(swaps), "dissents": len(dissents)}
        rows.append(row)
        f = row["final"]
        print(f"  {label}  final {f['ret']*100:+6.2f}% (a {f['alpha']*100:+5.2f}, inv {f['invested']:.0%}, "
              f"pctile {f['pctile']:.0%})  draft {row['draft']['ret']*100:+6.2f}%  council {row['council']*100:+6.2f}%  "
              f"SPY {spy*100:+5.2f}%  swaps {len(swaps)}  {', '.join(f'{t} {w:.0%}' for t, w in final_book)}")
    if not rows:
        return
    summary = {}
    for k in ("draft", "final"):
        r = [x[k] for x in rows]
        cum, dd = lab._curve([x["ret"] for x in r])
        summary[k] = {"weeks": len(r), "mean_alpha": statistics.fmean(x["alpha"] for x in r),
                      "alpha_t": lab._tstat([x["alpha"] for x in r]),
                      "mean_vs_random": statistics.fmean(x["vs_random"] for x in r),
                      "vs_random_t": lab._tstat([x["vs_random"] for x in r]),
                      "mean_pctile": statistics.fmean(x["pctile"] for x in r),
                      "mean_invested": statistics.fmean(x["invested"] for x in r),
                      "cumulative": cum, "max_drawdown": dd}
    vc = [x["final"]["ret"] - x["council"] for x in rows]
    summary["final_vs_council"] = {"mean": statistics.fmean(vc), "t": lab._tstat(vc),
                                   "weeks_better": sum(1 for v in vc if v > 0)}
    summary["swaps"] = sum(x["swaps"] for x in rows)
    summary["dissents"] = sum(x["dissents"] for x in rows)
    for k in ("draft", "final"):
        s = summary[k]
        print(f"  {k:<6} alpha {s['mean_alpha']*100:+.2f}%/wk (t {s['alpha_t']:+.2f}), vs random "
              f"{s['mean_vs_random']*100:+.2f}%/wk (t {s['vs_random_t']:+.2f}, pctile {s['mean_pctile']:.0%}), "
              f"invested {s['mean_invested']:.0%}, cum {s['cumulative']*100:+.1f}%, max DD {s['max_drawdown']*100:.1f}%")
    s = summary["final_vs_council"]
    print(f"  final vs the real Council: {s['mean']*100:+.2f}%/wk (t {s['t']:+.2f}), better {s['weeks_better']}/{len(rows)}; "
          f"swaps {summary['swaps']}, dissents kept {summary['dissents']}")
    with open(lab.RESULTS / "room_v2_debate.json", "w", encoding="ascii", newline="\n") as fh:
        json.dump({"summary": summary, "weeks": rows}, fh, indent=1, default=float)
        fh.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("build", "pass3", "score", "debate", "approve", "final"))
    ap.add_argument("dir")
    a = ap.parse_args(argv)
    {"build": build, "pass3": pass3, "score": score, "debate": debate, "approve": approve,
     "final": final}[a.command](a.dir)


if __name__ == "__main__":
    main()
