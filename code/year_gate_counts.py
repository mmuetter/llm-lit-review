"""Live per-year gated-paper counts from the six-group v2 gate.

Queried year by year (rather than pooled) so each year's true score>=2 count
matches exactly what sampling.py draws from, unlike the stale pre-v2 files
plot_results.py used to read.
"""

import json
import sys
from pathlib import Path

from pubmed_scoring_open import collect_memberships

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "gated_papers_per_year.json"
FIRST_YEAR = 2010
LAST_YEAR = 2025


def gated_count_for_year(year):
    """Return the number of papers scoring >= 2 in one publication year."""
    memberships, oversized = collect_memberships([year])
    if oversized:
        print(f"  warning: oversized pairs in {year}: {oversized}", file=sys.stderr)
    return len(memberships)


def main():
    """Compute and save the true per-year gated counts."""
    counts = {}
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        counts[year] = gated_count_for_year(year)
        print(f"  {year}: {counts[year]}", file=sys.stderr, flush=True)
    OUTPUT_PATH.write_text(json.dumps(counts, indent=2))
    print(f"wrote {OUTPUT_PATH}")
    print(f"total {sum(counts.values())} over {len(counts)} years")


if __name__ == "__main__":
    main()
