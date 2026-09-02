"""Gated-corpus composition for 2022-2025: term-group membership and journals."""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from pubmed_scoring_open import collect_memberships

DATA_DIR = Path(__file__).parent.parent / "data"
MEMBERSHIP_PATH = DATA_DIR / "spike2025_memberships.json"
JOURNAL_PATH = DATA_DIR / "spike2025_journals.json"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
YEARS = (2022, 2023, 2024, 2025)
CHUNK_SIZE = 200
NCBI_DELAY_SECONDS = 0.4
REQUEST_TIMEOUT_SECONDS = 120
MAX_RETRIES = 6
RETRY_BACKOFF_SECONDS = 2


def chunked(items, size):
    """Split a list into consecutive chunks of at most `size` items."""
    return [items[start:start + size] for start in range(0, len(items), size)]


def fetch_summary_chunk(pmids):
    """Post one esummary request and return its result block."""
    payload = urllib.parse.urlencode({"db": "pubmed", "retmode": "json",
                                      "id": ",".join(pmids)}).encode()
    with urllib.request.urlopen(ESUMMARY_URL, payload, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))["result"]


def summary_chunk(pmids):
    """Fetch one chunk of esummary records, retrying on failure."""
    for attempt in range(MAX_RETRIES):
        try:
            return fetch_summary_chunk(pmids)
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))


def record_fields(record):
    """Keep the journal, type and date fields the composition tables use."""
    return {"journal": record.get("fulljournalname") or record.get("source"),
            "pubtype": record.get("pubtype"),
            "pubdate": record.get("pubdate"),
            "epubdate": record.get("epubdate"),
            "sortdate": record.get("sortpubdate"),
            "lang": record.get("lang")}


def summaries_for(pmids):
    """Fetch the reported summary fields for every PMID."""
    collected = {}
    for chunk in chunked(sorted(pmids), CHUNK_SIZE):
        block = summary_chunk(chunk)
        collected.update({pmid: record_fields(block[pmid]) for pmid in chunk if pmid in block})
        time.sleep(NCBI_DELAY_SECONDS)
        print(f"    {len(collected)}/{len(pmids)}", file=sys.stderr, flush=True)
    return collected


def memberships_for_year(year):
    """Map each gated PMID in one year to the term groups it matched."""
    memberships, oversized = collect_memberships([year])
    if oversized:
        print(f"  warning: oversized pairs in {year}: {oversized}", file=sys.stderr)
    return {pmid: sorted(groups) for pmid, groups in memberships.items()}


def main():
    """Collect gated memberships and journal summaries for every year."""
    memberships = {}
    journals = {}
    for year in YEARS:
        memberships[year] = memberships_for_year(year)
        print(f"  {year}: {len(memberships[year])} gated papers", file=sys.stderr, flush=True)
        journals[year] = summaries_for(memberships[year])
    MEMBERSHIP_PATH.write_text(json.dumps(memberships))
    JOURNAL_PATH.write_text(json.dumps(journals))
    print(f"wrote {MEMBERSHIP_PATH} and {JOURNAL_PATH}")


if __name__ == "__main__":
    main()
