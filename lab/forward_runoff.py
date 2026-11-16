#!/usr/bin/env python3
"""Pass 36 B -- the runoff, forward: from a story to the names several steps away.

The owner's idea: the companies affected by the companies affected by the
story (generator sellers after a flood). A session writes, for each of the
week's big stories and loudest stock moves, the causal chain out to each
linked name, hop by hop; `degree` is the number of hops. This script finds
the stock triggers, validates the maps and scores them.

  detect [--since YYYY-MM-DD] [--max N]
        The week's stock triggers, by Pass 36 A's rule (an S&P 500 name up or
        down 8% against SPY on twice its 20-day volume; 20-session cool-off;
        one per sub-industry, day and direction), largest moves first, both
        directions when both exist, minus the ones already mapped. Prints
        JSON. Writes nothing.
  check FILE
        Validates a map file (lab/runoff/<DAY>_<KEY>.json); for a stock
        trigger, also that `detect` would print it. Prints VALID or problems.
  (no argument)
        Scores every map whose window has closed and rewrites lab/RUNOFF.md
        and lab/results/runoff.json. Entry is the first open after the file's
        commit; a file edited after that open is not scored.

Registered in lab/README.md (Pass 36 B) before the first map.

    python lab/forward_runoff.py detect
    python lab/forward_runoff.py check lab/runoff/2026-11-20_gulf-flood.json
    python lab/forward_runoff.py
"""
from __future__ import annotations

import csv
import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_lab as lab  # noqa: E402

FULL_CSV = lab.LAB / "universe_sp500_full_2026-09-22.csv"
MAPS = lab.LAB / "runoff"
PAGE = lab.LAB / "RUNOFF.md"
OUT = lab.RESULTS / "runoff.json"
ET = ZoneInfo("America/New_York")
MOVE, VOL_X, VOL_N, COOL, CLIP = 0.08, 2.0, 20, 20, 0.50
RUNUP = 0.03                      # a link already up this much its expected way before entry counts as priced
HORIZONS = (5, 20)
TYPES = ("supplier", "customer", "competitor", "complement", "substitute", "demand", "cost")
MAX_DEGREE = 4
FIRST_DAY = "2026-11-16"          # nothing before the registration is mapped
MAX_LINKS, MIN_LINKS = 8, 2
DAY_RE = r"\d{4}-\d{2}-\d{2}"


def sp500():
    with open(FULL_CSV, encoding="ascii") as fh:
        return {r["ticker"]: r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}


def last_closed_session():
    n = datetime.now(ET)
    d = n.date() if n.hour >= 17 else n.date() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def triggers(since, until):
    """Stock triggers on sessions since..until (ISO dates, inclusive), by Pass 36 A's rule."""
    meta = sp500()
    names = sorted(meta)
    start = (date.fromisoformat(since) - timedelta(days=110)).isoformat()
    end = (date.fromisoformat(until) + timedelta(days=1)).isoformat()
    df = lab.download(sorted(names + ["SPY"]), True, end, start=start)
    have = set(df.columns.get_level_values(1))
    names = [t for t in names if t in have]
    spy = df["Close"]["SPY"].to_numpy(float)
    keep = np.isfinite(spy)
    dates = [x.strftime("%Y-%m-%d") for x in df.index[keep]]
    C = df["Close"][names].to_numpy(float)[keep]
    V = df["Volume"][names].to_numpy(float)[keep]
    sc = spy[keep]
    T, N = C.shape
    out, last = [], np.full(N, -10 ** 6)
    for d in range(VOL_N + 1, T):
        with np.errstate(invalid="ignore", divide="ignore"):
            ab = C[d] / C[d - 1] - 1.0 - (sc[d] / sc[d - 1] - 1.0)
            vx = V[d] / np.mean(V[d - VOL_N:d], axis=0)
        cand = np.isfinite(ab) & np.isfinite(vx) & (np.abs(ab) >= MOVE) & (vx >= VOL_X) & (d - last > COOL)
        groups = defaultdict(list)
        for j in np.where(cand)[0]:
            groups[(meta[names[j]]["gics_sub_industry"], ab[j] > 0)].append(j)
        for (sub, up), js in groups.items():
            j = max(js, key=lambda k: abs(ab[k]))
            for k in js:
                last[k] = d
            if since <= dates[d] <= until and dates[d] >= FIRST_DAY:
                out.append({"kind": "stock", "ticker": names[j], "day": dates[d], "direction": "up" if up else "down",
                            "move_vs_spy": round(float(ab[j]), 4), "volume_x": round(float(vx[j]), 2),
                            "sector": meta[names[j]]["gics_sector"], "sub_industry": sub,
                            "also_triggered": sorted(names[k] for k in js if k != j)})
    return out


