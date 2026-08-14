#!/usr/bin/env python3
"""
Sample n papers randomly from aggregated dataset.
Papers are sampled across years uniformly.
"""

import json
import random
from pathlib import Path
import sys

def main():
    if len(sys.argv) < 2:
        n = 100
    else:
        n = int(sys.argv[1])

    data_dir = Path(__file__).parent.parent / "data"
    aggregated_file = data_dir / "pubmed_results_all_years.json"

    if not aggregated_file.exists():
        print(f"Error: {aggregated_file} not found")
        return 1

    with open(aggregated_file) as f:
        all_papers = json.load(f)

    print(f"Dataset has {len(all_papers)} papers")
    print(f"Sampling {n} papers randomly...")

    # Sample n papers randomly
    sampled = random.sample(all_papers, min(n, len(all_papers)))

    # Save sample
    sample_file = data_dir / f"sample_{n}_for_screening.json"
    with open(sample_file, "w") as f:
        json.dump(sampled, f, indent=2)

    print(f"✓ Saved {len(sampled)} papers to {sample_file}")

    # Summary by year
    from collections import Counter
    years = Counter(p.get('year') for p in sampled if p.get('year'))

    print(f"\nSample distribution by year:")
    for year in sorted(years.keys()):
        print(f"  {year}: {years[year]}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
