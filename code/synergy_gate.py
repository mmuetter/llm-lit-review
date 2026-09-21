"""Enumerate the papers whose title or abstract uses a synergy term.

Only these papers can present synergy as desirable, so they form the eligible
population. Each year is bisected by date until every slice is retrievable.
"""

import datetime
import json
import sys
from pathlib import Path

from enumerate_score1 import search_slice, slice_pmids

DATA_DIR = Path(__file__).parent.parent / "data"
GATE_PATH = DATA_DIR / "synergy_gate_pmids.json"
SYNERGY_QUERY = "synergy[tiab] OR synergism[tiab] OR synergistic[tiab]"
FIRST_YEAR = 2010
LAST_YEAR = 2025


def year_pmids(year):
    """Return one year's synergy-term PMIDs, checked against PubMed's count."""
    start, end = datetime.date(year, 1, 1), datetime.date(year, 12, 31)
    expected, _ = search_slice(SYNERGY_QUERY, start, end)
    pmids = slice_pmids(SYNERGY_QUERY, start, end)
    if len(pmids) != expected:
        raise ValueError(f"{year}: retrieved {len(pmids)} of {expected}")
    print(f"  {year}: {len(pmids):6d}", file=sys.stderr, flush=True)
    return pmids


def main():
    """Enumerate every year's synergy-term PMIDs and save their union."""
    pmids = set()
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        pmids |= year_pmids(year)
    GATE_PATH.write_text(json.dumps(sorted(pmids)))
    print(f"synergy-term papers {FIRST_YEAR}-{LAST_YEAR}: {len(pmids)}")


if __name__ == "__main__":
    main()
