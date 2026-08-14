#!/usr/bin/env python3
"""
Screen 100 random papers (validation set).
Avoids papers already screened.
Tracks sampled PMIDs to avoid resampling.
"""

import json
import random
from pathlib import Path
from screen_abstract import load_api_key, screen_papers, print_summary

def main():
    api_key = load_api_key()
    data_dir = Path(__file__).parent.parent / "data"

    # Papers already screened
    already_screened = {
        '40401399', '24520095', '21865116', '41531068', '31029959',
        '29356379', '30125561', '25734622', '41596714', '24928110'
    }

    # Load all papers
    with open(data_dir / "pubmed_results_all_years.json") as f:
        all_papers = json.load(f)

    # Filter out already screened
    available_papers = [p for p in all_papers if p.get('pmid') not in already_screened]

    print(f"Available papers: {len(available_papers)} (excluding {len(already_screened)} already screened)\n")

    # Sample 100
    random.seed(100)
    sample_papers = random.sample(available_papers, min(100, len(available_papers)))

    sampled_pmids = [p.get('pmid') for p in sample_papers]

    print(f"Screening {len(sample_papers)} papers...\n")

    # Screen with Mistral
    results = screen_papers(sample_papers, api_key)

    # Save results
    screening_dir = data_dir / "screening_100_validation"
    screening_dir.mkdir(exist_ok=True)

    with open(screening_dir / "screening_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Track sampled PMIDs for next run
    with open(screening_dir / "sampled_pmids.txt", "w") as f:
        for pmid in sampled_pmids:
            f.write(pmid + "\n")

    # Summary
    print_summary(results, name="100-paper validation")
    print(f"Results: {screening_dir}/screening_results.json")
    print(f"PMIDs tracked: {screening_dir}/sampled_pmids.txt")

if __name__ == "__main__":
    main()
