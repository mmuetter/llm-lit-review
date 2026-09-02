"""Compare candidate stage-1 gate definitions against the one actually used.

Reports how many papers each option admits, how it overlaps the current gated
set, and a sample of titles it newly admits so relevance can be judged.
"""

import json
import random
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CURRENT_SCORES_PATH = DATA_DIR / "pubmed_term_scores.json"
OPEN_SCORES_PATH = DATA_DIR / "pubmed_term_scores_open.json"
MEMBERSHIP_PATH = DATA_DIR / "pubmed_term_memberships_open.json"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

METHOD_GROUPS = {"fici", "checkerboard", "loewe", "bliss", "chou_talalay",
                 "combination_index", "isobologram", "highest_single_agent",
                 "zero_interaction_potency", "musyc", "braid", "concentration_addition"}
CURRENT_GATE = 2
SAMPLE_TITLES = 12
RANDOM_SEED = 42


def load_memberships():
    """Load each scored PMID's matched term groups."""
    return {pmid: set(groups) for pmid, groups in json.loads(MEMBERSHIP_PATH.read_text()).items()}


def current_gated():
    """Return PMIDs admitted by the pipeline as actually run."""
    scores = json.loads(CURRENT_SCORES_PATH.read_text())
    return {pmid for pmid, score in scores.items() if score >= CURRENT_GATE}


def method_count(groups):
    """Count how many matched groups name a specific interaction method."""
    return len(groups & METHOD_GROUPS)


def gate_options(memberships):
    """Define each candidate gate as a predicate over matched groups."""
    return {
        "B open: score >= 2": lambda g: len(g) >= 2,
        "C open: score >= 2 and >= 1 method": lambda g: len(g) >= 2 and method_count(g) >= 1,
        "D open: score >= 3": lambda g: len(g) >= 3,
        "E open: >= 2 methods": lambda g: method_count(g) >= 2,
        "F open: score >= 3 and >= 1 method": lambda g: len(g) >= 3 and method_count(g) >= 1,
    }


def fetch_titles(pmids):
    """Fetch titles for a handful of PMIDs."""
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    with urllib.request.urlopen(f"{ESUMMARY}?{urllib.parse.urlencode(params)}", timeout=60) as r:
        payload = json.load(r)["result"]
    return [payload[p].get("title", "?") for p in pmids if p in payload]


def report_option(name, admitted, current):
    """Print one gate option's size and overlap with the current gate."""
    shared = admitted & current
    print(f"{name:38s} n={len(admitted):7d}  keeps {len(shared):6d} of "
          f"{len(current)}  adds {len(admitted - current):7d}")
    return admitted - current


def main():
    """Compare every candidate gate and sample what the best adds."""
    memberships = load_memberships()
    current = current_gated()
    print(f"current gate (pool AND score >= 2): n={len(current)}\n")
    added = {}
    for name, predicate in gate_options(memberships).items():
        admitted = {pmid for pmid, groups in memberships.items() if predicate(groups)}
        added[name] = report_option(name, admitted, current)
    focus = sys.argv[1] if len(sys.argv) > 1 else "C open: score >= 2 and >= 1 method"
    extra = sorted(added.get(focus, set()))
    if not extra:
        return
    random.Random(RANDOM_SEED).shuffle(extra)
    print(f"\nSample of titles newly admitted by [{focus}]:")
    for title in fetch_titles(extra[:SAMPLE_TITLES]):
        print(f"  - {title[:110]}")


if __name__ == "__main__":
    main()
