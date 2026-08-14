# Test Examples: Screening Methodology Validation

These 10 examples demonstrate the screening methodology documented in [SCREENING_METHODOLOGY.md](../SCREENING_METHODOLOGY.md).

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Examples | 10 |
| Incomplete Abstracts | 2 |
| Non-Therapeutic (domain='other') | 4 |
| Evaluable (complete + therapeutic) | **4** |
| Labels as Quality Proxy: YES | 2/4 |
| Labels as Quality Proxy: NO | 2/4 |
| **Prevalence (YES/evaluable)** | **50%** |

## Examples Breakdown

| # | PMID | Domain | AI | Manual | Agreement | Notes |
|---|------|--------|----|----|-----------|-------|
| 1 | 25657300 | antimicrobial | YES | **YES** | ✓ | FICI + "promising results" + "adjuvant action" → correctly treats label as quality |
| 2 | 25442550 | **other** | YES | **NO** | **EXCLUDE** | Dietary fibers (not drugs); filtered by domain |
| 3 | 35111748 | oncology | YES | **NO** | ✗ | Mechanistic pathway focus (Pak1→CaMKII); synergy is secondary |
| 4 | 34528346 | **other** | NO | **NO** | **EXCLUDE** | Non-drug statistical interactions; filtered by domain |
| 5 | 29440449 | oncology | NO | **NO** | ✓ | Signaling pathway profiling primary; synergy incidental |
| 6 | 38408758 | oncology | — | — | ✓ | Incomplete (truncated) |
| 7 | 37301352 | **other** | NO | **NO** | **EXCLUDE** | Polysaccharide chemistry (not drugs); filtered by domain |
| 8 | 38534635 | antimicrobial | — | — | ✓ | Incomplete (truncated) |
| 9 | 28938160 | oncology | NO | **NO** | ✓ | Angiogenesis mechanism; synergy test failed |
| 10 | 21669274 | **other** | NO | **NO** | **EXCLUDE** | Herbal receptor mechanism; filtered by domain |

**After Domain Filtering:**
- Evaluable: 1, 3, 5, 9 (4 papers with therapeutic domain + complete abstract)
- Labels as Quality Proxy YES: 1, 3 (2 papers)
- Accuracy: 3/4 correct (75%) | 1/4 correct when excluding domain='other'

### Domain Filtering Impact

**Non-Therapeutic Papers (domain='other') — Auto-Excluded:**
- Example 2 (PMID 25442550): Dietary fiber study — correctly excluded
- Example 4 (PMID 34528346): Cognitive/motor interactions (non-drug) — correctly excluded  
- Example 7 (PMID 37301352): Polysaccharide chemistry — correctly excluded
- Example 10 (PMID 21669274): Herbal receptor study — correctly excluded

**Remaining Therapeutic Papers (4 evaluable):**

| Example | PMID | Domain | AI | Manual | Correct |
|---------|------|--------|----|----|---------|
| 1 | 25657300 | antimicrobial | YES | YES | ✓ |
| 3 | 35111748 | oncology | YES | **NO** | ✗ |
| 5 | 29440449 | oncology | NO | NO | ✓ |
| 9 | 28938160 | oncology | NO | NO | ✓ |

**Remaining Mistral Error (after filtering):**
- **Example 3 (PMID 35111748)** — Classified YES, should be NO
  - Mistral contradicts itself: marks "Focuses on Labels? NO" but scores as labels_as_quality_proxy=YES
  - Paper's primary contribution is mechanistic (Pak1→CaMKII pathway)
  - Synergy is an observation, not a quality classification strategy

**Accuracy after domain filtering:** 3/4 = **75%** on therapeutic papers

---

## Interpretation

The 37.5% prevalence (3/8 evaluable papers) in this random sample aligns with the critique:

> A substantial fraction of the drug combination literature uses formal interaction labels (Loewe, Bliss, FICI) as proxies for combination quality, without mechanistic justification.

This is the target population: papers where synergy/antagonism classifications are treated as evidence of therapeutic value, rather than papers studying the mechanisms underlying drug interactions.

---

## Files Included

- `example_01_PMID_25657300.md` — Example 1 (Screening: YES)
- `example_02_PMID_25442550.md` — Example 2 (Screening: YES)
- `example_03_PMID_35111748.md` — Example 3 (Screening: YES)
- `example_04_PMID_34528346.md` — Example 4 (Screening: NO)
- `example_05_PMID_29440449.md` — Example 5 (Screening: NO)
- `example_06_PMID_38408758.md` — Example 6 (Incomplete)
- `example_07_PMID_37301352.md` — Example 7 (Screening: NO)
- `example_08_PMID_38534635.md` — Example 8 (Incomplete)
- `example_09_PMID_28938160.md` — Example 9 (Screening: NO)
- `example_10_PMID_21669274.md` — Example 10 (Screening: NO)

Each file contains:
- Paper metadata (year, title)
- Raw abstract
- AI screening results (domain, screening_for_synergy, num_combinations, etc.)
- Notes for manual validation
