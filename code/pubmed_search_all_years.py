#!/usr/bin/env python3
"""
Search PubMed for all years 2010-2026 by year.
Saves each year's results to data/by_year/YYYY/ folder.
"""

import subprocess
import sys
from pathlib import Path

def main():
    start_year = 2010
    end_year = 2026

    years = list(range(start_year, end_year + 1))
    total_years = len(years)

    print(f"Searching PubMed for {total_years} years ({start_year}-{end_year})...\n")

    results = {}

    for i, year in enumerate(years, 1):
        print(f"[{i}/{total_years}] Searching {year}...")

        try:
            result = subprocess.run(
                ["python3", "code/pubmed_search_by_year.py", str(year)],
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                # Extract paper count from output
                for line in result.stdout.split('\n'):
                    if 'Total papers:' in line:
                        count = int(line.split(':')[1].strip())
                        results[year] = count
                        print(f"  ✓ {count} papers\n")
                        break
            else:
                print(f"  ✗ Error: {result.stderr}\n")
                results[year] = 0

        except subprocess.TimeoutExpired:
            print(f"  ✗ Timeout\n")
            results[year] = 0
        except Exception as e:
            print(f"  ✗ Exception: {e}\n")
            results[year] = 0

    # Summary
    print("\n" + "="*70)
    print("SUMMARY BY YEAR")
    print("="*70)

    total_papers = 0
    for year in years:
        count = results.get(year, 0)
        total_papers += count
        print(f"{year}: {count:5d} papers")

    print("="*70)
    print(f"TOTAL: {total_papers} papers across all years")

    return 0

if __name__ == "__main__":
    sys.exit(main())