def trigger_key(t):
    return t["ticker"] if t["kind"] == "stock" else t.get("slug", "")


def validate(d, name=None):
    bad = []
    if not isinstance(d, dict):
        return ["not a JSON object"]
    t = d.get("trigger")
    if not isinstance(t, dict) or t.get("kind") not in ("stock", "story") or not re.fullmatch(DAY_RE, str(t.get("day", ""))):
        return ["trigger block needs kind (stock or story) and day (YYYY-MM-DD)"]
    if t["kind"] == "stock":
        if not all(k in t for k in ("ticker", "direction", "move_vs_spy", "volume_x")):
            return ["stock trigger incomplete (copy it from `detect`)"]
    else:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+){0,5}", str(t.get("slug", ""))):
            bad.append("story trigger needs slug: lower-case words joined by hyphens, six at most")
        if not isinstance(t.get("headline"), str) or len(t["headline"]) < 15:
            bad.append("story trigger needs headline (the story as the Market Brief states it)")
        if not isinstance(t.get("source"), str) or "Market Brief" not in t["source"]:
            bad.append("story trigger source must name the README Market Brief it came from")
    if name and name != f"{t['day']}_{trigger_key(t)}.json":
        bad.append(f"file name must be {t['day']}_{trigger_key(t)}.json")
    for k in ("model", "recorded_at"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            bad.append(f"{k} is missing")
    links = d.get("links")
    if not isinstance(links, list) or not MIN_LINKS <= len(links) <= MAX_LINKS:
        return bad + [f"links must hold {MIN_LINKS} to {MAX_LINKS} rows"]
    seen = set()
    for i, r in enumerate(links, 1):
        tk = r.get("ticker")
        if not isinstance(tk, str) or not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,6}", tk):
            bad.append(f"link {i}: bad ticker {tk!r}")
        elif tk == t.get("ticker"):
            bad.append(f"link {i}: the trigger itself is not a link")
        elif tk in seen:
            bad.append(f"link {i}: {tk} listed twice")
        seen.add(tk)
        if r.get("type") not in TYPES:
            bad.append(f"link {i}: type must be one of {', '.join(TYPES)}")
        ch = r.get("chain")
        if r.get("degree") not in range(1, MAX_DEGREE + 1):
            bad.append(f"link {i}: degree must be 1 to {MAX_DEGREE}")
        elif not isinstance(ch, list) or len(ch) != r["degree"] or not all(isinstance(x, str) and 8 <= len(x) <= 160 for x in ch):
            bad.append(f"link {i}: chain must list one step per degree ({r['degree']} here), each 8 to 160 characters")
        if r.get("expected") not in (1, -1):
            bad.append(f"link {i}: expected must be 1 (outperform) or -1 (underperform)")
        if not isinstance(r.get("exposure_source"), str) or len(r["exposure_source"].strip()) < 12:
            bad.append(f"link {i}: exposure_source is missing (the filing or company page showing the name is in that business)")
    if not any(r.get("degree", 0) >= 2 for r in links):
        bad.append("no link is two or more steps out: the map must go past the obvious names")
    return bad


def commit_times(path):
    rel = str(path.relative_to(lab.ROOT)).replace("\\", "/")
    out = subprocess.run(["git", "-C", str(lab.ROOT), "log", "--format=%aI", "--", rel],
                         capture_output=True, text=True, check=True).stdout.split()
    return [datetime.fromisoformat(x) for x in out]


def entry_open_after(ts):
    """The first weekday 09:30 ET strictly after a commit time."""
    t = ts.astimezone(ET)
    day = t.date() if (t.hour, t.minute) < (9, 30) else t.date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return datetime.combine(day, datetime.min.time(), ET).replace(hour=9, minute=30)


def tstat(xs):
    xs = np.asarray([x for x in xs if x == x], float)
    if len(xs) < 3 or xs.std(ddof=1) == 0:
        return float("nan")
    return float(xs.mean() / (xs.std(ddof=1) / math.sqrt(len(xs))))


