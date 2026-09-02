"""Complete the clean-restart grid with Sonnet, on the exact same sample.

Domain + all five outcome prompts, writing into the same screening_final/
results the Mistral pass already populated (records are keyed by model, so
both models' cells coexist in the same files).
"""

from pathlib import Path

import run_screening
from model_clients import AnthropicClient
from prompts import OUTCOME_PROMPTS
from sampling import load_sample

DATA_DIR = Path(__file__).parent.parent / "data"
run_screening.RESULTS_DIR = DATA_DIR / "screening_final"


def main():
    """Run domain + outcome stages for Sonnet on the fixed clean-restart sample."""
    papers, payload = load_sample()
    run_screening.banner("CLEAN RESTART — Sonnet",
                         f"{len(papers)} papers (seed {payload['seed']}) from the unified 2010-2025 gate")
    clients = [AnthropicClient()]
    run_screening.run_stage("domain", papers, clients, [run_screening.DOMAIN_TASK])
    run_screening.run_stage("outcome", papers, clients, list(OUTCOME_PROMPTS))


if __name__ == "__main__":
    main()
