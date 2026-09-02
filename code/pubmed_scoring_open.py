"""Score papers by indicator-term groups without a separate candidate pool.

Score >= 2 is exactly the union of pairwise group intersections, so the gated
set and every paper's group membership can be built from pair queries alone --
avoiding the retrieval limit that makes the broad groups unqueryable directly.
"""

import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

from pubmed_scoring import PUBMED_TERM_GROUPS, esearch, esearch_count, year_filtered

DATA_DIR = Path(__file__).parent.parent / "data"
OPEN_SCORES_PATH = DATA_DIR / "pubmed_term_scores_open.json"
MEMBERSHIP_PATH = DATA_DIR / "pubmed_term_memberships_open.json"
FIRST_YEAR = 2010
LAST_YEAR = 2024
RETRIEVAL_LIMIT = 9999


def pair_query(first, second):
    """Build the query matching papers in both term groups."""
    return f"({PUBMED_TERM_GROUPS[first]}) AND ({PUBMED_TERM_GROUPS[second]})"


def group_pairs():
    """Return every unordered pair of term groups."""
    return list(itertools.combinations(sorted(PUBMED_TERM_GROUPS), 2))


def pair_pmids(first, second, year):
    """Return PMIDs matching both groups in one year, or None if too many."""
    query = year_filtered(pair_query(first, second), year)
    if esearch_count(query) > RETRIEVAL_LIMIT:
        return None
    return esearch(query)


def collect_memberships(years):
    """Map each PMID with score >= 2 to the groups it matches."""
    memberships = defaultdict(set)
    oversized = []
    pairs = group_pairs()
    for index, (first, second) in enumerate(pairs, start=1):
        for year in years:
            pmids = pair_pmids(first, second, year)
            if pmids is None:
                oversized.append((first, second, year))
                continue
            for pmid in pmids:
                memberships[pmid].update((first, second))
        print(f"  [{index}/{len(pairs)}] {first} x {second}: "
              f"{len(memberships)} papers so far", file=sys.stderr, flush=True)
    return memberships, oversized


def main():
    """Build the pool-free score table and save it."""
    years = range(FIRST_YEAR, LAST_YEAR + 1)
    memberships, oversized = collect_memberships(years)
    scores = {pmid: len(groups) for pmid, groups in memberships.items()}
    OPEN_SCORES_PATH.write_text(json.dumps(scores))
    MEMBERSHIP_PATH.write_text(json.dumps({p: sorted(g) for p, g in memberships.items()}))
    print(f"\npapers with score >= 2: {len(scores)}")
    if oversized:
        print(f"pairs exceeding the retrieval limit: {len(oversized)}")
        for entry in oversized[:5]:
            print(f"  {entry}")


if __name__ == "__main__":
    main()
