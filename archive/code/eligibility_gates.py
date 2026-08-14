"""Compare stage-1 eligibility gates: MeSH descriptors vs. term-group scoring.

Reports the score distribution over the corpus, MeSH coverage on a random
sample, and how both gates treat a known mechanistic reference paper.
"""

import json
import random
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CORPUS_PATH = DATA_DIR / "pubmed_results_all_years.json"
FIRST_INCLUDED_YEAR = 2010
LAST_INCLUDED_YEAR = 2025
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MESH_BATCH_SIZE = 150
NCBI_DELAY_SECONDS = 0.4
MESH_SAMPLE_SIZE = 400
RANDOM_SEED = 42
SCORE_THRESHOLDS = range(1, 7)

ELIGIBLE_MESH_TERMS = {"Drug Synergism", "Drug Antagonism", "Drug Interactions"}

TERM_GROUP_PATTERNS = {
    "synergy": r"synerg\w*",
    "antagonism": r"antagonis\w*",
    "additivity": r"additiv\w*|indifferen\w*",
    "drug_interaction": r"drug[- ]interaction\w*|drug[- ]combination\w*|pairwise interaction\w*|interaction network",
    "fici": r"FICI|FIC index|fractional inhibitory",
    "checkerboard": r"checkerboard",
    "loewe": r"Loewe",
    "bliss": r"Bliss",
    "chou_talalay": r"Chou[- ]Talalay",
    "combination_index": r"combination index",
    "isobologram": r"isobolo\w*",
    "highest_single_agent": r"highest single agent|HSA model",
    "zip": r"ZIP score|zero interaction potency",
    "musyc": r"MuSyC",
    "braid": r"BRAID",
    "concentration_addition": r"concentration addition|independent action",
}

COMPILED_TERM_GROUPS = {
    name: re.compile(pattern, re.I) for name, pattern in TERM_GROUP_PATTERNS.items()
}

REFERENCE_TITLE = "Functional classification of drugs by properties of their pairwise interactions"

REFERENCE_ABSTRACT = """Multidrug treatments are increasingly important in medicine and for probing
biological systems. Although many studies have focused on interactions between specific drugs,
little is known about the system properties of a full drug interaction network. Like their genetic
counterparts, two drugs may have no interaction, or they may interact synergistically or
antagonistically to increase or suppress their individual effects. Here we use a sensitive
bioluminescence technique to provide quantitative measurements of pairwise interactions among 21
antibiotics that affect growth rate in Escherichia coli. We find that the drug interaction network
possesses a special property: it can be separated into classes of drugs such that any two classes
interact either purely synergistically or purely antagonistically. These classes correspond directly
to the cellular functions affected by the drugs. This network approach provides a new conceptual
framework for understanding the functional mechanisms of drugs and their cellular targets and can be
applied in systems intractable to mutant screening, biochemistry or microscopy."""


def matched_term_groups(abstract):
    """List the interaction-terminology groups present in an abstract."""
    if not abstract:
        return []
    return [name for name, matcher in COMPILED_TERM_GROUPS.items() if matcher.search(abstract)]


def term_group_score(abstract):
    """Count distinct interaction-terminology groups present in an abstract."""
    return len(matched_term_groups(abstract))


def publication_year(record):
    """Return a record's publication year as an integer, or None."""
    try:
        return int(record["year"])
    except (KeyError, TypeError, ValueError):
        return None


def load_corpus():
    """Load corpus records restricted to the included publication years."""
    with open(CORPUS_PATH) as handle:
        records = json.load(handle)
    in_window = lambda year: year is not None and FIRST_INCLUDED_YEAR <= year <= LAST_INCLUDED_YEAR
    return [record for record in records if in_window(publication_year(record))]


def fetch_url(endpoint, params):
    """Fetch an NCBI E-utilities endpoint and return the raw response."""
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{EUTILS_BASE}/{endpoint}?{query}", timeout=90) as response:
        return response.read()


def article_pmid(article):
    """Extract the PMID from a PubmedArticle element."""
    node = article.find("./MedlineCitation/PMID")
    return node.text if node is not None else None


def article_mesh_terms(article):
    """Extract MeSH descriptor names from a PubmedArticle element."""
    return {node.text for node in article.iter("DescriptorName") if node.text}


