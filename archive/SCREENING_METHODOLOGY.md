# Screening Methodology for Drug Interaction Literature Review

## Data Source & Search Strategy

**Database:** PubMed  
**Date Range:** 2010–2026 (June)  
**Search Approach:** Year-by-year to overcome relevance ranking bias  
**Total Papers Retrieved:** 24,487

### Search Query

```
(synergy OR antagonism OR "synergistic" OR "antagonistic") 
AND combination 
AND (Loewe OR Bliss OR "Chou-Talalay" OR "combination index" OR CI OR FICI 
     OR "fractional inhibitory" OR "concentration addition" OR HSA 
     OR "highest single agent" OR MuSyC OR BRAID OR interaction)
```

**Rationale:** Captures papers using formal drug interaction assessment methods while mentioning synergy/antagonism as core concepts.

---

## Screening Criteria

### Step 1: Abstract Length Filter (Hard Cutoff)
- **Rule:** Abstracts under 200 characters → automatically marked as `abstract_incomplete: yes`
- **Rationale:** Stubs/truncated abstracts lack sufficient content to evaluate. Papers ≥200 chars proceed to Mistral.

### Step 2: LLM-Based Screening (Mistral Large)

Papers with abstracts ≥200 characters are evaluated by Mistral AI using the following criteria:

#### Domain Classification
Classified by **therapeutic target** (what disease/pathogen the drugs treat):
- **antimicrobial** — bacterial/fungal infections
- **antiviral** — viral infections
- **oncology** — cancer
- **immunology** — immune-related conditions
- **other** — non-disease applications or unclear targets

#### labels_as_quality_proxy (Primary Classification)
**Field Name Clarification:** This field captures whether interaction labels (synergy/antagonism) derived from formal methods (Loewe, Bliss, FICI, etc.) are treated **as proxies for combination quality**, not merely observed or discussed.

- **YES** = Uses formal drug interaction labels to categorize combinations AND either:
  - (a) explicitly claims these labels indicate quality/promise/efficacy, OR
  - (b) screens many combinations, implying labels help identify therapeutically valuable ones
- **NO** = Focuses on mechanistic understanding of WHY combinations work (interaction labels are secondary or not central)

**Operationalization:** Papers scoring YES are the target population for the critique—they treat interaction labels (synergy/antagonism classifications) as evidence of combination quality without mechanistic justification.

#### num_combinations & drugs
- **num_combinations:** Exact count if stated; "5+" if >5 but imprecise; "≤5" if ≤5; "unknown" otherwise
- **drugs:** Comma-separated drug names if mentioned, otherwise "not mentioned"
- **num_drugs:** Count of distinct drugs tested

#### focuses_on_interaction_labels
- **YES** if synergy/antagonism classification is central to the study
- **NO** if measured incidentally or not mentioned

#### abstract_incomplete
- **YES** if ANY of:
  - Under 200 characters (auto-flagged in Step 1)
  - Clearly missing results/conclusions sections
  - Uses "..." or "[truncated]" markers
- **NO** if reads as coherent complete abstract

#### cannot_classify
- **YES** only if abstract is too vague to assess despite being complete
- **NO** otherwise

---

## Model Configuration

- **Model:** Mistral Large (latest)
- **Temperature:** 0.1 (low variance, deterministic output)
- **Retry Strategy:** Exponential backoff (429 rate limits)
- **Output Format:** Strict JSON validation

---

## Sampling & Analysis

**Initial Sample:** 100 papers randomly sampled from 24,487  
**Evaluation:** 10 papers manually reviewed for accuracy

### Filtering Pipeline
1. Exclude papers with `abstract_incomplete: yes`
2. Exclude papers with `domain: "other"` (non-therapeutic applications: food chemistry, materials science, etc.)
3. Evaluate on therapeutic domains only: antimicrobial, antiviral, oncology, immunology

**Rationale for Domain Filter:** The critique targets drug interaction labels in therapeutic contexts. Non-therapeutic studies (dietary fiber combinations, polysaccharide chemistry) use "synergistic/antagonistic" language mechanistically, not as quality proxies for therapeutic selection. Domain filtering ensures we measure the right population.

Prevalence reported as: `(labels_as_quality_proxy: yes) / (total - incomplete - other)`

---

## Rationale for Criteria

The screening targets papers that use drug interaction labels (Loewe, Bliss, FICI, etc.) **as a quality indicator**. The core critique is:

> Formal interaction labels (synergistic/antagonistic) are derived methods for classifying empirical observations, not evidence that a combination is therapeutically valuable. Yet many papers implicitly treat these labels as proxies for combination quality.

Papers focusing on mechanisms (e.g., "How does this combination work?") without foregrounding interaction labels are scored NO, as they do not make this problematic inference.

---

## Limitations

1. **LLM Classification Accuracy:** Mistral achieves ~70–80% accuracy on full-text validation (based on manual review). Edge cases include:
   - Herbal medicine studies using informal "synergistic" language
   - Papers using "synergy" colloquially without formal methods
   
2. **Abstract-Only Evaluation:** Full-text assessment would improve accuracy but is infeasible at scale (24,487 papers).

3. **Short Abstract Borderline:** Papers with 200–250 characters are evaluated by Mistral; some may be stubs that pass as "grammatically complete."

4. **Domain Misclassification:** Papers with unclear therapeutic targets or multiple domains are classified as "other" or the primary target; cross-domain misclassification is rare but possible.

---

## Output Files

- `pubmed_results_all_years.json` — Master dataset (24,487 papers with metadata)
- `sample_100_for_screening.json` — Random 100-paper sample
- `screening_100/screening_results.json` — LLM classifications + markdown summaries
- `test_examples/` — 10-paper manual validation set (raw abstracts + AI classifications + manual assessment)
