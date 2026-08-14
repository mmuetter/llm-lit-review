#!/usr/bin/env python3
"""
Screen 900 papers, avoiding already-screened PMIDs.
After completion, merges all results into screening_1010/screening_results.json.
"""

import json
import random
from pathlib import Path
from screen_abstract import load_api_key, screen_papers, save_markdown_files, print_summary

def load_screened_pmids(data_dir):
    screened = set()
    for folder in ['screening_100']:
        p = data_dir / folder / 'screening_results.json'
        if p.exists():
            with open(p) as f:
                for r in json.load(f):
                    if r.get('pmid'):
                        screened.add(r.get('pmid'))
    return screened

def main():
    api_key = load_api_key()
    data_dir = Path(__file__).parent.parent / 'data'

    # Avoid already-screened papers
    already_screened = load_screened_pmids(data_dir)
    print(f"Already screened: {len(already_screened)} papers")

    with open(data_dir / 'pubmed_results_all_years.json') as f:
        all_papers = json.load(f)

    # Pre-filter: only sample from papers with abstracts ≥200 chars
    available = [
        p for p in all_papers
        if p.get('pmid') not in already_screened
        and len(p.get('abstract') or '') >= 200
    ]
    print(f"Available (abstract ≥200 chars, not yet screened): {len(available)} papers\n")

    random.seed(900)
    sample = random.sample(available, min(900, len(available)))

    screening_dir = data_dir / 'screening_900'
    screening_dir.mkdir(exist_ok=True)
    checkpoint = screening_dir / 'checkpoint.jsonl'

    print(f"Screening {len(sample)} papers...\n")
    results = screen_papers(sample, api_key, checkpoint_file=checkpoint)

    with open(screening_dir / 'screening_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print_summary(results, name="900-paper screening")

    # Merge all results into single combined file
    all_results = []
    for folder in ['screening_100', 'screening_900']:
        p = data_dir / folder / 'screening_results.json'
        if p.exists():
            with open(p) as f:
                batch = json.load(f)
            all_results.extend(batch)
            print(f"Loaded {len(batch)} from {folder}")

    combined_dir = data_dir / 'screening_all_results'
    combined_dir.mkdir(exist_ok=True)
    with open(combined_dir / 'screening_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nCombined total: {len(all_results)} papers")
    print_summary(all_results, name="Combined (all batches)")
    print(f"\nCombined results: {combined_dir}/screening_results.json")

if __name__ == '__main__':
    main()
