# Runner fix required: `backfill_weekly.py` deletes series when given `--only`

**To:** whoever maintains the scan runner (Kimi side)
**From:** weekly-council-scan / sector-regime-heatmap
**Date:** 2026-08-26
**Severity:** high — silent data loss, reported as success

---

## Summary

`backfill_weekly.py` has no way to *add* tickers to an existing weekly file.
Asking it to do so with `--only ... --force` **replaces** the file with just
those tickers, deleting every other series.

On 2026-08-26 this ran against `weekly-council-scan/data/weekly` and turned
**287 series into 44, across 107 weekly files**. The job exited 0 and reported
success. It was caught by inspection, not by any gate, and reverted.

The repo-side copy at `scripts/backfill_weekly.py` has been fixed. **The
runner's copy has not**, and `scan_pipeline/scripts/backfill_weekly.py` in this
repo is a mirror of it, so the two have diverged. This document is what the
runner needs so they converge again.

---

## The defect

`build_and_write()` constructs its bars from the ticker list it was handed and
calls `snapshot.write_weekly()`:

```python
def build_and_write(friday, tickers, history, out_dir):
    bars, missing = {}, []
    for t in tickers:                     # <-- only the --only set
        bar, actual = slice_week(history.get(t, ([], [], [])), monday, friday)
        ...
    path = snapshot.write_weekly(          # <-- writes a COMPLETE file
        friday.isoformat(), {"bars": bars, "missing": missing}, special,
        out_dir=out_dir)
```

`write_weekly()` composes a whole document — `as_of`, `source`, `fetched_at`,
`series`, the special blocks, `missing` — and writes it. There is no read of
the existing file and no merge. So:

| Invocation | Intent | Actual |
|---|---|---|
| No `--only`, `--force` | Full-universe rewrite | Correct. Writing the whole file is the operation. |
| `--only A,B,C`, no `--force` | Fill new names | Skips existing files entirely — nothing happens. |
| `--only A,B,C` **+** `--force` | Fill new names | **Replaces each week with A,B,C. Everything else is deleted.** |

The third row is the one that looks like the answer, and it is the one that was
documented. Our own `BACKFILL_44.md` said, incorrectly:

> `--force` is required because the target weekly files already exist; the run
> adds the new names to `series` in each.

That sentence is why the command looked safe. It has been corrected.

---

## What the runner should change

### 1. Add a merge path

Add `merge_into_existing()` and call it when the file exists and named tickers
were requested. Reference implementation is in this repo at
`scripts/backfill_weekly.py`. The essential shape:

```python
def merge_into_existing(friday, tickers, history, path):
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    if doc.get("as_of") != friday.isoformat():
        raise SystemExit("refusing to merge into a file that is not the week "
                         "it claims to be")

    series = doc.setdefault("series", {})
    prov = doc.setdefault("provenance", {}).setdefault("series", {})

    fresh = {}
    for t in tickers:
        bar, _ = slice_week(history.get(t, ([], [], [])), monday, friday)
        if bar is not None:
            fresh[t] = bar

    # Same normalizer write_weekly uses, so a merged bar is indistinguishable
    # in shape and rounding from a scanned one.
    for t, bar in snapshot._normalize_block(fresh).items():
        series[t] = bar
        prov[t] = {"source": BACKFILL_SOURCE, "fetched_at": RUN_TS}

    # `missing` stays honest in both directions.
    filled = set(fresh)
    missing = [m for m in doc.get("missing", []) if m.get("ticker") not in filled]
    listed = {m.get("ticker") for m in missing}
    for t in tickers:
        if t not in filled and t not in listed:
            missing.append({"ticker": t, "reason": MISSING_REASON % friday.isoformat()})
    doc["missing"] = sorted(missing, key=lambda m: m.get("ticker") or "")

    if not prov:
        doc.pop("provenance", None)

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(snapshot.canonical_json(doc))
```

Three details in there are not optional:

- **Do not restamp the file-level `fetched_at` or `source`.** They describe the
  series that were already in the file. The names being merged were fetched
  *now*; the other 287 were not. Restamping relabels every untouched series
  with a fetch that never happened to it.
- **Route merged bars through the same normalizer `write_weekly` uses.**
  Writing the raw slice lands full float precision (`179.94000244140625`)
  beside the panel's rounded closes.
