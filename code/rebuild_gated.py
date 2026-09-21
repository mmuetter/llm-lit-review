"""Rebuild the score >= 2 papers from pairwise group queries on a fresh snapshot.

A paper scores at least two exactly when it matches some pair of groups, so the
union of all pair queries gives every such paper and the groups it matches.
Slices and dates are checkpointed, so an interrupted run resumes losslessly.
"""

import datetime
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from enumerate_score1 import raw_dates, search_slice, slice_pmids
from pubmed_scoring import NCBI_DELAY_SECONDS, PUBMED_TERM_GROUPS
from year_gate_counts import SUMMARY_BATCH_SIZE, summary_page, year_of

DATA_DIR = Path(__file__).parent.parent / "data"
SLICES_PATH = DATA_DIR / "gated_v3_slices.jsonl"
DATES_PATH = DATA_DIR / "gated_v3_dates.jsonl"
SCORES_PATH = DATA_DIR / "term_scores_v3.json"
MEMBERSHIPS_PATH = DATA_DIR / "term_memberships_v3.json"
YEARS_PATH = DATA_DIR / "gated_paper_years_v3.json"
SCORE1_SLICES_PATH = DATA_DIR / "score1_slices.jsonl"
FIRST_YEAR = 2010
LAST_YEAR = 2025


def pair_query(first, second):
    """Build the query for papers matching both groups."""
    return f"({PUBMED_TERM_GROUPS[first]}) AND ({PUBMED_TERM_GROUPS[second]})"


def pending_units():
    """Return the (pair, year) units not yet checkpointed."""
    done = set()
    if SLICES_PATH.exists():
        done = {(tuple(r["pair"]), r["year"]) for r in map(json.loads, SLICES_PATH.open())}
    pairs = itertools.combinations(PUBMED_TERM_GROUPS, 2)
    return [(pair, year) for pair in pairs for year in range(FIRST_YEAR, LAST_YEAR + 1)
            if (pair, year) not in done]


def record_unit(log, pair, year):
    """Fetch one pair-year slice, check it against PubMed's count, and save it."""
    query = pair_query(*pair)
    start, end = datetime.date(year, 1, 1), datetime.date(year, 12, 31)
    expected, _ = search_slice(query, start, end)
    pmids = slice_pmids(query, start, end)
    if len(pmids) != expected:
        print(f"  WARNING {pair} {year}: retrieved {len(pmids)} of {expected}", file=sys.stderr)
    log.write(json.dumps({"pair": pair, "year": year, "expected": expected,
                          "pmids": sorted(pmids)}) + "\n")
    log.flush()
    print(f"  {pair[0]} x {pair[1]} {year}: {len(pmids):6d}", file=sys.stderr, flush=True)


def memberships():
    """Map every checkpointed PMID to the groups it matches."""
    groups = defaultdict(set)
    for record in map(json.loads, SLICES_PATH.open()):
        for pmid in record["pmids"]:
            groups[pmid].update(record["pair"])
    return groups


def dated_pmids():
    """Return the raw dates already checkpointed, keyed by PMID."""
    dated = {}
    if DATES_PATH.exists():
        for record in map(json.loads, DATES_PATH.open()):
            dated.update(record)
    return dated


def date_pmids(pmids):
    """Date every PMID not yet checkpointed, batch by batch."""
    pending = sorted(set(pmids) - set(dated_pmids()))
    with DATES_PATH.open("a") as log:
        for start in range(0, len(pending), SUMMARY_BATCH_SIZE):
            result = summary_page(pending[start:start + SUMMARY_BATCH_SIZE])
            log.write(json.dumps({p: raw_dates(result[p]) for p in result.get("uids", [])}) + "\n")
            log.flush()
            time.sleep(NCBI_DELAY_SECONDS)
            print(f"  dated {min(start + SUMMARY_BATCH_SIZE, len(pending))}/{len(pending)}",
                  file=sys.stderr, flush=True)


def score1_overlap(pmids):
    """Return rebuilt PMIDs that the score-1 enumeration also contains."""
    score1 = set()
    for record in map(json.loads, SCORE1_SLICES_PATH.open()):
        score1.update(record["pmids"])
    return sorted(score1 & set(pmids))


def main():
    """Rebuild, score, date and window the score >= 2 papers, then save them."""
    with SLICES_PATH.open("a") as log:
        for pair, year in pending_units():
            record_unit(log, pair, year)
    groups = memberships()
    SCORES_PATH.write_text(json.dumps({p: len(g) for p, g in groups.items()}))
    MEMBERSHIPS_PATH.write_text(json.dumps({p: sorted(g) for p, g in groups.items()}))
    print(f"score-1 overlap: {len(score1_overlap(groups))}")
    date_pmids(groups)
    undated = set(groups) - set(dated_pmids())
    if undated:
        raise ValueError(f"{len(undated)} PMIDs undated; rerun to date them")
    years = {p: year_of(stamps) for p, stamps in dated_pmids().items()}
    years = {p: y for p, y in years.items() if y and FIRST_YEAR <= y <= LAST_YEAR}
    YEARS_PATH.write_text(json.dumps(years))
    print(f"score >= 2: {len(groups)} retrieved, {len(years)} in {FIRST_YEAR}-{LAST_YEAR}; "
          f"by score {sorted(Counter(len(groups[p]) for p in years).items())}")


if __name__ == "__main__":
    main()