def score_map(d, first_commit):
    """Scores one map, or returns None while its 5-session window is open."""
    meta = sp500()
    t = d["trigger"]
    tickers = sorted({r["ticker"] for r in d["links"]} | {"SPY", "IWM"})
    start = (date.fromisoformat(t["day"]) - timedelta(days=8)).isoformat()
    end = (last_closed_session() + timedelta(days=1)).isoformat()
    df = lab.download(tickers, True, end, start=start)
    have = set(df.columns.get_level_values(1))
    spy = df["Close"]["SPY"].to_numpy(float)
    keep = np.isfinite(spy)
    dates = [x.strftime("%Y-%m-%d") for x in df.index[keep]]
    O = {k: df["Open"][k].to_numpy(float)[keep] for k in tickers if k in have}
    C = {k: df["Close"][k].to_numpy(float)[keep] for k in tickers if k in have}
    entry_day = entry_open_after(first_commit).date().isoformat()
    e = next((i for i, x in enumerate(dates) if x >= entry_day), None)
    if e is None or e + HORIZONS[0] - 1 >= len(dates):
        return None
    di = next((i for i, x in enumerate(dates) if x >= t["day"]), e)     # the story's day, or the next session
    di = max(1, min(di, e))
    res = {"trigger": t, "model": d["model"], "entry": dates[e], "lag": e - di, "links": []}
    for r in d["links"]:
        k = r["ticker"]
        b = "SPY" if k in meta else "IWM"
        row = dict(r, member=k in meta, bench=b)
        if k not in have or not np.isfinite(O[k][e]):
            row["no_data"] = True
            res["links"].append(row)
            continue
        # run-up: from the close before the story's day to the last close before entry, over the benchmark
        move = float("nan")
        if e - 1 > di - 1 and np.isfinite(C[k][e - 1]) and np.isfinite(C[k][di - 1]):
            move = (C[k][e - 1] / C[k][di - 1] - 1.0) - (C[b][e - 1] / C[b][di - 1] - 1.0)
        row["runup"] = None if move != move else float(move)
        row["priced"] = bool(move == move and r["expected"] * move >= RUNUP)
        for h in HORIZONS:
            x = e + h - 1
            if x < len(dates) and np.isfinite(C[k][x]):
                ex = (C[k][x] / O[k][e] - 1.0) - (C[b][x] / O[b][e] - 1.0)
                row[f"signed_{h}"] = float(np.clip(ex, -CLIP, CLIP) * r["expected"])
            else:
                row[f"signed_{h}"] = None
        res["links"].append(row)
    return res


def table(scored, pick, label):
    rows = []
    for h in HORIZONS:
        per_trig, n = [], 0
        for s in scored:
            vals = [r[f"signed_{h}"] for r in s["links"] if r.get(f"signed_{h}") is not None and pick(s, r)]
            if vals:
                per_trig.append(float(np.mean(vals)))
                n += len(vals)
        rows.append((h, n, len(per_trig), float(np.mean(per_trig)) if per_trig else None, tstat(per_trig)))
    return label, rows


