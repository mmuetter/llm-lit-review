"""Resume the clean-restart outcome stage using wave-based dispatch.

Domain is already complete (see data/clean_mistral_run.log). This covers the
outcome grid only, on the already-drawn sample, Mistral only.
"""

from pathlib import Path

import run_screening
from model_clients import MistralClient
from prompts import OUTCOME_PROMPTS
from run_screening import checkpoint_path, load_completed, pending_units
from sampling import load_sample
from wave_dispatch import dispatch_waves

DATA_DIR = Path(__file__).parent.parent / "data"
run_screening.RESULTS_DIR = DATA_DIR / "screening_final"


def main():
    """Dispatch the remaining outcome-stage cells in fast-to-slow waves."""
    papers, _ = load_sample()
    tasks = list(OUTCOME_PROMPTS)
    path = checkpoint_path("outcome")
    completed = load_completed(path)
    units = pending_units(papers, [MistralClient()], tasks, completed)
    run_screening.banner("CLEAN RESTART — outcome (wave dispatch)",
                         f"{len(units)} calls pending, {len(completed)} already done")
    succeeded = dispatch_waves(units, path)
    run_screening.log(f"\n{succeeded}/{len(units)} succeeded across all waves")


if __name__ == "__main__":
    main()
