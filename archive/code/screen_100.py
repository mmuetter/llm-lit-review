#!/usr/bin/env python3
"""
Screen 100 sampled papers with Mistral API.
Uses screen_abstract.py core module.
"""

import json
from pathlib import Path
from screen_abstract import load_api_key, screen_papers, save_markdown_files, print_summary

def main():
    api_key = load_api_key()
    data_dir = Path(__file__).parent.parent / "data"
    screening_dir = data_dir / "screening_100"
    screening_dir.mkdir(exist_ok=True)

    # Load sample
    with open(data_dir / "sample_100_for_screening.json") as f:
        papers = json.load(f)

    checkpoint = screening_dir / "checkpoint.jsonl"

    print(f"Screening {len(papers)} papers...\n")

    # Screen papers
    results = screen_papers(papers, api_key, checkpoint_file=checkpoint)

    # Save markdown files
    print("\nCreating individual paper files...")
    save_markdown_files(results, papers, screening_dir)

    # Save results JSON
    with open(screening_dir / "screening_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    stats = print_summary(results, name="100-paper screening")
    print(f"Results saved to: {screening_dir}")

if __name__ == "__main__":
    main()
