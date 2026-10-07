"""The phantom-EPS net of `truth_check --quarantine` (#120, second half).

The net looks at wiki table rows that hold a "$X EPS" claim and calls X
absurd when it is more than 20% of the share price in the same row. The
price was the first "$d.dd" figure on the row, and the pattern for that
matches the EPS figure itself. Read as its own price an EPS fails whatever
it is, since X is more than 20% of X.

On 2026-09-28 the Monday Council's second pass got two FAILs from it,
semiconductors.md:123 and :156: Micron's consensus "~$31.45 EPS", reported
as "$31.45 EPS vs $31.45 price". MU had closed at 1,082.28. Over every
version of every wiki file through 2026-10-06 the net FAILed 11 rows, and
five were this and nothing else.

The EPS figure is no longer a candidate for its own price. What is pinned:

  - the two rows of the issue, as the wiki held them, are clean;
  - a row with a real price still fails when the EPS is more than 20% of
    it, wherever on the row the price is, and passes when it is not;
  - a ban in macro/quarantine.json fires as before.

And what is not fixed is pinned too, so that changing it is a decision. The
price is still the first OTHER "$d.dd" figure on the row, which can be an
estimate or the reported number and not a share price. Of the six rows in
the wiki's history that still fail, one is the GOOGL $9.11 ghost the net was
written after (read against the $2.90 estimate beside it) and five are
earnings rows like "$2.04 EPS vs $1.60 est".
"""
from __future__ import annotations

import json

import pytest

import truth_check as tc  # noqa: E402  (conftest puts scripts/ on the path)

# wiki/semiconductors.md at 28feeeb, the version the 2026-09-28 run checked.
MU_ROW_123 = (
    "| **Memory / HBM / DRAM Pricing** | **Citi cuts MU target to $1,150 "
    "(from $1,400), sees pricing momentum slowing in 2027; MU FQ4 consensus "
    "~$31.45 EPS / ~$50.8B revenue** | The shortage is still in the numbers, "
    "but the second derivative is now being debated. Micron's guide on Sep "
    "30 settles it for now. |")
MU_ROW_156 = (
    "| **Micron** | MU | Sep 30, 2026 (after close) | FQ4 2026 | Street "
    "~$31.45 EPS / ~$50.8B revenue; FQ1 FY27 guide vs ~$35 / ~$56.6B; HBM "
    "allocation into 2027; whether DRAM/NAND pricing is still accelerating "
    "(the Citi debate); capex plan |")


def quarantine(tmp_path, rows, bans=()):
    """Run the check over a wiki of one page holding `rows` as a table."""
    (tmp_path / "wiki").mkdir()
    (tmp_path / "macro").mkdir()
    (tmp_path / "wiki" / "page.md").write_text(
        "# Page\n\n| a | b |\n|---|---|\n" + "\n".join(rows) + "\n",
        encoding="utf-8", newline="\n")
    (tmp_path / "macro" / "quarantine.json").write_text(
        json.dumps(list(bans)), encoding="utf-8", newline="\n")
    rep = tc.Report()
    tc.check_quarantine(tmp_path, rep)
    return rep


# -- the issue --------------------------------------------------------------

def test_the_two_rows_of_issue_120_are_clean(tmp_path):
    """Neither row holds a share price at all: $1,150 and $1,400 are
    targets with no cents, and $50.8B is revenue. The only "$d.dd" on
    either is the EPS."""
    rep = quarantine(tmp_path, [MU_ROW_123, MU_ROW_156])
    assert rep.counts["FAIL"] == 0
    assert rep.lines == ["OK: quarantine: 0 ban(s) active, no hits; "
                         "phantom-EPS net clean"]


def test_an_eps_figure_is_never_its_own_price(tmp_path):
    """The whole of the defect in one row. It used to read "$5.0 EPS vs
    $5.0 price", and so did any EPS written before any price."""
    rep = quarantine(tmp_path, ["| XYZ | Street $5.00 EPS on the quarter |"])
    assert rep.counts["FAIL"] == 0


