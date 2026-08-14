#!/usr/bin/env python3
"""
Aggregate PubMed search results from all years (2010-2026).
Creates master dataset and generates statistics by year.
"""

import json
from pathlib import Path
from collections import Counter

def main():
    data_dir = Path(__file__).parent.parent / "data"
    by_year_dir = data_dir / "by_year"

    # Find all year folders
    year_folders = sorted([d for d in by_year_dir.iterdir() if d.is_dir()])

    print(f"Aggregating results from {len(year_folders)} years...\n")

    all_papers = []
    papers_by_year = {}
    total_by_year = Counter()

    for year_folder in year_folders:
        year = year_folder.name
        results_file = year_folder / f"pubmed_results_{year}.json"

        if results_file.exists():
            with open(results_file) as f:
                papers = json.load(f)

            all_papers.extend(papers)
            papers_by_year[year] = papers
            total_by_year[year] = len(papers)

            print(f"{year}: {len(papers):5d} papers")
        else:
            print(f"{year}: (no results file yet)")

    # Save aggregated results
    master_file = data_dir / "pubmed_results_all_years.json"
    with open(master_file, "w") as f:
        json.dump(all_papers, f, indent=2)

    print(f"\n{'='*70}")
    print(f"✓ Aggregated {len(all_papers)} papers total")
    print(f"  Saved to: {master_file}")

    # Statistics
    with_abstract = sum(1 for p in all_papers if p.get('abstract') and str(p.get('abstract')).strip())
    print(f"\nStatistics:")
    print(f"  Papers with abstract: {with_abstract} ({100*with_abstract/len(all_papers):.1f}%)")

    # Year-by-year breakdown
    print(f"\nPapers by year:")
    print(f"{'Year':<6} {'Count':<8} Bar")
    print("-" * 50)

    for year in sorted(total_by_year.keys()):
        count = total_by_year[year]
        bar_width = max(1, count // 50)  # Scale for visualization
        bar = "█" * bar_width
        print(f"{year:<6} {count:<8} {bar}")

    # Check for key papers
    print(f"\n{'='*70}")
    print("Verification - checking for key papers:")

    yu_pmid = '26729502'
    if any(p.get('pmid') == yu_pmid for p in all_papers):
        paper = next(p for p in all_papers if p.get('pmid') == yu_pmid)
        print(f"✓ Yu/Regoes paper (PMID {yu_pmid}): {paper.get('title')[:60]}")
    else:
        print(f"✗ Yu/Regoes paper (PMID {yu_pmid}): NOT FOUND")

    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()
