#!/usr/bin/env python3
"""
Core screening module for drug interaction papers.
Used by screen_10.py, screen_100.py, screen_1000.py, screen_all.py
"""

import json
import time
from pathlib import Path
import requests

MISTRAL_API_KEY_FILE = Path.home() / ".mistral_key"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-large-2512"
DELAY = 2.5
MAX_RETRIES = 3

SCREENING_PROMPT = """Analyze this research paper abstract and extract the following information:

Title: {title}
Abstract: {abstract}

Respond ONLY with this JSON (no other text):
{{
  "domain": "antimicrobial|antiviral|oncology|immunology|anesthesia|neurology|ecotoxicology|pest_management|other",
  "labels_as_quality_proxy": "yes|no",
  "abstract_incomplete": "yes|no"
}}

PROTOCOL:
- domain: Classify by the TARGET of the combination study:
  - antimicrobial: bacterial or fungal infections
  - antiviral: viral infections
  - oncology: cancer
  - immunology: immune-related conditions
  - anesthesia: sedation, analgesia, or anesthesia management
  - neurology: neurological conditions (epilepsy, Parkinson's, pain, etc.)
  - ecotoxicology: toxic effects of chemical mixtures on non-target organisms or ecosystems
  - pest_management: combinations targeting pest organisms (insects, weeds, fungi in agricultural context)
  - other: target is genuinely unclear, non-combination study, or none of the above
- labels_as_quality_proxy: YES = Uses formal drug interaction labels (Loewe, Bliss, FICI, etc.) to categorize combinations AND either: (a) explicitly claims these labels indicate quality/promise/efficacy, OR (b) screens many combinations implying labels help identify the most effective ones; NO = Focuses on mechanistic understanding of WHY combinations work (labels are secondary or not central)
- abstract_incomplete: YES if the abstract reads incomplete and was likely cut off. NO if it reads as a coherent complete abstract."""

def load_api_key():
    """Load Mistral API key from file."""
    if MISTRAL_API_KEY_FILE.exists():
        return MISTRAL_API_KEY_FILE.read_text().strip()
    raise ValueError(f"API key not found in {MISTRAL_API_KEY_FILE}")

def screen_paper(paper, api_key):
    """Screen a single paper with Mistral API, with exponential backoff retry."""
    title = paper.get("title") or ""
    abstract = paper.get("abstract") or ""

    # Hard cutoff: abstracts under 200 chars are incomplete
    if len(abstract) < 200:
        return {
            "pmid": paper.get("pmid"),
            "title": (paper.get("title") or "")[:100],
            "domain": "unknown",
            "labels_as_quality_proxy": "unknown",
            "abstract_incomplete": "yes",
            "reason": "abstract_too_short",
            "_tokens_in": 0,
            "_tokens_out": 0,
            "_time_s": 0.0,
        }

    prompt = SCREENING_PROMPT.format(title=title, abstract=abstract)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    for attempt in range(MAX_RETRIES):
        try:
            t0 = time.time()
            response = requests.post(MISTRAL_URL, json=payload, headers=headers, timeout=30)
            elapsed = time.time() - t0
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Extract JSON from markdown if present
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            result = json.loads(content)
            result["pmid"] = paper.get("pmid")
            result["title"] = (paper.get("title") or "")[:100]
            usage = data.get("usage", {})
            result["_tokens_in"]  = usage.get("prompt_tokens", 0)
            result["_tokens_out"] = usage.get("completion_tokens", 0)
            result["_time_s"]     = round(elapsed, 2)
            return result

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(2.5 * (2 ** attempt))
                continue
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            # Malformed/empty API response — retry
            if attempt < MAX_RETRIES - 1:
                time.sleep(2.5 * (2 ** attempt))
                continue
            raise