def page(scored, pending, late):
    P = lambda x: "--" if x is None or x != x else f"{100 * x:+.2f}%"  # noqa: E731
    F = lambda x: "--" if x is None or x != x else f"{x:+.2f}"  # noqa: E731
    far = lambda r: r["degree"] >= 2  # noqa: E731
    out = ["# The runoff", "",
           "From the week's big stories and loudest stock moves to the names several causal steps away, each chain written",
           "out hop by hop before any of it was scored (Pass 36 B). Each link carries the direction the session expected;",
           "the numbers are the link's return over its benchmark (SPY for S&P 500 names, IWM for the rest) from the first",
           "open after the map was committed, signed by that expectation. `lab/forward_runoff.py` regenerates this page;",
           "edits by hand are overwritten.", "",
           f"Maps scored: {len(scored)}. Waiting on their window: {len(pending)}. Not scored (invalid, uncommitted or edited after entry): {len(late)}.", ""]
    if scored:
        groups = [
            table(scored, lambda s, r: far(r), "**Two or more steps out (decisive)**"),
            table(scored, lambda s, r: r["degree"] == 1, "One step (the obvious name)"),
            table(scored, lambda s, r: r["degree"] == 2, "Two steps"),
            table(scored, lambda s, r: r["degree"] >= 3, "Three or four steps"),
            table(scored, lambda s, r: far(r) and s["trigger"]["kind"] == "story", "Two or more steps, story triggers"),
            table(scored, lambda s, r: far(r) and s["trigger"]["kind"] == "stock", "Two or more steps, stock triggers"),
            table(scored, lambda s, r: far(r) and r["expected"] == 1, "Two or more steps, expected to outperform (buys)"),
            table(scored, lambda s, r: far(r) and r["expected"] == -1, "Two or more steps, expected to underperform (avoids)"),
            table(scored, lambda s, r: far(r) and not r["member"], "Two or more steps, outside the S&P 500"),
            table(scored, lambda s, r: far(r) and r["member"], "Two or more steps, S&P 500 names"),
            table(scored, lambda s, r: far(r) and not r.get("priced", False), "Two or more steps, no run-up before entry"),
            table(scored, lambda s, r: far(r) and r.get("priced", False), "Two or more steps, already run 3% its way"),
        ]
        out += ["| Group | 5 sessions: mean (t) | links / triggers | 20 sessions: mean (t) | links / triggers |", "|---|---|---|---|---|"]
        for label, rows in groups:
            cells = [f"{P(m)} ({F(t)}) | {n} / {k}" for _, n, k, m, t in rows]
            out.append(f"| {label} | " + " | ".join(cells) + " |")
        out += ["", "Means are over triggers (each trigger is the mean of its links); t is over triggers.", "",
                "| Trigger | Day | Entry | Sessions from the story | Links (steps) | Signed, 5 sessions | Signed, 20 sessions |", "|---|---|---|---|---|---|---|"]
        for s in scored:
            t = s["trigger"]
            m = {h: [r[f"signed_{h}"] for r in s["links"] if r.get(f"signed_{h}") is not None] for h in HORIZONS}
            name = f"{t['ticker']} {t['direction']}" if t["kind"] == "stock" else t["slug"]
            out.append(f"| {name} | {t['day']} | {s['entry']} | {s['lag']} | "
                       f"{', '.join(r['ticker'] + ' (' + str(r['degree']) + ')' for r in s['links'])} | "
                       f"{P(np.mean(m[5]) if m[5] else None)} | {P(np.mean(m[20]) if m[20] else None)} |")
        out.append("")
    else:
        out += ["No map has been scored yet.", ""]
    if late:
        out += ["## Not scored", ""] + [f"- {n}: {why}" for n, why in late] + [""]
    out += ["The registered reading waits for 60 scored links two or more steps out, from at least 20 triggers, on the",
            "20-session number: confirmed at +1.0% or more with t of 2 or more; rejected at zero or below with 100 links.",
            "Before that this page shows direction, not proof."]
    return "\n".join(out) + "\n"


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "score"
    if cmd == "detect":
        until = last_closed_session().isoformat()
        since = (date.fromisoformat(until) - timedelta(days=6)).isoformat()
        cap = 2
        if "--since" in argv:
            since = argv[argv.index("--since") + 1]
        if "--max" in argv:
            cap = int(argv[argv.index("--max") + 1])
        trig = triggers(since, until)
        done = {p.stem for p in MAPS.glob("*.json")} if MAPS.exists() else set()
        fresh = [t for t in trig if f"{t['day']}_{t['ticker']}" not in done]
        fresh.sort(key=lambda t: -abs(t["move_vs_spy"]))
        ups = [t for t in fresh if t["direction"] == "up"]
        downs = [t for t in fresh if t["direction"] == "down"]
        chosen = []                                  # alternate so both directions are mapped when both exist
        while len(chosen) < cap and (ups or downs):
            for pool in ((ups, downs) if len(chosen) % 2 == 0 else (downs, ups)):
                if pool:
                    chosen.append(pool.pop(0))
                    break
        print(json.dumps({"since": since, "until": until, "found": len(trig), "already_mapped": len(trig) - len(fresh),
                          "to_map": chosen}, indent=1))
        return 0
    if cmd == "check":
        path = Path(argv[2])
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        bad = validate(d, path.name)
        if not bad and d["trigger"]["kind"] == "stock":
            t = d["trigger"]
            same = [x for x in triggers(t["day"], t["day"]) if x["ticker"] == t["ticker"] and x["direction"] == t["direction"]]
            if not same:
                bad.append(f"{t['ticker']} {t['direction']} on {t['day']} is not a trigger `detect` prints")
        print("VALID" if not bad else "INVALID:\n  " + "\n  ".join(bad))
        return 1 if bad else 0
    scored, pending, late = [], [], []
    for path in sorted(MAPS.glob("*.json")) if MAPS.exists() else []:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        bad = validate(d, path.name)
        if bad:
            late.append((path.stem, "invalid: " + "; ".join(bad[:3])))
            continue
        times = commit_times(path)
        if not times:
            late.append((path.stem, "not committed"))
            continue
        if max(times) >= entry_open_after(min(times)):
            late.append((path.stem, f"edited {max(times).astimezone(ET):%Y-%m-%d %H:%M} ET, after its entry open"))
            continue
        r = score_map(d, min(times))
        (scored.append(r) if r else pending.append(path.stem))
    text = page(scored, pending, late)
    with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    lab.RESULTS.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"scored": scored, "pending": pending, "late": late}, fh, indent=1, default=float)
        fh.write("\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
