#!/usr/bin/env python3
"""
Screen 10 random papers with Mistral API.
Uses screen_abstract.py core module.
"""

import json
import random
from pathlib import Path
from screen_abstract import load_api_key, screen_papers, save_markdown_files, print_summary

def main():
    api_key = load_api_key()
    data_dir = Path(__file__).parent.parent / "data"
    screening_dir = data_dir / "screening_10"
    screening_dir.mkdir(exist_ok=True)

    # Load all papers
    with open(data_dir / "pubmed_results_all_years.json") as f:
        all_papers = json.load(f)

    # Randomly sample 10
    random.seed(42)
    papers = random.sample(all_papers, min(10, len(all_papers)))

    print(f"Screening {len(papers)} papers...\n")

    # Screen papers
    results = screen_papers(papers, api_key)

    # Save markdown files
    print("\nCreating individual paper files...")
    save_markdown_files(results, papers, screening_dir)

    # Save results JSON
    with open(screening_dir / "screening_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    stats = print_summary(results, name="10-paper screening")
    print(f"Results saved to: {screening_dir}")

if __name__ == "__main__":
    main()
