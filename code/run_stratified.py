"""Classify the stratified sample with one model, domain and outcome stages.

Usage: python run_stratified.py mistral|sonnet
Mistral is dispatched in fast-to-slow waves, Sonnet through the standard
stage runner. Cells append to screening_v3/, so any restart resumes.
"""

import sys
from pathlib import Path

import run_screening
from model_clients import AnthropicClient, MistralClient
from prompts import OUTCOME_PROMPTS
from run_screening import DOMAIN_TASK, checkpoint_path, load_completed, pending_units
from sampling import load_stratified_sample
from wave_dispatch import dispatch_waves

DATA_DIR = Path(__file__).parent.parent / "data"
run_screening.RESULTS_DIR = DATA_DIR / "screening_v3"
STAGE_TASKS = {"domain": [DOMAIN_TASK], "outcome": list(OUTCOME_PROMPTS)}
USAGE = "usage: python run_stratified.py mistral|sonnet"


def run_mistral(papers):
    """Dispatch each stage's pending Mistral cells in waves."""
    for stage, tasks in STAGE_TASKS.items():
        path = checkpoint_path(stage)
        units = pending_units(papers, [MistralClient()], tasks, load_completed(path))
        run_screening.banner(f"STRATIFIED - Mistral {stage}", f"{len(units)} calls pending")
        succeeded = dispatch_waves(units, path)
        run_screening.log(f"\n{succeeded}/{len(units)} {stage} cells succeeded")


def run_sonnet(papers):
    """Run each stage for Sonnet through the standard stage runner."""
    clients = [AnthropicClient()]
    for stage, tasks in STAGE_TASKS.items():
        run_screening.run_stage(stage, papers, clients, tasks)


RUNNERS = {"mistral": run_mistral, "sonnet": run_sonnet}


def main():
    """Run the requested model over the stratified sample."""
    model = sys.argv[1] if len(sys.argv) > 1 else ""
    if model not in RUNNERS:
        sys.exit(USAGE)
    papers, strata = load_stratified_sample()
    run_screening.banner(f"STRATIFIED SAMPLE - {model}",
                         f"{len(papers)} papers across scores {sorted(strata)}")
    RUNNERS[model](papers)


if __name__ == "__main__":
    main()
