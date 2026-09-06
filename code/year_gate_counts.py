"""Per-year counts of the gated papers, derived from the pooled gate.

Counts are taken from the deduplicated gate file rather than from separate
per-year queries, so the series sums to the gate size exactly. PubMed's [dp]
field matches both the electronic and the print publication date, so a paper
straddling a year boundary is returned by two year queries; each paper is
instead dated once, by its sortpubdate year.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from pubmed_scoring import EUTILS_BASE, MAX_RATE_LIMIT_RETRIES, NCBI_DELAY_SECONDS

DATA_DIR = Path(__file__).parent.parent / "data"
TERM_SCORES_PATH = DATA_DIR / "term_scores_v2.json"
OUTPUT_PATH = DATA_DIR / "gated_papers_per_year.json"
YEARS_PATH = DATA_DIR / "gated_paper_years.json"
GATE_THRESHOLD = 2
SUMMARY_BATCH_SIZE = 200


def gated_pmids():
    """Return the deduplicated PMIDs that meet the gate."""
    scores = json.loads(TERM_SCORES_PATH.read_text())
    return sorted(pmid for pmid, score in scores.items() if score >= GATE_THRESHOLD)


def summary_page(pmids):
    """Fetch the esummary payload for one batch of PMIDs."""
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    url = f"{EUTILS_BASE}/esummary.fcgi?{urllib.parse.urlencode(params)}"
    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                body = response.read().decode("utf-8", errors="replace")
            return json.loads(body, strict=False)["result"]
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == MAX_RATE_LIMIT_RETRIES - 1:
                raise
            time.sleep(2 * (attempt + 1))


def year_of(record):
    """Return the sortpubdate year of one record, or None if absent."""
    stamp = record.get("sortpubdate") or record.get("pubdate") or ""
    head = stamp[:4]
    return int(head) if head.isdigit() else None


def fetch_years(pmids):
    """Map each PMID to its single publication year."""
    years = {}
    for start in range(0, len(pmids), SUMMARY_BATCH_SIZE):
        batch = pmids[start:start + SUMMARY_BATCH_SIZE]
        result = summary_page(batch)
        for pmid in result.get("uids", []):
            year = year_of(result[pmid])
            if year is not None:
                years[pmid] = year
        print(f"  {min(start + SUMMARY_BATCH_SIZE, len(pmids))}/{len(pmids)} dated",
              file=sys.stderr, flush=True)
        time.sleep(NCBI_DELAY_SECONDS)
    return years


def main():
    """Date every gated paper once and save the per-year counts."""
    pmids = gated_pmids()
    print(f"gated papers: {len(pmids)}", file=sys.stderr)
    years = fetch_years(pmids)
    counts = Counter(years.values())
    YEARS_PATH.write_text(json.dumps(years))
    OUTPUT_PATH.write_text(json.dumps({str(y): counts[y] for y in sorted(counts)}, indent=2))
    undated = len(pmids) - len(years)
    print(f"wrote {OUTPUT_PATH}")
    print(f"total {sum(counts.values())} of {len(pmids)} gated papers dated "
          f"({undated} without a usable date)")


if __name__ == "__main__":
    main()
