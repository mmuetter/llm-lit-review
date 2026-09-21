"""Deterministic completeness filter and seeded sampling of gated papers.

Records are fetched from PubMed on demand, because the gate admits papers that
predate the stored corpus.
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
CORPUS_PATH = DATA_DIR / "pubmed_results_all_years.json"
TERM_SCORES_PATH = DATA_DIR / "term_scores_v3.json"
GATED_YEARS_PATH = DATA_DIR / "gated_paper_years_v3.json"
SCORE1_YEARS_PATH = DATA_DIR / "score1_paper_years.json"
SAMPLE_PATH = DATA_DIR / "screening_sample_v2.json"
STRATIFIED_SAMPLE_PATH = DATA_DIR / "screening_sample_v4.json"
SYNERGY_GATE_PATH = DATA_DIR / "synergy_gate_pmids.json"
TARGET_PER_SCORE = 250
ALL_SCORES = (1, 2, 3, 4, 5, 6)

FIRST_YEAR = 2010
LAST_YEAR = 2025
GATE_THRESHOLD = 2
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


def gated_years():
    """Return each gated PMID's single publication year."""
    if not GATED_YEARS_PATH.exists():
        raise FileNotFoundError(
            f"{GATED_YEARS_PATH.name} is missing; run year_gate_counts.py before sampling")
    return json.loads(GATED_YEARS_PATH.read_text())


def gated_pmids():
    """Return in-window PMIDs whose group score meets the gate."""
    scores = json.loads(TERM_SCORES_PATH.read_text())
    years = gated_years()
    return sorted(pmid for pmid, score in scores.items()
                  if score >= GATE_THRESHOLD
                  and FIRST_YEAR <= years.get(pmid, 0) <= LAST_YEAR)


def stored_records():
    """Return already-stored records keyed by PMID."""
    if not CORPUS_PATH.exists():
        return {}
    return {p["pmid"]: p for p in json.loads(CORPUS_PATH.read_text())}


def draw_sample(target_size):
    """Walk a seeded shuffle keeping complete abstracts until target_size."""
    shuffled = gated_pmids()
    random.Random(RANDOM_SEED).shuffle(shuffled)
    stored, kept, drawn = stored_records(), [], 0
    for start in range(0, len(shuffled), FETCH_BATCH_SIZE):
        chunk = shuffled[start:start + FETCH_BATCH_SIZE]
        missing = [p for p in chunk if p not in stored]
        stored.update(fetch_records(missing) if missing else {})
        for pmid in chunk:
            drawn += 1
            record = stored.get(pmid)
            if record and is_complete(record.get("abstract")):
                kept.append(record)
            if len(kept) == target_size:
                return kept, drawn
    raise ValueError(f"only {len(kept)} complete abstracts in {len(shuffled)} gated papers")


def build_sample(target_size):
    """Draw the sample, record how many papers were walked, and save it."""
    papers, n_drawn = draw_sample(target_size)
    payload = {"seed": RANDOM_SEED, "target_size": target_size, "n_drawn": n_drawn,
               "gate": GATE_THRESHOLD, "papers": papers}
    SAMPLE_PATH.write_text(json.dumps(payload))
    return papers, payload


def load_sample():
    """Load the saved sample in draw order."""
    payload = json.loads(SAMPLE_PATH.read_text())
    return payload["papers"], payload


def in_window(years):
    """Return the PMIDs dated inside the analysis window."""
    return {pmid for pmid, year in years.items() if FIRST_YEAR <= (year or 0) <= LAST_YEAR}


def synergy_pmids():
    """Return the PMIDs whose title or abstract uses a synergy term."""
    return set(json.loads(SYNERGY_GATE_PATH.read_text()))


def score_strata(scores=ALL_SCORES):
    """Map each requested group score to its sorted in-window PMIDs."""
    gated = json.loads(TERM_SCORES_PATH.read_text())
    strata = {1: sorted(in_window(json.loads(SCORE1_YEARS_PATH.read_text())))} if 1 in scores else {}
    for pmid in sorted(in_window(gated_years())):
        if gated[pmid] in scores:
            strata.setdefault(gated[pmid], []).append(pmid)
    return strata


def synergy_strata(scores=ALL_SCORES):
    """Map each score to its in-window PMIDs that use a synergy term."""
    synergy = synergy_pmids()
    return {score: [p for p in pmids if p in synergy]
            for score, pmids in score_strata(scores).items()}


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


def seeded_order(score, pmids):
    """Return a score stratum's PMIDs in its seeded random order."""
    shuffled = list(pmids)
    random.Random(RANDOM_SEED + score).shuffle(shuffled)
    return shuffled


def draw_stratum(score, pmids, eligible=None):
    """Draw one stratum's eligible papers in seeded order, or all if few."""
    shuffled = [p for p in seeded_order(score, pmids) if eligible is None or p in eligible]
    kept, drawn = walk_complete(shuffled, TARGET_PER_SCORE)
    if len(shuffled) > TARGET_PER_SCORE and len(kept) < TARGET_PER_SCORE:
        raise ValueError(f"score {score}: only {len(kept)} complete abstracts in {len(shuffled)}")
    papers = [dict(record, score=score) for record in kept]
    return papers, {"population": len(shuffled), "drawn": drawn, "kept": len(kept)}


def build_stratified_sample(scores=ALL_SCORES):
    """Draw the requested score strata from fresh records and save the manifest."""
    papers, strata = [], {}
    synergy = synergy_pmids()
    for score, pmids in sorted(score_strata(scores).items()):
        drawn, strata[score] = draw_stratum(score, pmids, synergy)
        papers.extend(drawn)
    payload = {"seed": RANDOM_SEED, "target_per_score": TARGET_PER_SCORE,
               "strata": strata, "papers": papers}
    STRATIFIED_SAMPLE_PATH.write_text(json.dumps(payload))
    return papers, payload


def load_stratified_sample():
    """Load the stratified sample and its per-score population sizes."""
    payload = json.loads(STRATIFIED_SAMPLE_PATH.read_text())
    return payload["papers"], {int(score): s for score, s in payload["strata"].items()}
