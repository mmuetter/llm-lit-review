"""Enumerate and date the papers whose title or abstract uses a synerg* word.

These papers form the eligible population. Each year is bisected by date until
every slice is retrievable. PubMed's [dp] field matches both the print and the
electronic date, so each paper is then dated once, by the later of the two
years; dates fetched for earlier pools are reused.
"""

import datetime
import json
import sys
import time
from collections import Counter
from pathlib import Path

from enumerate_score1 import raw_dates, search_slice, slice_pmids
from pubmed_scoring import NCBI_DELAY_SECONDS
from year_gate_counts import SUMMARY_BATCH_SIZE, summary_page, year_of

DATA_DIR = Path(__file__).parent.parent / "data"
GATE_PATH = DATA_DIR / "synerg_gate_pmids.json"
DATES_PATH = DATA_DIR / "synerg_dates.jsonl"
YEARS_PATH = DATA_DIR / "synerg_paper_years.json"
PER_YEAR_PATH = DATA_DIR / "synerg_papers_per_year.json"
CACHED_DATES_PATHS = (DATA_DIR / "score1_dates.jsonl", DATA_DIR / "gated_v3_dates.jsonl", DATES_PATH)
SYNERGY_QUERY = "synerg*[tiab]"
FIRST_YEAR = 2010
LAST_YEAR = 2025


def year_pmids(year):
    """Return one year's synerg* PMIDs, checked against PubMed's count."""
    start, end = datetime.date(year, 1, 1), datetime.date(year, 12, 31)
    expected, _ = search_slice(SYNERGY_QUERY, start, end)
    pmids = slice_pmids(SYNERGY_QUERY, start, end)
    if len(pmids) != expected:
        raise ValueError(f"{year}: retrieved {len(pmids)} of {expected}")
    print(f"  {year}: {len(pmids):6d}", file=sys.stderr, flush=True)
    return pmids


def gate_pmids():
    """Return the synerg* PMIDs of every [dp] year, enumerating them once."""
    if GATE_PATH.exists():
        return json.loads(GATE_PATH.read_text())
    pmids = set()
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        pmids |= year_pmids(year)
    GATE_PATH.write_text(json.dumps(sorted(pmids)))
    return sorted(pmids)


def cached_dates():
    """Return every raw date already fetched, keyed by PMID."""
    dated = {}
    for path in CACHED_DATES_PATHS:
        if path.exists():
            for record in map(json.loads, path.open()):
                dated.update(record)
    return dated


def date_missing(pmids, dated):
    """Fetch and checkpoint the raw dates of PMIDs not yet dated."""
    pending = sorted(set(pmids) - set(dated))
    with DATES_PATH.open("a") as log:
        for start in range(0, len(pending), SUMMARY_BATCH_SIZE):
            result = summary_page(pending[start:start + SUMMARY_BATCH_SIZE])
            stamps = {pmid: raw_dates(result[pmid]) for pmid in result.get("uids", [])}
            log.write(json.dumps(stamps) + "\n")
            log.flush()
            dated.update(stamps)
            time.sleep(NCBI_DELAY_SECONDS)
            print(f"  dated {min(start + SUMMARY_BATCH_SIZE, len(pending))}/{len(pending)}",
                  file=sys.stderr, flush=True)
    return dated


def main():
    """Enumerate and date the synerg* papers, then save the in-window years."""
    pmids = gate_pmids()
    dated = date_missing(pmids, cached_dates())
    undated = set(pmids) - set(dated)
    if undated:
        raise ValueError(f"{len(undated)} PMIDs undated; rerun to date them")
    years = {pmid: year_of(dated[pmid]) for pmid in pmids}
    windowed = {pmid: year for pmid, year in years.items()
                if year and FIRST_YEAR <= year <= LAST_YEAR}
    counts = Counter(windowed.values())
    YEARS_PATH.write_text(json.dumps(windowed))
    PER_YEAR_PATH.write_text(json.dumps({str(y): counts[y] for y in sorted(counts)}, indent=2))
    print(f"synerg* papers: {len(pmids)} enumerated, "
          f"{len(windowed)} in {FIRST_YEAR}-{LAST_YEAR} by latest publication date")


if __name__ == "__main__":
    main()
