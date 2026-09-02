"""Classify only the new-2025 papers that survived the final 1000-paper draw.

Writes to a separate results directory so the append-only v2 logs
(data/screening_multiverse_v2/) are never touched -- the already-completed
1000-paper v2 screen is reused as-is, not rerun.
"""

import json
import time
from pathlib import Path

import run_screening
from model_clients import build_clients
from prompts import OUTCOME_PROMPTS

DATA_DIR = Path(__file__).parent.parent / "data"
FINAL_MANIFEST_PATH = DATA_DIR / "screening_sample_final.json"
run_screening.RESULTS_DIR = DATA_DIR / "screening_multiverse_2025_ext"


def new_papers():
    """Return the final manifest's papers sourced from the 2025 extension."""
    manifest = json.loads(FINAL_MANIFEST_PATH.read_text())
    return [p for p in manifest["papers"] if p["source"] == "2025"]


def main():
    """Run domain then outcome classification on the new-2025 papers only."""
    papers = new_papers()
    run_screening.banner("2025 EXTENSION SCREEN",
                         f"{len(papers)} new papers | stages: domain, outcome")
    clients = build_clients()
    started = time.monotonic()
    run_screening.run_stage("domain", papers, clients, [run_screening.DOMAIN_TASK])
    run_screening.run_stage("outcome", papers, clients, list(OUTCOME_PROMPTS))
    run_screening.log(f"\nAll stages finished in "
                      f"{run_screening.format_duration(time.monotonic() - started)}")


if __name__ == "__main__":
    main()
