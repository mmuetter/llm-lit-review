"""Preview run: classify the final sample with only the new P2 prompt.

Writes to a separate, disposable results directory so it never touches the
real v2 / 2025-extension logs -- this is just to see how the new P2 behaves
before the user's planned full rerun.
"""

import json
from pathlib import Path

import run_screening
from analyse_screening import FINAL_MANIFEST_PATH
from model_clients import build_clients

DATA_DIR = Path(__file__).parent.parent / "data"
run_screening.RESULTS_DIR = DATA_DIR / "p2_preview"

TASK = "P2_mechanism"


def final_sample_papers():
    """Return every paper in the final reported sample."""
    return json.loads(FINAL_MANIFEST_PATH.read_text())["papers"]


def report_rates():
    """Print the yes-rate for the new P2 prompt, per model."""
    path = run_screening.RESULTS_DIR / "outcome.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    by_model = {}
    for r in records:
        if "result" not in r:
            continue
        by_model.setdefault(r["model"], []).append(r["result"]["synergy_desirable"])
    for model, answers in by_model.items():
        yes = sum(1 for a in answers if a == "yes")
        print(f"  {model}: {yes}/{len(answers)} = {100 * yes / len(answers):.1f}% yes")


def main():
    """Run the P2-only preview and report the resulting yes-rate."""
    papers = final_sample_papers()
    clients = build_clients()
    run_screening.banner("P2 PREVIEW", f"{len(papers)} papers x 1 prompt x 2 models")
    run_screening.run_stage("outcome", papers, clients, [TASK])
    report_rates()


if __name__ == "__main__":
    main()
