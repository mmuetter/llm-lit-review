"""Per-year PubMed counts behind the 2025 gated-corpus spike.

Covers the corpus baseline, the six gate term groups, synergy and LLM-marker
vocabulary, MeSH probes, field slices and gate-level record-type splits.
"""

import itertools
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from pubmed_scoring import PUBMED_TERM_GROUPS

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "spike2025_counts.json"
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
FIRST_YEAR = 2010
LAST_YEAR = 2026
NCBI_DELAY_SECONDS = 0.4
REQUEST_TIMEOUT_SECONDS = 120
MAX_RETRIES = 6
RETRY_BACKOFF_SECONDS = 2
YEAR = "{year}"

VOCABULARY = {
    "synergy": "synergy[tiab]",
    "synergistic": "synergistic[tiab]",
    "synergism": "synergism[tiab]",
    "antagonistic": "antagonistic[tiab]",
    "antagonism": "antagonism[tiab]",
    "potentiation": "potentiation[tiab]",
    "additivity": "additivity[tiab]",
    "delve": "delve[tiab] OR delves[tiab] OR delving[tiab]",
    "intricate": "intricate[tiab]",
    "underscore": "underscore[tiab] OR underscores[tiab] OR underscoring[tiab]",
    "pivotal": "pivotal[tiab]",
    "showcasing": "showcase[tiab] OR showcases[tiab] OR showcasing[tiab]",
    "realm": "realm[tiab]",
    "significant": "significant[tiab]",
    "cohort": "cohort[tiab]",
    "randomized": "randomized[tiab]",
    "in_vitro": '"in vitro"[tiab]',
}

PROBES = {
    "mesh_drug_synergism": '"Drug Synergism"[mh]',
    "mesh_drug_combo_therapy": '"Drug Therapy, Combination"[mh]',
    "mesh_drug_antagonism": '"Drug Antagonism"[mh]',
    "synergistic_in_title": "synergistic[ti]",
    "synergistic_and_drug": "synergistic[tiab] AND (drug[tiab] OR antibiotic[tiab] OR chemotherapy[tiab])",
    "synergistic_not_drug": "synergistic[tiab] NOT (drug[tiab] OR antibiotic[tiab] OR chemotherapy[tiab])",
    "synergistic_material": ("synergistic[tiab] AND (nanoparticle*[tiab] OR catalys*[tiab] OR "
                             "composite[tiab] OR hydrogel[tiab] OR photothermal[tiab])"),
    "synergistic_extract": ('synergistic[tiab] AND (extract[tiab] OR "essential oil"[tiab] OR '
                            'phytochemical*[tiab] OR "traditional chinese medicine"[tiab] OR herbal[tiab])'),
}

CORPUS = {
    "pubmed_total": "",
    "pubmed_with_abstract": "hasabstract",
    "pubmed_english_abstract": "hasabstract AND english[la]",
    "pubmed_medline_indexed": "medline[sb]",
    "pubmed_preprints": "preprint[pt]",
}

GATE_SPLITS = {
    "gate_review": "review[pt]",
    "gate_preprint": "preprint[pt]",
}


def gate_query():
    """Return score >= 2 as one query: the union of all term-group pairs."""
    pairs = itertools.combinations(sorted(PUBMED_TERM_GROUPS), 2)
    return " OR ".join(f"(({PUBMED_TERM_GROUPS[first]}) AND ({PUBMED_TERM_GROUPS[second]}))"
                       for first, second in pairs)


def by_publication_year(query):
    """Restrict a query to one publication year."""
    return f'({query}) AND ("{YEAR}"[dp] : "{YEAR}"[dp])'


def by_entry_year(query):
    """Restrict a query to one PubMed entry year."""
    return f'({query}) AND ("{YEAR}/01/01"[edat] : "{YEAR}/12/31"[edat])'


def narrowed(query, restriction):
    """Combine a query with an optional extra restriction."""
    if not restriction:
        return query
    return f"({query}) AND ({restriction})"


def all_series():
    """Map every reported series name to its year-templated query."""
    gate = gate_query()
    series = {name: by_publication_year(narrowed(f'"{YEAR}"[dp]', extra))
              for name, extra in CORPUS.items()}
    series.update({f"group_{name}": by_publication_year(query)
                   for name, query in PUBMED_TERM_GROUPS.items()})
    series.update({f"term_{name}": by_publication_year(query)
                   for name, query in VOCABULARY.items()})
    series.update({name: by_publication_year(query) for name, query in PROBES.items()})
    series.update({name: by_publication_year(narrowed(gate, extra))
                   for name, extra in GATE_SPLITS.items()})
    series["gate_dp"] = by_publication_year(gate)
    series["gate_edat"] = by_entry_year(gate)
    series["gate_notmedline"] = f'({by_publication_year(gate)}) NOT medline[sb]'
    return series


def fetch_count(payload):
    """Post one esearch request and return its record count."""
    with urllib.request.urlopen(ESEARCH_URL, payload, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8", errors="replace")
    return int(json.loads(body)["esearchresult"]["count"])


def count_records(term):
    """Return how many PubMed records match a query, retrying on failure."""
    payload = urllib.parse.urlencode({"db": "pubmed", "term": term,
                                      "retmode": "json", "retmax": 0}).encode()
    for attempt in range(MAX_RETRIES):
        try:
            return fetch_count(payload)
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))


def counts_by_year(template):
    """Count matching records for every year in the window."""
    counts = {}
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        counts[year] = count_records(template.format(year=year))
        time.sleep(NCBI_DELAY_SECONDS)
    return counts


def main():
    """Run every count series and save the table."""
    counts = {}
    for name, template in all_series().items():
        counts[name] = counts_by_year(template)
        print(f"  {name}: {counts[name]}", flush=True)
    OUTPUT_PATH.write_text(json.dumps(counts, indent=1))
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
