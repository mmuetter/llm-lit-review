"""Fast Sonnet-only loop for tuning the P2 wording on a fixed 100-paper set.

Sonnet has no rate-limit throttle, so this is quick to re-run after each
wording change -- meant for iterating before committing to a full preview.
"""

import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from analyse_screening import FINAL_MANIFEST_PATH
from model_clients import MistralClient
from prompts import OUTCOME_SCHEMA, SCOPE_GUARD, paper_block

SAMPLE_SIZE = 100
RANDOM_SEED = 11


def test_set():
    """Draw a fixed, seeded 100-paper subset of the final sample."""
    papers = json.loads(FINAL_MANIFEST_PATH.read_text())["papers"]
    shuffled = sorted(papers, key=lambda p: p["pmid"])
    random.Random(RANDOM_SEED).shuffle(shuffled)
    return shuffled[:SAMPLE_SIZE]


def classify_one(client, paper, candidate_text):
    """Classify one paper with a candidate P2 wording."""
    prompt = f"{paper_block(paper)}\n\n{SCOPE_GUARD}\n\n{candidate_text}"
    try:
        result = client.classify(prompt, OUTCOME_SCHEMA)
        return {"pmid": paper["pmid"], "synergy_desirable": result["synergy_desirable"]}
    except Exception as error:
        return {"pmid": paper["pmid"], "error": f"{type(error).__name__}: {error}"}


def run_candidate(label, candidate_text, papers):
    """Classify every paper with one candidate wording and report the yes-rate."""
    client = MistralClient()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda p: classify_one(client, p, candidate_text), papers))
    errors = [r for r in results if "error" in r]
    answered = [r for r in results if "synergy_desirable" in r]
    yes = sum(1 for r in answered if r["synergy_desirable"] == "yes")
    print(f"  {label}: {yes}/{len(answered)} = {100 * yes / len(answered):.1f}% yes "
          f"({len(errors)} errors)")
    return results


if __name__ == "__main__":
    print("Use this module's run_candidate(label, text, test_set()) from a driver script.")
