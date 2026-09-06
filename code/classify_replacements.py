"""Classify only the papers swapped into the sample, both models, all tasks.

The rest of the grid is untouched: results append to the same checkpoint files,
and the existing cells for retained papers are already complete.
"""

import json
from pathlib import Path

import run_screening
from model_clients import build_clients
from prompts import OUTCOME_PROMPTS
from sampling import SAMPLE_PATH

DATA_DIR = Path(__file__).parent.parent / "data"
REPLACEMENTS_PATH = DATA_DIR / "sample_replacements.json"
run_screening.RESULTS_DIR = DATA_DIR / "screening_final"


def replacement_papers():
    """Return the sampled records for the newly added PMIDs."""
    added = set(json.loads(REPLACEMENTS_PATH.read_text())["added"])
    papers = json.loads(SAMPLE_PATH.read_text())["papers"]
    return [p for p in papers if p["pmid"] in added]


def main():
    """Run domain and outcome classification for the replacements only."""
    papers = replacement_papers()
    clients = build_clients()
    run_screening.banner("REPLACEMENT PAPERS",
                         f"{len(papers)} papers x {len(clients)} models x "
                         f"{1 + len(OUTCOME_PROMPTS)} tasks")
    run_screening.run_stage("domain", papers, clients, [run_screening.DOMAIN_TASK])
    run_screening.run_stage("outcome", papers, clients, list(OUTCOME_PROMPTS))


if __name__ == "__main__":
    main()