def screen_papers(papers, api_key, show_progress=True, checkpoint_file=None):
    """Screen papers, writing each result to checkpoint_file immediately.

    On restart, already-processed PMIDs are loaded from the checkpoint and
    skipped — so the run resumes from where it left off.
    """
    # Load already-processed results from checkpoint
    done = {}
    if checkpoint_file and Path(checkpoint_file).exists():
        with open(checkpoint_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    done[r.get("pmid")] = r
        if done:
            print(f"Resuming: {len(done)} papers already in checkpoint.")

    results = []
    total = len(papers)

    for i, paper in enumerate(papers, 1):
        pmid = paper.get("pmid")

        if pmid in done:
            results.append(done[pmid])
            if show_progress:
                print(f"[{i:4d}/{total}] PMID {pmid}... (cached)")
            continue

        if show_progress:
            print(f"[{i:4d}/{total}] PMID {pmid}...", end=" ", flush=True)

        try:
            result = screen_paper(paper, api_key)
            results.append(result)
            if show_progress:
                tok_in  = result.get("_tokens_in", 0)
                tok_out = result.get("_tokens_out", 0)
                t       = result.get("_time_s", 0)
                print(f"✓  ({tok_in}in/{tok_out}out, {t:.1f}s)")
        except Exception as e:
            result = {"pmid": pmid, "error": str(e),
                      "_tokens_in": 0, "_tokens_out": 0, "_time_s": 0.0}
            results.append(result)
            if show_progress:
                print(f"✗ {str(e)[:30]}")

        if checkpoint_file:
            with open(checkpoint_file, "a") as f:
                f.write(json.dumps(result) + "\n")

        time.sleep(DELAY)

    return results

def save_markdown_files(results, papers, output_dir):
    """Create individual markdown files for each paper."""
    papers_by_pmid = {p.get("pmid"): p for p in papers}

    for i, r in enumerate(results, 1):
        pmid = r.get("pmid")
        original = papers_by_pmid.get(pmid, {})

        md_file = output_dir / f"{i:04d}_{pmid}.md"

        if "error" in r:
            md_content = f"# Paper {i}: {pmid}\n\n⚠️ ERROR: {r['error']}\n"
        else:
            md_content = f"""# Paper {i}: {pmid}

## Abstract

{original.get('abstract', 'N/A')}

---

## AI Screening Evaluation

| Field | Value |
|-------|-------|
| Domain | {r.get('domain', 'ERROR')} |
| Labels as Quality Proxy? | {r.get('labels_as_quality_proxy', 'ERROR')} |
| Abstract Incomplete? | {r.get('abstract_incomplete', 'no')} |
"""

        with open(md_file, "w") as f:
            f.write(md_content)

def print_summary(results, name="Screening"):
    """Print summary statistics."""
    valid = [r for r in results if "error" not in r]
    incomplete = sum(1 for r in valid if r.get("abstract_incomplete") == "yes")
    non_therapeutic = sum(1 for r in valid if r.get("domain") == "other")
    # Evaluable = complete AND therapeutic (not incomplete AND not 'other')
    evaluable = sum(1 for r in valid if r.get("abstract_incomplete") != "yes" and r.get("domain") != "other")

    labels_as_proxy = sum(1 for r in valid if r.get("labels_as_quality_proxy") == "yes" and r.get("abstract_incomplete") != "yes" and r.get("domain") != "other")

    tokens_in  = sum(r.get("_tokens_in",  0) for r in valid)
    tokens_out = sum(r.get("_tokens_out", 0) for r in valid)
    cost_usd = tokens_in / 1e6 * 2 + tokens_out / 1e6 * 6
    cost_chf = cost_usd * 0.88

    print("\n" + "="*70)
    print(f"✓ {name} complete: {len(valid)}/{len(results)} successful")
    print(f"  - Abstract incomplete: {incomplete}")
    print(f"  - Non-therapeutic (domain='other'): {non_therapeutic}")
    print(f"  - Evaluable papers (complete + therapeutic): {evaluable}")
    if evaluable > 0:
        print(f"  - Labels as quality proxy: {labels_as_proxy}/{evaluable} ({100*labels_as_proxy/evaluable:.1f}%)")
    if tokens_in:
        print(f"  - Tokens: {tokens_in:,} in / {tokens_out:,} out  (~${cost_usd:.2f} / CHF {cost_chf:.2f})")
    print("="*70)

    return {
        "total": len(results),
        "valid": len(valid),
        "incomplete": incomplete,
        "non_therapeutic": non_therapeutic,
        "evaluable": evaluable,
        "labels_as_proxy": labels_as_proxy,
    }