def fetch_mesh_batch(pmids):
    """Fetch MeSH descriptors for one batch of PMIDs."""
    payload = fetch_url("efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
    root = ET.fromstring(payload)
    return {article_pmid(a): article_mesh_terms(a) for a in root.iter("PubmedArticle")}


def fetch_mesh_terms(pmids):
    """Fetch MeSH descriptors for many PMIDs in batches."""
    collected = {}
    for start in range(0, len(pmids), MESH_BATCH_SIZE):
        collected.update(fetch_mesh_batch(pmids[start:start + MESH_BATCH_SIZE]))
        time.sleep(NCBI_DELAY_SECONDS)
    return collected


def search_first_pmid(title):
    """Return the first PMID matching a title query."""
    payload = fetch_url("esearch.fcgi", {"db": "pubmed", "term": title, "retmode": "json"})
    identifiers = json.loads(payload)["esearchresult"]["idlist"]
    return identifiers[0] if identifiers else None


def has_eligible_mesh(mesh_terms):
    """Report whether a MeSH descriptor set marks a paper as interaction-related."""
    return bool(mesh_terms & ELIGIBLE_MESH_TERMS)


def report_score_distribution(records):
    """Print how many corpus records reach each term-group score threshold."""
    scores = Counter(term_group_score(record.get("abstract")) for record in records)
    total = len(records)
    print(f"\nTerm-group score distribution ({total} papers, {FIRST_INCLUDED_YEAR}-{LAST_INCLUDED_YEAR}):")
    for threshold in SCORE_THRESHOLDS:
        passing = sum(count for score, count in scores.items() if score >= threshold)
        print(f"  score >= {threshold}: {passing:6d} ({100 * passing / total:5.1f}%)")


def report_reference_paper():
    """Print how both gates treat the mechanistic reference paper."""
    groups = matched_term_groups(REFERENCE_ABSTRACT)
    print(f"\nReference paper (Yeh/Kishony) term groups: {groups}")
    print(f"  term-group score: {len(groups)}")
    pmid = search_first_pmid(REFERENCE_TITLE)
    if not pmid:
        print("  PubMed lookup failed")
        return
    mesh = fetch_mesh_terms([pmid]).get(pmid, set())
    print(f"  PMID {pmid} | eligible MeSH: {has_eligible_mesh(mesh)}")
    print(f"  matched MeSH: {sorted(mesh & ELIGIBLE_MESH_TERMS)}")


def report_mesh_coverage(records):
    """Print MeSH gate coverage and its agreement with the score gate."""
    random.seed(RANDOM_SEED)
    sample = random.sample(records, min(MESH_SAMPLE_SIZE, len(records)))
    mesh_by_pmid = fetch_mesh_terms([record["pmid"] for record in sample])
    rows = [(record, mesh_by_pmid.get(record["pmid"], set())) for record in sample]
    print_gate_agreement(rows)
    print_mesh_by_year(rows)


def print_gate_agreement(rows):
    """Print the cross-tabulation of the MeSH gate against the score gate."""
    counts = Counter(
        (has_eligible_mesh(mesh), term_group_score(record.get("abstract")) >= 3)
        for record, mesh in rows
    )
    print(f"\nGate agreement on {len(rows)} sampled papers (MeSH vs. score>=3):")
    for mesh_pass in (True, False):
        for score_pass in (True, False):
            print(f"  mesh={mesh_pass!s:5} score={score_pass!s:5}: {counts[(mesh_pass, score_pass)]:4d}")


def print_mesh_by_year(rows):
    """Print MeSH indexing coverage per publication year."""
    totals, indexed = Counter(), Counter()
    for record, mesh in rows:
        totals[publication_year(record)] += 1
        indexed[publication_year(record)] += bool(mesh)
    print("\nMeSH indexing coverage by year (any descriptor present):")
    for year in sorted(totals):
        print(f"  {year}: {indexed[year]:3d}/{totals[year]:3d}")


def main():
    """Run the eligibility-gate comparison."""
    records = load_corpus()
    report_score_distribution(records)
    report_reference_paper()
    report_mesh_coverage(records)


if __name__ == "__main__":
    main()
