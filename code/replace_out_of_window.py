"""Swap out-of-window papers from the sample without redrawing the pool.

Papers whose latest publication year falls outside the analysis window are
dropped and replaced by continuing the same seeded shuffle, so the result stays
a uniform sample of the in-window gate. Only the replacements need classifying.
"""

import json
import random
from pathlib import Path

from analyse_screening import FIRST_YEAR, LAST_YEAR
from sampling import RANDOM_SEED, SAMPLE_PATH, fetch_records, gated_pmids, is_complete
from year_gate_counts import SUMMARY_BATCH_SIZE, summary_page, year_of

DATA_DIR = Path(__file__).parent.parent / "data"
REPLACEMENTS_PATH = DATA_DIR / "sample_replacements.json"
CANDIDATE_BATCH_SIZE = 100


def authoritative_years(pmids):
    """Map PMIDs to their single publication year via esummary."""
    years = {}
    for start in range(0, len(pmids), SUMMARY_BATCH_SIZE):
        result = summary_page(pmids[start:start + SUMMARY_BATCH_SIZE])
        for pmid in result.get("uids", []):
            year = year_of(result[pmid])
            if year is not None:
                years[pmid] = year
    return years


def in_window(year):
    """Return whether a year falls inside the analysis window."""
    return year is not None and FIRST_YEAR <= year <= LAST_YEAR


def out_of_window_pmids(papers):
    """Return sampled PMIDs whose true year lies outside the window."""
    years = authoritative_years([p["pmid"] for p in papers])
    return {p["pmid"] for p in papers if not in_window(years.get(p["pmid"]))}


def find_replacements(shuffled, start_index, held, needed):
    """Walk the shuffle onward for in-window papers with complete abstracts."""
    found, drawn = [], start_index
    while len(found) < needed and drawn < len(shuffled):
        chunk = [p for p in shuffled[drawn:drawn + CANDIDATE_BATCH_SIZE] if p not in held]
        drawn += CANDIDATE_BATCH_SIZE
        records = fetch_records(chunk)
        years = authoritative_years(list(records))
        for pmid in chunk:
            record = records.get(pmid)
            if not record or not is_complete(record.get("abstract")):
                continue
            if not in_window(years.get(pmid)):
                continue
            found.append(record)
            if len(found) == needed:
                break
    return found, drawn


def main():
    """Replace out-of-window sampled papers and save the updated sample."""
    payload = json.loads(SAMPLE_PATH.read_text())
    papers = payload["papers"]
    dropped = out_of_window_pmids(papers)
    print(f"out-of-window papers to replace: {len(dropped)}")
    kept = [p for p in papers if p["pmid"] not in dropped]

    shuffled = gated_pmids()
    random.Random(RANDOM_SEED).shuffle(shuffled)
    held = {p["pmid"] for p in papers}
    found, drawn = find_replacements(shuffled, payload["n_drawn"], held, len(dropped))
    print(f"replacements found: {len(found)} (walked to {drawn})")

    payload["papers"] = kept + found
    payload["n_drawn"] = drawn
    SAMPLE_PATH.write_text(json.dumps(payload))
    REPLACEMENTS_PATH.write_text(json.dumps(
        {"dropped": sorted(dropped), "added": [p["pmid"] for p in found]}, indent=2))
    print(f"sample now holds {len(payload['papers'])} papers")


if __name__ == "__main__":
    main()