# -- the net still works ----------------------------------------------------

@pytest.mark.parametrize("row, said", [
    ("| XYZ | $100.00 | reported $50.00 EPS |", "$50.0 EPS vs $100.0 price"),
    ("| XYZ | reported $50.00 EPS | $100.00 |", "$50.0 EPS vs $100.0 price"),
    ("| XYZ | **$100.00** | $50 per share |", "$50.0 EPS vs $100.0 price"),
], ids=["price-first", "eps-first", "bold-price"])
def test_an_eps_over_a_fifth_of_the_rows_price_still_fails(
        tmp_path, row, said):
    """Half the share price is not an EPS. With the EPS written first the
    old net failed this row too, against the EPS itself; it now says which
    price it means."""
    rep = quarantine(tmp_path, [row])
    assert rep.counts["FAIL"] == 1
    assert ("quarantine: page.md:5 phantom-EPS candidate: " + said
            + " -- quarantine or correct this row") in rep.lines[0]


@pytest.mark.parametrize("row", [
    "| XYZ | $100.00 | reported $5.00 EPS |",
    "| XYZ | reported $5.00 EPS | $100.00 |",
    "| MU | $1,082.28 | Street ~$31.45 EPS / ~$50.8B revenue |",
    "| MU | Street ~$31.45 EPS / ~$50.8B revenue | $1,082.28 |",
], ids=["price-first", "eps-first", "mu-price-first", "mu-eps-first"])
def test_a_plausible_eps_beside_its_price_passes(tmp_path, row):
    """The second and fourth rows failed before: the EPS came first, so it
    was the price. MU's is 2.9% of its close of 2026-09-25."""
    rep = quarantine(tmp_path, [row])
    assert rep.counts["FAIL"] == 0


def test_a_ban_fires_as_before(tmp_path):
    rep = quarantine(
        tmp_path, ["| GOOGL | $9.11 EPS |", MU_ROW_156],
        bans=[{"ticker": "GOOGL", "banned": "9.11",
               "reason": "ghost EPS, 2026-07-21 outage", "added": "2026-08-09"}])
    assert rep.counts["FAIL"] == 1
    assert rep.lines[0].startswith(
        "FAIL: quarantine: page.md:5 contains banned GOOGL value '9.11' "
        "(ghost EPS, 2026-07-21 outage)")


# -- not fixed, and pinned so that fixing it is a decision ------------------

@pytest.mark.parametrize("row, said", [
    ("| BMY | 14.4x / 4.06% yield | $2.04 EPS vs $1.60 est, guidance raised |",
     "$2.04 EPS vs $1.6 price"),
    ("| LMT | 21.5x / 2.37% yield | $7.94 EPS crushed $7.20 est |",
     "$7.94 EPS vs $7.2 price"),
    ("| **Oracle** | ORCL | Q1 FY2027 | $1.74 | Actual: adj. EPS $1.92. FY27 "
     "raised: $8.10 EPS. CLOSED at ~$150.28 |", "$8.1 EPS vs $1.74 price"),
    ("| **Alphabet** | **GOOGL** | Jul 22 | $2.90 | *anomalous* | reported "
     "$9.11 EPS |", "$9.11 EPS vs $2.9 price"),
], ids=["bmy", "lmt", "orcl", "googl"])
def test_the_price_can_still_be_an_estimate(tmp_path, row, said):
    """NOT DECIDED. The "price" is the first other "$d.dd" on the row, and
    on an earnings row that is the estimate. The first three are the shape
    of rows the wiki has held (synthesis.md, tech.md): true statements that
    the net fails. The first two failed before as well, against themselves.
    The third has the stock's own close further along, $150.28, and the net
    stops at the first figure. The fourth is the shape of the ghost the net
    was written after, and it is the estimate beside it that catches it,
    not a share price.

    Asking for a Price/Close/Last column, as the linter does, would clear
    the first three and lose the fourth."""
    rep = quarantine(tmp_path, [row])
    assert rep.counts["FAIL"] == 1
    assert said in rep.lines[0]
