"""rederive_market_state.py -- regenerate data/market_state.json from scratch.

market_state.json is derived, and the derivation is pure: the weekly files,
data/us2y_treasury.json, data/commodity_settlements.json and macro/facts.json
in, one file out, byte for byte (DATA_FEED.md sec.2). The weekly job writes
it one step at a time, from last week's state. This writes the same file
through the whole chain, earliest week forward, which is what `truth_check
--derive` compares against -- so it regenerates the file after a change the
weekly job did not make:

  * a week added to data/us2y_treasury.json or an entry added to
    data/commodity_settlements.json (scripts/backfill_us2y.py and
    scripts/backfill_commodities.py call this themselves after a fill),
  * a change to the deriver,
  * macro/facts.json regenerated after the weekly job ran (the Sunday
    auditor's purity repair is this same derivation).

It refuses to run without facts.json. The deriver degrades every facts-fed
field to null when that file is missing, which is right for a derivation
and wrong for a repair: it would blank the policy block of a committed file.

CLI:
  python scripts/rederive_market_state.py [--data data] [--facts PATH]

  --data   the data root (default: data); reads <data>/weekly,
           <data>/us2y_treasury.json and <data>/commodity_settlements.json,
           writes <data>/market_state.json
  --facts  macro facts (default: macro/facts.json beside the data root)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Repo root = the nearest ancestor holding the scan_pipeline package. Copied
# from scripts/backfill_weekly.py deliberately; see the note there.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPELINE_ROOT = _SCRIPT_DIR
while not os.path.isdir(os.path.join(_PIPELINE_ROOT, "scan_pipeline")):
    _parent = os.path.dirname(_PIPELINE_ROOT)
    if _parent == _PIPELINE_ROOT:
        raise RuntimeError(
            "cannot locate the scan_pipeline package above " + _SCRIPT_DIR)
    _PIPELINE_ROOT = _parent
if _PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, _PIPELINE_ROOT)

from scan_pipeline import snapshot          # noqa: E402


def default_facts(data_root: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(data_root)),
                        "macro", "facts.json")


def rederive(data_root: str, facts_path: str | None = None) -> int:
    """Rewrite <data_root>/market_state.json through the whole chain.

    Returns 0 when the file is current afterwards, 1 when it could not be
    regenerated. Prints what changed, or that nothing did."""
    weekly_dir = os.path.join(data_root, "weekly")
    out_path = os.path.join(data_root, "market_state.json")
    facts_path = facts_path or default_facts(data_root)
    if not os.path.isdir(weekly_dir):
        print("No such directory: " + weekly_dir)
        return 1
    if not os.path.isfile(facts_path):
        print("NOT re-derived: " + facts_path + " not found. Deriving "
              "without it would null every facts-fed field (policy, the "
              "policy leg of regime, upcoming). Pass --facts.")
        return 1

    state = snapshot.derive_chain(weekly_dir, facts_path)
    before = None
    if os.path.isfile(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            before = json.load(f)
    if before is not None and (snapshot.canonical_json(before)
                               == snapshot.canonical_json(state)):
        print("market_state.json is already what the chain derives "
              "(as_of " + state["as_of"] + "); nothing written")
        return 0

    snapshot._write_json(out_path, state)
    where = ("(new file)" if before is None
             else "first difference at "
             + str(snapshot._first_diff(state, before)))
    us2y = state["rates"]["US2Y"]
    print("Re-derived " + out_path + ": as_of " + state["as_of"]
          + ", US2Y lvl " + str(us2y["lvl"]) + ", d1w_bps "
          + str(us2y["d1w_bps"]) + ", 2s10s "
          + str(state["rates"]["curve_2s10s_bps"]) + " " + where)
    return 0


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Regenerate data/market_state.json through the whole "
                    "derivation chain.")
    p.add_argument("--data", default="data",
                   help="data root (default: data)")
    p.add_argument("--facts", default=None,
                   help="macro facts file (default: macro/facts.json beside "
                        "the data root)")
    a = p.parse_args(argv)
    return rederive(a.data, a.facts)


if __name__ == "__main__":
    sys.exit(main())
