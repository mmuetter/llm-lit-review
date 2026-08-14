"""Deterministic completeness filter and seeded sampling of gated papers."""

import json
import random
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CORPUS_PATH = DATA_DIR / "pubmed_results_all_years.json"
TERM_SCORES_PATH = DATA_DIR / "pubmed_term_scores.json"
SAMPLE_PATH = DATA_DIR / "screening_sample.json"

GATE_THRESHOLD = 2
RANDOM_SEED = 42
MINIMUM_ABSTRACT_CHARS = 200
SENTENCE_ENDINGS = ".?!"
OPENING_DELIMITERS = "([{"
TRUNCATED_TAIL = re.compile(r"(\d+\s*[×x]\s*10?|\b[A-Z][a-z]?)$")


def has_balanced_delimiters(abstract):
    """Report whether parentheses and brackets are balanced."""
    depth = abstract.count("(") - abstract.count(")")
    bracket_depth = abstract.count("[") - abstract.count("]")
    return depth == 0 and bracket_depth == 0


def ends_mid_token(abstract):
    """Report whether the abstract stops mid-token or on an open delimiter."""
    if abstract[-1] in OPENING_DELIMITERS:
        return True
    return bool(TRUNCATED_TAIL.search(abstract))


def is_complete(abstract):
    """Report whether an abstract passes every completeness rule."""
    text = (abstract or "").strip()
    if len(text) < MINIMUM_ABSTRACT_CHARS or text[-1] not in SENTENCE_ENDINGS:
        return False
    return has_balanced_delimiters(text) and not ends_mid_token(text[:-1])


def load_gated_papers():
    """Load corpus papers whose term-group score meets the gate."""
    scores = json.loads(TERM_SCORES_PATH.read_text())
    corpus = json.loads(CORPUS_PATH.read_text())
    return [p for p in corpus if scores.get(p["pmid"], 0) >= GATE_THRESHOLD]


def draw_sample(papers, target_size):
    """Walk a seeded shuffle keeping complete abstracts until target_size."""
    shuffled = list(papers)
    random.Random(RANDOM_SEED).shuffle(shuffled)
    kept = []
    for drawn, paper in enumerate(shuffled, start=1):
        if is_complete(paper.get("abstract")):
            kept.append(paper)
        if len(kept) == target_size:
            return kept, drawn
    raise ValueError(f"only {len(kept)} complete abstracts in {len(shuffled)} papers")


def build_sample(target_size):
    """Draw the sample, record how many papers were walked, and save it."""
    papers, n_drawn = draw_sample(load_gated_papers(), target_size)
    payload = {"seed": RANDOM_SEED, "target_size": target_size,
               "n_drawn": n_drawn, "pmids": [p["pmid"] for p in papers]}
    SAMPLE_PATH.write_text(json.dumps(payload, indent=2))
    return papers, payload


def load_sample():
    """Load the saved sample as full paper records, in draw order."""
    payload = json.loads(SAMPLE_PATH.read_text())
    by_pmid = {p["pmid"]: p for p in json.loads(CORPUS_PATH.read_text())}
    return [by_pmid[pmid] for pmid in payload["pmids"]], payload
