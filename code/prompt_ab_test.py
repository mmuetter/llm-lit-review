"""Minimal A/B test: old single-prompt construct vs new P1_neutral, same papers.

Isolates the prompt-construct effect from the domain-scheme and population
changes, to explain why oncology's yes-rate diverged from antimicrobial's
between the first-version analysis and the current multiverse screen.
"""

import json
import random
from pathlib import Path

from analyse_screening import (FINAL_MANIFEST_PATH, MODELS, load_successful,
                               resolve_domains)
from model_clients import MistralClient

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "prompt_ab_test.json"

SAMPLE_PER_DOMAIN = 30
RANDOM_SEED = 7
DOMAINS = ["oncology", "antimicrobial"]

OLD_PROMPT_TEMPLATE = """Analyze this research paper abstract and extract the following information:

Title: {title}
Abstract: {abstract}

Respond ONLY with this JSON (no other text):
{{
  "domain": "antimicrobial|antiviral|oncology|immunology|anesthesia|
             neurology|ecotoxicology|pest_management|other",
  "labels_as_quality_proxy": "yes|no",
  "abstract_incomplete": "yes|no"
}}

PROTOCOL:
- domain: Classify by the TARGET of the combination study:
  antimicrobial (bacterial/fungal infections), antiviral (viral
  infections), oncology (cancer), immunology (immune conditions),
  anesthesia (sedation/analgesia), neurology (epilepsy, Parkinson's,
  pain, etc.), ecotoxicology (toxic effects on non-target
  organisms/ecosystems), pest_management (combinations targeting pest
  organisms in agricultural context), other (unclear or none of above)
- labels_as_quality_proxy: YES = paper treats synergy as a marker of
  combination quality — either by explicitly claiming synergistic labels
  indicate promise/efficacy, or by screening many combinations implying
  labels identify the most effective ones;
  NO = focuses on mechanistic understanding of why combinations work
  (labels are secondary or not central)
- abstract_incomplete: YES if the abstract reads incomplete and was
  likely cut off. NO if it reads as a coherent complete abstract."""

OLD_SCHEMA = {
    "type": "object",
    "properties": {
        "domain": {"type": "string", "enum": [
            "antimicrobial", "antiviral", "oncology", "immunology", "anesthesia",
            "neurology", "ecotoxicology", "pest_management", "other"]},
        "labels_as_quality_proxy": {"type": "string", "enum": ["yes", "no"]},
        "abstract_incomplete": {"type": "string", "enum": ["yes", "no"]},
    },
    "required": ["domain", "labels_as_quality_proxy", "abstract_incomplete"],
    "additionalProperties": False,
}


def sample_papers_by_domain(resolved, papers_by_pmid):
    """Draw a seeded sample of papers for each domain under the new scheme."""
    rng = random.Random(RANDOM_SEED)
    sampled = {}
    for domain in DOMAINS:
        pmids = sorted(p for p, d in resolved.items() if d == domain)
        rng.shuffle(pmids)
        sampled[domain] = [papers_by_pmid[p] for p in pmids[:SAMPLE_PER_DOMAIN]]
    return sampled


def old_prompt_yes_rate(client, papers):
    """Classify papers with the old single-prompt construct; return yes count and results."""
    results = []
    for paper in papers:
        prompt = OLD_PROMPT_TEMPLATE.format(title=paper["title"], abstract=paper["abstract"])
        result = client.classify(prompt, OLD_SCHEMA)
        results.append({"pmid": paper["pmid"], **result})
    return results


def new_p1_yes_rate(outcome_cells, papers):
    """Look up each paper's already-computed new-scheme P1_neutral (mistral) answer."""
    results = []
    for paper in papers:
        cell = outcome_cells.get((paper["pmid"], "mistral-large-2512", "P1_neutral"))
        if cell:
            results.append({"pmid": paper["pmid"], "synergy_desirable": cell["synergy_desirable"]})
    return results


def summarise(label, results, key):
    """Print the yes-rate for one set of classification results."""
    total = len(results)
    yes = sum(1 for r in results if r[key] == "yes")
    print(f"  {label}: {yes}/{total} = {100 * yes / total:.1f}% yes")
    return yes, total


def main():
    """Run the A/B test and report old-vs-new yes-rates per domain."""
    manifest = json.loads(FINAL_MANIFEST_PATH.read_text())
    papers_by_pmid = {p["pmid"]: p for p in manifest["papers"]}
    domain_cells = load_successful("domain")
    outcome_cells = load_successful("outcome")
    pmids = list(papers_by_pmid)
    resolved = resolve_domains(domain_cells, pmids)

    sampled = sample_papers_by_domain(resolved, papers_by_pmid)
    client = MistralClient()

    report = {}
    for domain in DOMAINS:
        papers = sampled[domain]
        print(f"\n=== {domain} (n={len(papers)}) ===")
        old_results = old_prompt_yes_rate(client, papers)
        new_results = new_p1_yes_rate(outcome_cells, papers)
        old_yes, old_total = summarise("old single-prompt", old_results, "labels_as_quality_proxy")
        new_yes, new_total = summarise("new P1_neutral    ", new_results, "synergy_desirable")
        report[domain] = {"old": old_results, "new": new_results,
                          "old_rate": old_yes / old_total, "new_rate": new_yes / new_total}

    OUTPUT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nwrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
