"""Combine the v2 sample and the 2025 extension into one final 1000-paper draw.

Draws once, uniformly, from the union of the already-screened 1000 papers and
the newly drawn 2025 candidates. Old papers that lose this draw are simply
dropped from the reported sample; their already-computed results are just
unused, not wasted work. New papers that win it are the only ones that still
need classifying.
"""

import json
import random
from pathlib import Path

from sampling import load_sample

DATA_DIR = Path(__file__).parent.parent / "data"
CANDIDATES_2025_PATH = DATA_DIR / "screening_sample_2025.json"
FINAL_MANIFEST_PATH = DATA_DIR / "screening_sample_final.json"

FINAL_SAMPLE_SIZE = 1000
RANDOM_SEED = 44


def tagged_papers(papers, source):
    """Attach a source tag to each paper record."""
    return [{**p, "source": source} for p in papers]


def load_candidate_pool():
    """Load the v2 sample and the 2025 candidates as one tagged pool."""
    v2_papers, _ = load_sample()
    extension = json.loads(CANDIDATES_2025_PATH.read_text())
    return tagged_papers(v2_papers, "v2") + tagged_papers(extension["papers"], "2025")


def draw_final_sample(pool):
    """Uniformly draw the final reported sample from the combined pool."""
    shuffled = list(pool)
    random.Random(RANDOM_SEED).shuffle(shuffled)
    return shuffled[:FINAL_SAMPLE_SIZE]


def main():
    """Build and save the final 1000-paper manifest."""
    pool = load_candidate_pool()
    final = draw_final_sample(pool)
    by_source = {"v2": 0, "2025": 0}
    for paper in final:
        by_source[paper["source"]] += 1
    payload = {"seed": RANDOM_SEED, "pool_size": len(pool),
               "final_size": len(final), "by_source": by_source, "papers": final}
    FINAL_MANIFEST_PATH.write_text(json.dumps(payload))
    print(f"pool {len(pool)} (1000 v2 + {len(pool) - 1000} new 2025) "
          f"-> final {len(final)}: {by_source}")
    print(f"wrote {FINAL_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
