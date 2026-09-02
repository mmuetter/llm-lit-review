"""Clean-slate run: fresh sample from the unified 2010-2025 gate, Mistral only.

Draws a single-stage 1000-paper sample directly from the merged gate (no
two-stage patch needed now that term_scores_v2.json already covers 2010-2025),
then runs domain + all five outcome prompts with Mistral only. Sonnet follows
in a second pass after the Mistral results are reviewed.
"""

from pathlib import Path

import run_screening
from model_clients import MistralClient
from prompts import OUTCOME_PROMPTS
from sampling import build_sample

DATA_DIR = Path(__file__).parent.parent / "data"
run_screening.RESULTS_DIR = DATA_DIR / "screening_final"

SAMPLE_SIZE = 1000


def main():
    """Draw a fresh sample and run the full grid on Mistral only."""
    papers, payload = build_sample(SAMPLE_SIZE)
    run_screening.banner("CLEAN RESTART — Mistral only",
                         f"{len(papers)} papers (drew {payload['n_drawn']}, "
                         f"seed {payload['seed']}) from the unified 2010-2025 gate")
    clients = [MistralClient()]
    run_screening.run_stage("domain", papers, clients, [run_screening.DOMAIN_TASK])
    run_screening.run_stage("outcome", papers, clients, list(OUTCOME_PROMPTS))


if __name__ == "__main__":
    main()
