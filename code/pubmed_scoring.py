"""Score papers by how many interaction-terminology groups PubMed matches them on.

Each term group is issued as its own PubMed query, so a paper can match through
abstract text, title, author keywords or MeSH indexing.
"""

import json
import time
import urllib.parse
import urllib.request

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_DELAY_SECONDS = 0.4
ESEARCH_PAGE_SIZE = 9999
ESEARCH_RETRIEVAL_LIMIT = 9999

PUBMED_TERM_GROUPS = {
    "synergy": "synergism OR synergistic OR synergy",
    "antagonism": "antagonism OR antagonistic",
    "additivity": "additive OR additivity OR indifference",
    "drug_interaction": '"drug interactions" OR "drug combination" OR "pairwise interaction" OR "interaction network"',
    "fici": 'FICI[tiab] OR "fractional inhibitory concentration"[tiab] OR "FIC index"[tiab]',
    "checkerboard": "checkerboard[tiab]",
    "loewe": "Loewe[tiab]",
    "bliss": "Bliss[tiab]",
    "chou_talalay": '"Chou-Talalay"[tiab] OR "Chou Talalay"[tiab]',
    "combination_index": '"combination index"[tiab]',
    "isobologram": "isobologram[tiab] OR isobolographic[tiab] OR isobole[tiab]",
    "highest_single_agent": '"highest single agent"[tiab]',
    "zero_interaction_potency": '"zero interaction potency"[tiab] OR "ZIP score"[tiab]',
    "musyc": "MuSyC[tiab]",
    "braid": "BRAID[tiab]",
    "concentration_addition": '"concentration addition"[tiab] OR "independent action"[tiab]',
}


def esearch_page(term, retstart, retmax):
    """Run one page of a PubMed search and return its result payload."""
    params = {"db": "pubmed", "term": term, "retmode": "json",
              "retstart": retstart, "retmax": retmax}
    url = f"{EUTILS_BASE}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=120) as response:
        body = response.read().decode("utf-8", errors="replace")
    return json.loads(body, strict=False)["esearchresult"]


def esearch_count(term):
    """Return the total number of PubMed records matching a query."""
    return int(esearch_page(term, retstart=0, retmax=0)["count"])


def esearch(term, retmax=None):
    """Run a PubMed search and return all matching PMIDs, paginating as needed."""
    total = retmax if retmax else esearch_count(term)
    if total > ESEARCH_RETRIEVAL_LIMIT:
        raise ValueError(f"{total} records exceeds the PubMed retrieval limit; split the query")
    collected = set()
    for retstart in range(0, total, ESEARCH_PAGE_SIZE):
        collected.update(esearch_page(term, retstart, ESEARCH_PAGE_SIZE)["idlist"])
        time.sleep(NCBI_DELAY_SECONDS)
    return collected


def year_filtered(query, year):
    """Restrict a PubMed query to a single publication year."""
    return f'({query}) AND ("{year}"[dp] : "{year}"[dp])'


def collect_group_pmids(base_query, group_query, years):
    """Collect PMIDs matching one term group across the given years."""
    collected = set()
    for year in years:
        collected.update(esearch(year_filtered(f"({base_query}) AND ({group_query})", year)))
    return collected


def restrict_to_pmid(pmid, group_query):
    """Build a query testing whether one PMID matches a term group."""
    return f"{pmid}[uid] AND ({group_query})"


def matched_groups_for_pmid(pmid):
    """List the term groups PubMed matches a single PMID on."""
    matched = []
    for name, group_query in PUBMED_TERM_GROUPS.items():
        if esearch(restrict_to_pmid(pmid, group_query), retmax=1):
            matched.append(name)
        time.sleep(NCBI_DELAY_SECONDS)
    return matched


def pmids_by_term_group(base_query, years):
    """Map each term group to the PMIDs matching it, searched year by year."""
    return {
        name: collect_group_pmids(base_query, group_query, years)
        for name, group_query in PUBMED_TERM_GROUPS.items()
    }


def score_pmids(group_to_pmids):
    """Count how many term groups each PMID matched."""
    scores = {}
    for pmids in group_to_pmids.values():
        for pmid in pmids:
            scores[pmid] = scores.get(pmid, 0) + 1
    return scores
