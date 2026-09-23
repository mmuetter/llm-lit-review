"""Deterministic completeness filter and seeded simple random sample of the pool.

The pool is every in-window paper whose title or abstract uses a synerg* word
(see synergy_gate.py). Records are fetched fresh from PubMed while walking a
seeded shuffle, keeping complete abstracts until the target size is reached.
"""

import json
import random
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
ELIGIBLE_YEARS_PATH = DATA_DIR / "synerg_paper_years.json"
SAMPLE_PATH = DATA_DIR / "screening_sample_v5.json"
SAMPLE_SIZE = 1000

FIRST_YEAR = 2010
LAST_YEAR = 2025
RANDOM_SEED = 42
MINIMUM_ABSTRACT_CHARS = 200
SENTENCE_ENDINGS = ".?!"
OPENING_DELIMITERS = "([{"
TRUNCATED_TAIL = re.compile(r"(\d+\s*[×x]\s*10?|\b[A-Z][a-z]?)$")

EUTILS_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
FETCH_BATCH_SIZE = 150
NCBI_DELAY_SECONDS = 0.4


def has_balanced_delimiters(abstract):
    """Report whether parentheses and brackets are balanced."""
    return (abstract.count("(") == abstract.count(")")
            and abstract.count("[") == abstract.count("]"))


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


def element_text(node):
    """Return an element's complete text, including any nested markup."""
    return "".join(node.itertext()) if node is not None else ""


def leading_year(stamp):
    """Return the four-digit year a date string starts with, if any."""
    match = re.match(r"\s*(\d{4})", stamp or "")
    return int(match.group(1)) if match else None


def publication_year(article):
    """Return the later of an article's print and electronic publication years."""
    stamps = [article.findtext(".//JournalIssue/PubDate/Year"),
              article.findtext(".//JournalIssue/PubDate/MedlineDate")]
    stamps += [date.findtext("Year") for date in article.findall(".//ArticleDate")]
    years = [year for year in map(leading_year, stamps) if year]
    return str(max(years)) if years else ""


def article_record(article):
    """Extract pmid, title, abstract and year from a PubmedArticle element."""
    pmid = article.findtext("./MedlineCitation/PMID")
    title = element_text(article.find(".//ArticleTitle"))
    abstract = " ".join(element_text(node) for node in article.iter("AbstractText"))
    return {"pmid": pmid, "title": title, "abstract": abstract.strip(),
            "year": publication_year(article)}


def fetch_batch(pmids):
    """Fetch title and abstract for one batch of PMIDs."""
    query = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
    with urllib.request.urlopen(f"{EUTILS_EFETCH}?{query}", timeout=120) as response:
        root = ET.fromstring(response.read())
    return {r["pmid"]: r for r in map(article_record, root.iter("PubmedArticle")) if r["pmid"]}


def fetch_records(pmids):
    """Fetch records for many PMIDs in batches."""
    collected = {}
    for start in range(0, len(pmids), FETCH_BATCH_SIZE):
        collected.update(fetch_batch(pmids[start:start + FETCH_BATCH_SIZE]))
        time.sleep(NCBI_DELAY_SECONDS)
    return collected


def walk_complete(pmids, target_size):
    """Fetch PMIDs in order, keeping complete abstracts until target_size."""
    kept, drawn = [], 0
    for start in range(0, len(pmids), FETCH_BATCH_SIZE):
        records = fetch_records(pmids[start:start + FETCH_BATCH_SIZE])
        for pmid in pmids[start:start + FETCH_BATCH_SIZE]:
            drawn += 1
            if pmid in records and is_complete(records[pmid]["abstract"]):
                kept.append(records[pmid])
            if len(kept) == target_size:
                return kept, drawn
    return kept, drawn


def eligible_pmids():
    """Return the in-window synerg* PMIDs in a fixed order."""
    return sorted(json.loads(ELIGIBLE_YEARS_PATH.read_text()))


def draw_sample(target_size):
    """Walk a seeded shuffle of the pool keeping complete abstracts until target_size."""
    shuffled = eligible_pmids()
    random.Random(RANDOM_SEED).shuffle(shuffled)
    kept, drawn = walk_complete(shuffled, target_size)
    if len(kept) < target_size:
        raise ValueError(f"only {len(kept)} complete abstracts in {len(shuffled)} eligible papers")
    return kept, drawn, len(shuffled)


def build_sample(target_size=SAMPLE_SIZE):
    """Draw the sample, record the pool size and papers walked, and save it."""
    papers, n_drawn, population = draw_sample(target_size)
    payload = {"seed": RANDOM_SEED, "target_size": target_size, "n_drawn": n_drawn,
               "population": population, "papers": papers}
    SAMPLE_PATH.write_text(json.dumps(payload))
    return papers, payload


def load_sample():
    """Load the saved sample in draw order."""
    payload = json.loads(SAMPLE_PATH.read_text())
    return payload["papers"], payload


def main():
    """Draw and save the sample, refusing to overwrite an existing one."""
    if SAMPLE_PATH.exists():
        raise SystemExit(f"{SAMPLE_PATH.name} exists; delete it to redraw")
    papers, payload = build_sample()
    print(f"sample: {len(papers)} complete abstracts from {payload['n_drawn']} walked "
          f"of {payload['population']} eligible papers (seed {payload['seed']})")


if __name__ == "__main__":
    main()
