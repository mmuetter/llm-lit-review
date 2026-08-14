#!/usr/bin/env python3
"""
Generate fresh test examples for methodology validation.
Uses screen_abstract.py core module.
"""

import json
import random
from pathlib import Path
from screen_abstract import load_api_key, screen_papers, print_summary

def main():
    api_key = load_api_key()
    data_dir = Path(__file__).parent.parent / "data"
    test_dir = Path(__file__).parent.parent / "test_examples"

    # Load all papers
    with open(data_dir / "pubmed_results_all_years.json") as f:
        all_papers = json.load(f)

    # Randomly sample 10
    random.seed(42)
    papers = random.sample(all_papers, min(10, len(all_papers)))

    print(f"Generating {len(papers)} test examples...\n")

    # Screen papers
    results = screen_papers(papers, api_key)

    # Create detailed markdown files for test examples
    print("\nCreating test example files...")
    papers_by_pmid = {p.get("pmid"): p for p in papers}

    for i, (paper, result) in enumerate(zip(papers, results), 1):
        pmid = result.get("pmid")
        title = paper.get("title", "")
        abstract = paper.get("abstract", "N/A")
        year = paper.get("year", "unknown")

        md_content = f"""# Test Example {i}: PMID {pmid}

## Paper Details
- **Year:** {year}
- **Title:** {title}

## Abstract Length
{len(abstract)} characters

## Raw Abstract

{abstract}

---

## AI Screening Results (Mistral Large)

| Field | Value |
|-------|-------|
| Domain | {result.get('domain', 'ERROR')} |
| Labels as Quality Proxy? | {result.get('labels_as_quality_proxy', 'ERROR')} |
| Num Combinations | {result.get('num_combinations', 'unknown')} |
| Drugs | {result.get('drugs', 'not mentioned')} |
| Num Drugs | {result.get('num_drugs', 'not mentioned')} |
| Focuses on Labels? | {result.get('focuses_on_interaction_labels', 'ERROR')} |
| Abstract Incomplete? | {result.get('abstract_incomplete', 'no')} |
| Cannot Classify? | {result.get('cannot_classify', 'no')} |

---

## Notes for Manual Validation

**Labels as Quality Proxy:** {result.get('labels_as_quality_proxy', 'UNKNOWN').upper()}

According to methodology:
- **YES** = Uses formal interaction labels (Loewe, Bliss, FICI, etc.) AND treats as quality/promise indicator
- **NO** = Focuses on mechanistic understanding, not label classification

**Key Indicators to Check:**
- Does abstract mention formal methods (Loewe, Bliss, FICI, etc.)?
- Does it evaluate labels as quality proxies or mechanistically?
- How many combinations tested (num_combinations)?
"""

        md_file = test_dir / f"example_{i:02d}_PMID_{pmid}.md"
        with open(md_file, "w") as f:
            f.write(md_content)

        synergy_label = result.get('labels_as_quality_proxy', 'unknown').upper()
        incomplete = result.get('abstract_incomplete', 'no').upper()
        print(f"  {i:2d}. example_{i:02d}_PMID_{pmid}.md → labels_as_proxy={synergy_label}, incomplete={incomplete}")

    # Summary
    print_summary(results, name="Test example generation")
    print(f"\nTest examples saved to: {test_dir}")

if __name__ == "__main__":
    main()
