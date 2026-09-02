"""Classify the final sample with the finalized P2 and P3 prompts, both models.

Writes into the real v2 / 2025-extension result files (split by each paper's
source). P1/P4/P5 are untouched and already complete; this covers exactly the
two tasks that changed.
"""

import json
from pathlib import Path

import run_screening
from analyse_screening import FINAL_MANIFEST_PATH
from model_clients import build_clients

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_DIR_BY_SOURCE = {
    "v2": DATA_DIR / "screening_multiverse_v2",
    "2025": DATA_DIR / "screening_multiverse_2025_ext",
}
TASKS = ["P2_mechanism", "P3_apriori"]


def papers_by_source():
    """Group the final manifest's papers by which draw they came from."""
    manifest = json.loads(FINAL_MANIFEST_PATH.read_text())
    grouped = {"v2": [], "2025": []}
    for paper in manifest["papers"]:
        grouped[paper["source"]].append(paper)
    return grouped


def run_source(source, papers, clients):
    """Run both tasks for one source's papers into its own results file."""
    run_screening.RESULTS_DIR = RESULTS_DIR_BY_SOURCE[source]
    run_screening.banner(f"P2+P3 FINAL — source={source}", f"{len(papers)} papers x 2 models x 2 tasks")
    run_screening.run_stage("outcome", papers, clients, TASKS)


def main():
    """Run the finalized P2 and P3 prompts across both sources and both models."""
    grouped = papers_by_source()
    clients = build_clients()
    for source, papers in grouped.items():
        run_source(source, papers, clients)


if __name__ == "__main__":
    main()