- **Keep `missing` correct in both directions.** A ticker that now has a bar is
  no longer missing; one that still has none is listed with a reason rather
  than silently absent.

### 2. Refuse the dangerous combination outright

```python
if args.only and args.force and not args.merge:
    ap.error("--only with --force replaces each week with just those tickers, "
             "deleting every other series (this emptied 107 files on "
             "2026-08-26). Use --merge to add them, or drop --only for a "
             "full-universe rewrite.")
if args.merge and not args.only:
    ap.error("--merge adds specific tickers to existing weeks; pass --only "
             "with the tickers to add.")
```

`--force` stays valid for what it actually means: a full-universe rewrite with
no `--only`.

### 3. Record per-series provenance

This is a **contract change consumers already depend on**, specified in
`DATA_FEED.md` §1.

Adjusted closes are back-adjusted to the fetch date, so a merged week contains
series sitting on two different anchors. The file-level `fetched_at` still
describes the majority; the merged names carry their own:

```json
"provenance": {
  "series": {
    "PLTR": { "source": "yahoo-backfill", "fetched_at": "2026-08-26T04:08:06Z" },
    "VST":  { "source": "yahoo-backfill", "fetched_at": "2026-08-26T04:08:06Z" }
  }
}
```

Rules: the block is optional; a series absent from it carries the file-level
anchor; every key in `provenance.series` must exist in `series`. Files written
before this change stay valid unchanged.

`sector-regime-heatmap` resolves the adjustment anchor **per ticker** and
refuses a horizon whose anchors span more than 180 days. Without this block a
merged week reports one anchor for two, and that gate reads green while the
panel is mixed.

---

## What *not* to do

- **Do not just add a warning to `--force`.** The combination has to be refused
  in code. It was documented as safe for weeks, and a warning in a log nobody
  reads at 04:00 is not a gate.
- **Do not fix this by making `--only` imply `--force`.** That makes the
  destructive path the default.
- **Do not skip the `provenance` block** on the grounds that the numbers come
  out the same. They do come out the same; the *anchor* does not, and the
  downstream gate exists to catch exactly that.

Note the root-resolution bug we hit does **not** apply to the runner: the
runner's copy genuinely lives at `scan_pipeline/scripts/`, so its two-hop walk
to the repo root is correct. Ours had to be fixed because the file was also
copied to a top-level `scripts/`.

---

## How to verify the fix

Run against a **copy** of a real panel, never the live one.

```
python backfill_weekly.py --out <copy>/data --only PLTR,VST,RDDT \
    --start 2026-08-07 --end 2026-08-21 --merge
```

Then check, per file:

1. Series count **grew** by the number of names merged — nothing else moved.
2. Every pre-existing bar is **bit-identical**.
3. File-level `fetched_at` and `source` are **unchanged**.
4. `provenance.series` names exactly the merged tickers.
5. Merged closes are rounded like their neighbours.
6. Specials (`rates`, `vol`, `commodities`, `fx`) untouched.

And confirm the guard fires:

```
python backfill_weekly.py --out data --only PLTR --force     # must exit non-zero
python backfill_weekly.py --out data --merge                 # must exit non-zero
```

We have this covered by 27 tests in `weekly-council-scan/tests/`, which run
without network access (the provider is stubbed) — `tests/test_backfill_merge.py`
is the directly relevant file and can be lifted as-is.

---

## Why this matters more than a normal bug

The panel scores real money across two family accounts, and the governing rule
in both repos is *never invent a number to make something pass; a refused run
is the system working*. This defect is the inverse: it produced a confidently
wrong panel and reported success. Two gates that should have caught it were
also inert at the time — `truth_check` was invoked without its required
`--repo` argument and exited on a usage error that `|| echo` swallowed, and the
series-count step printed counts with nothing to compare them against. Both are
now fixed on our side, along with a `panel_guard.py` that fails any run in
which a weekly file loses series.

Until the runner's copy is updated, `scan_pipeline/scripts/backfill_weekly.py`
in this repo carries a "DO NOT RUN THIS COPY" header and a test fails if
anything invokes it.

---

## Contact / references

- Reference implementation: `scripts/backfill_weekly.py` (this repo)
- Contract: `DATA_FEED.md` §1 (`provenance`)
- Incident commits: `6260495` (the loss), `2a0f0dd` (revert), `3a099f6` (correct re-run with `--merge`)
- Corrected runbook: `BACKFILL_44.md`
