"""Enumerate and date the papers matching exactly one indicator-term group.

Single groups exceed PubMed's retrieval limit, so each group's exclusive set
is fetched per year and bisected by date until every slice is retrievable.
Slices and dates are checkpointed, so an interrupted run resumes losslessly.
"""

import datetime
import json
import sys
import time
from pathlib import Path

from pubmed_scoring import (ESEARCH_PAGE_SIZE, ESEARCH_RETRIEVAL_LIMIT, NCBI_DELAY_SECONDS,
                            PUBMED_TERM_GROUPS, esearch_page)
from year_gate_counts import DATE_FIELDS, FALLBACK_DATE_FIELD, SUMMARY_BATCH_SIZE, summary_page, year_of

DATA_DIR = Path(__file__).parent.parent / "data"
SLICES_PATH = DATA_DIR / "score1_slices.jsonl"
DATES_PATH = DATA_DIR / "score1_dates.jsonl"
YEARS_PATH = DATA_DIR / "score1_paper_years.json"
GATED_SCORES_PATH = DATA_DIR / "term_scores_v2.json"
FIRST_YEAR = 2010
LAST_YEAR = 2025
ONE_DAY = datetime.timedelta(days=1)
STORED_DATE_FIELDS = (*DATE_FIELDS, FALLBACK_DATE_FIELD)


def exclusive_query(name):
    """Build the query for papers matching one group and no other."""
    others = " OR ".join(f"({query})" for other, query in PUBMED_TERM_GROUPS.items()
                         if other != name)
    return f"({PUBMED_TERM_GROUPS[name]}) NOT ({others})"


def date_filtered(query, start, end):
    """Restrict a query to a publication-date range."""
    return f'({query}) AND ("{start:%Y/%m/%d}"[dp] : "{end:%Y/%m/%d}"[dp])'


def search_slice(query, start, end):
    """Return the match count and first page of PMIDs for one date range."""
    page = esearch_page(date_filtered(query, start, end), 0, ESEARCH_PAGE_SIZE)
    time.sleep(NCBI_DELAY_SECONDS)
    return int(page["count"]), set(page["idlist"])


def slice_pmids(query, start, end):
    """Return every PMID in a date range, bisecting until each part fits."""
    count, pmids = search_slice(query, start, end)
    if count <= ESEARCH_RETRIEVAL_LIMIT:
        return pmids
    if start == end:
        raise ValueError(f"{count} records on {start} exceed the retrieval limit")
    middle = start + (end - start) // 2
    return slice_pmids(query, start, middle) | slice_pmids(query, middle + ONE_DAY, end)


def year_pmids(name, year):
    """Return one group's exclusive PMIDs for one year, checked against PubMed's count."""
    query = exclusive_query(name)
    start, end = datetime.date(year, 1, 1), datetime.date(year, 12, 31)
    expected, _ = search_slice(query, start, end)
    pmids = slice_pmids(query, start, end)
    if len(pmids) != expected:
        print(f"  WARNING {name} {year}: retrieved {len(pmids)} of {expected}", file=sys.stderr)
    return pmids, expected


def completed_slices():
    """Return the (group, year) units already checkpointed."""
    if not SLICES_PATH.exists():
        return set()
    return {(r["group"], r["year"]) for r in map(json.loads, SLICES_PATH.open())}


def record_slice(log, name, year):
    """Fetch one group-year slice and append it to the checkpoint."""
    pmids, expected = year_pmids(name, year)
    log.write(json.dumps({"group": name, "year": year, "expected": expected,
                          "pmids": sorted(pmids)}) + "\n")
    log.flush()
    print(f"  {name:22s} {year}: {len(pmids):6d}", file=sys.stderr, flush=True)


def enumerate_slices():
    """Fetch every group-year slice not yet checkpointed."""
    done = completed_slices()
    pending = [(name, year) for name in PUBMED_TERM_GROUPS
               for year in range(FIRST_YEAR, LAST_YEAR + 1) if (name, year) not in done]
    with SLICES_PATH.open("a") as log:
        for name, year in pending:
            record_slice(log, name, year)


def score1_pmids():
    """Return the deduplicated score-1 PMIDs with the group each matches."""
    groups = {}
    for record in map(json.loads, SLICES_PATH.open()):
        groups.update(dict.fromkeys(record["pmids"], record["group"]))
    return groups


def raw_dates(record):
    """Return the date strings a publication year is derived from."""
    return {field: record.get(field, "") for field in STORED_DATE_FIELDS}


def dated_pmids():
    """Return the raw dates already checkpointed, keyed by PMID."""
    if not DATES_PATH.exists():
        return {}
    dated = {}
    for record in map(json.loads, DATES_PATH.open()):
        dated.update(record)
    return dated


def date_pmids(pmids):
    """Date every PMID not yet checkpointed, batch by batch."""
    pending = sorted(set(pmids) - set(dated_pmids()))
    with DATES_PATH.open("a") as log:
        for start in range(0, len(pending), SUMMARY_BATCH_SIZE):
            result = summary_page(pending[start:start + SUMMARY_BATCH_SIZE])
            stamps = {pmid: raw_dates(result[pmid]) for pmid in result.get("uids", [])}
            log.write(json.dumps(stamps) + "\n")
            log.flush()
            time.sleep(NCBI_DELAY_SECONDS)
            print(f"  dated {min(start + SUMMARY_BATCH_SIZE, len(pending))}/{len(pending)}",
                  file=sys.stderr, flush=True)


def overlap_with_gate(pmids):
    """Return score-1 PMIDs that also appear in the score >= 2 gate."""
    gated = json.loads(GATED_SCORES_PATH.read_text())
    return sorted(set(pmids) & set(gated))


def main():
    """Enumerate, date and window the score-1 papers, then save their years."""
    enumerate_slices()
    groups = score1_pmids()
    overlap = overlap_with_gate(groups)
    if overlap:
        raise ValueError(f"{len(overlap)} score-1 PMIDs are also gated, e.g. {overlap[:3]}")
    date_pmids(groups)
    years = {pmid: year_of(stamps) for pmid, stamps in dated_pmids().items()}
    years = {pmid: year for pmid, year in years.items() if year and FIRST_YEAR <= year <= LAST_YEAR}
    YEARS_PATH.write_text(json.dumps(years))
    print(f"score-1 papers: {len(groups)} enumerated, {len(years)} in "
          f"{FIRST_YEAR}-{LAST_YEAR} by latest publication date")


if __name__ == "__main__":
    main()
