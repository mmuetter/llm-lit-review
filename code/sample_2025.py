"""Draw a calibrated 2025 extension sample without touching the v2 sample.

The v2 run already screened 1000 papers drawn from the 2010-2024 gated pool
(18698 papers). Rather than redraw everything with 2025 folded in -- which
would waste that finished work -- we draw an additional, separately-seeded
sample from the 2025 gated pool only, sized so the combined sample has the
same year composition a single unified draw across 2010-2025 would have:

    K = 1000 * gated_2025 / gated_2010_2024
"""

import json
import random
from pathlib import Path

from pubmed_scoring import PUBMED_TERM_GROUPS
from pubmed_scoring_open import collect_memberships
from sampling import (FETCH_BATCH_SIZE, fetch_records, is_complete)

DATA_DIR = Path(__file__).parent.parent / "data"
V2_SCORES_PATH = DATA_DIR / "term_scores_v2.json"
SCORES_2025_PATH = DATA_DIR / "term_scores_2025.json"
MEMBERSHIPS_2025_PATH = DATA_DIR / "term_memberships_2025.json"
SAMPLE_2025_PATH = DATA_DIR / "screening_sample_2025.json"

YEAR = 2025
BASE_SAMPLE_SIZE = 1000
RANDOM_SEED = 43


def build_2025_gate():
    """Fetch and save the 2025 gated pool (score >= 2), mirroring term_scores_v2."""
    memberships, oversized = collect_memberships([YEAR])
    if oversized:
        raise ValueError(f"oversized pairs need splitting: {oversized}")
    scores = {pmid: len(groups) for pmid, groups in memberships.items()}
    SCORES_2025_PATH.write_text(json.dumps(scores))
    MEMBERSHIPS_2025_PATH.write_text(json.dumps({p: sorted(g) for p, g in memberships.items()}))
    return sorted(scores)


def extension_size(gated_2025_count):
    """Return how many 2025 papers to draw to match proportional representation."""
    gated_2010_2024 = len(json.loads(V2_SCORES_PATH.read_text()))
    return round(BASE_SAMPLE_SIZE * gated_2025_count / gated_2010_2024)


def draw_2025_sample(pmids, target_size):
    """Walk a seeded shuffle of 2025 PMIDs, keeping complete abstracts."""
    shuffled = list(pmids)
    random.Random(RANDOM_SEED).shuffle(shuffled)
    kept, drawn = [], 0
    for start in range(0, len(shuffled), FETCH_BATCH_SIZE):
        chunk = shuffled[start:start + FETCH_BATCH_SIZE]
        records = fetch_records(chunk)
        for pmid in chunk:
            drawn += 1
            record = records.get(pmid)
            if record and is_complete(record.get("abstract")):
                kept.append(record)
            if len(kept) == target_size:
                return kept, drawn
    raise ValueError(f"only {len(kept)} complete abstracts in {len(shuffled)} 2025 gated papers")


def main():
    """Build the 2025 gate, size the extension, draw it, and save it."""
    pmids = build_2025_gate()
    target_size = extension_size(len(pmids))
    print(f"2025 gated pool: {len(pmids)} papers -> drawing {target_size} for the extension")
    papers, n_drawn = draw_2025_sample(pmids, target_size)
    payload = {"seed": RANDOM_SEED, "target_size": target_size, "n_drawn": n_drawn,
               "gate": 2, "year": YEAR, "papers": papers}
    SAMPLE_2025_PATH.write_text(json.dumps(payload))
    print(f"drew {n_drawn} to keep {len(papers)} complete abstracts -> {SAMPLE_2025_PATH}")


if __name__ == "__main__":
    main()
