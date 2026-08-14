# Revised Analysis — Multiverse Screening Design

Status: **stage 1 locked, stage 2 drafted.** Remaining decisions at the bottom.

Purpose: support a claim at the granularity of "hundreds of papers per year",
robustly enough that it does not depend on any single prompt, model, or
threshold choice. This is a robustness exercise, not a precision exercise.

Window: **2010–2025** (2026 dropped as a partial year).

---

## Stage 1 — Eligibility by PubMed term-group score

Each term group is issued as its own PubMed query, restricted to the base query
and run year by year. A paper's score is the number of groups it matches.

Searching through PubMed rather than scoring abstract text locally means a group
can match via title, abstract, author keywords **or** MeSH indexing — so papers
whose abstracts do not use the vocabulary are still caught, without depending on
MeSH being assigned.

**Gate: score ≥ 2.**

### Base query

```
(synergy OR antagonism OR synergistic OR antagonistic)
AND combination
AND (Loewe OR Bliss OR "Chou-Talalay" OR "combination index" OR FICI
     OR "fractional inhibitory" OR "concentration addition" OR HSA
     OR "highest single agent" OR MuSyC OR BRAID OR interaction)
```

### Term groups

Unrestricted terms for the core concepts, so they pick up MeSH mapping;
`[tiab]` for specific method names, where MeSH mapping is meaningless.

| group | query | hits |
|---|---|---|
| synergy | `synergism OR synergistic OR synergy` | 19,810 |
| additivity | `additive OR additivity OR indifference` | 6,325 |
| antagonism | `antagonism OR antagonistic` | 4,586 |
| drug_interaction | `"drug interactions" OR "drug combination" OR "pairwise interaction" OR "interaction network"` | 2,232 |
| combination_index | `"combination index"[tiab]` | 1,762 |
| fici | `FICI[tiab] OR "fractional inhibitory concentration"[tiab] OR "FIC index"[tiab]` | 1,491 |
| checkerboard | `checkerboard[tiab]` | 1,091 |
| isobologram | `isobologram[tiab] OR isobolographic[tiab] OR isobole[tiab]` | 578 |
| chou_talalay | `"Chou-Talalay"[tiab] OR "Chou Talalay"[tiab]` | 353 |
| bliss | `Bliss[tiab]` | 260 |
| concentration_addition | `"concentration addition"[tiab] OR "independent action"[tiab]` | 241 |
| loewe | `Loewe[tiab]` | 126 |
| highest_single_agent | `"highest single agent"[tiab]` | 32 |
| zero_interaction_potency | `"zero interaction potency"[tiab] OR "ZIP score"[tiab]` | 31 |
| musyc | `MuSyC[tiab]` | 8 |
| braid | `BRAID[tiab]` | 5 |

### Resulting ladder

| threshold | papers | share |
|---|---|---|
| ≥1 (= the base query itself) | 21,930 | 100% |
| **≥2 (gate)** | **10,942** | **49.9%** |
| ≥3 | 4,132 | 18.8% |
| ≥4 | 1,425 | 6.5% |
| ≥5 | 395 | 1.8% |

Score ≥1 is tautological: the base query already requires synergy/antagonism
terms, so it restates the query rather than filtering it.

Every paper's score is stored (`data/pubmed_term_scores.json`), so the threshold
can be sliced post hoc and reported as a sensitivity rather than defended as a
choice.

### Why ≥2

Scoring against the previous Mistral run shows a clean monotonic relationship
between score and the rate at which papers were judged to treat labels as a
quality marker:

| term score | n | YES rate |
|---|---|---|
| 1 | 290 | 1.4% |
| 2 | 205 | 15.6% |
| 3 | 84 | 41.7% |
| 4 | 40 | 57.5% |
| 5 | 11 | 72.7% |

Papers at exactly score 1 — half the corpus — are 1.4% YES. Excluding them costs
almost nothing and removes the off-topic senses of "interaction" (parent–child
interaction therapy, drug–ultrasound interaction, protein interactions).

### Reproducibility notes

- PubMed's index shifts over time; record the retrieval date.
- ESearch cannot return more than 9,999 records for any query, hence the
  year-by-year split.
- The `synergy` group matches 90% of the corpus and so contributes no
  discrimination; the score is effectively driven by the other 15 groups.

---

## Stage 2 — Sampling

Seeded shuffle of the 10,942 gated papers, walked in order, keeping papers whose
abstract passes the deterministic completeness filter until **500** are
collected. `n_drawn` is recorded; completeness among gated papers is ~79%, so
expect to draw ~635.

The stopping rule depends only on completeness — a deterministic property
evaluated before any classification — so it cannot bias the outcome rate.

An abstract fails the completeness filter if any of:

1. Length < 200 characters.
2. Does not end in sentence-terminating punctuation after stripping whitespace.
3. Unbalanced parentheses or brackets.
4. Ends mid-token — final token is a bare unit, digit-unit fragment, or an
   opening delimiter (catches the `(Ca` and `×10` cases from the earlier manual
   validation run).

The claim is scoped to gated papers with complete abstracts. No assumption is
made about the excluded ones.

**Frame coverage.** The PubMed term-score query returns 10,942 gated PMIDs, but
728 of them have no record in the stored corpus (index drift between the June
2026 corpus fetch and the scoring queries), so the sampling frame is the
remaining **10,214**. This is a 6.6% coverage gap skewed toward recently added
records — immaterial at "hundreds per year" granularity, but stated rather than
silent.

Expected domain composition at n = 500, from the previous run gated at ≥2:

| domain | share of gated | expected n |
|---|---|---|
| oncology | 32.8% | 164 |
| antimicrobial | 24.7% | 124 |
| other_therapeutic | 16.1% | 81 |
| not_a_drug_combination | 14.5% | 73 |
| environmental_agricultural | 11.9% | 60 |

(Mapped from the previous run's nine categories; see stage 4.)

Gating raises antimicrobial from 14.3% of the ungated corpus to 24.7%.

At 500 papers the full grid is 5,000 calls, so this doubles as a pilot: if a
prompt misfires or the consensus histogram shows a fat middle, re-running or
scaling to 2,000 costs little and can be decided from data.

---

## Stage 3 — Domain classification

Both models classify domain **once per paper**, in a dedicated call independent
of the outcome classification. Two calls per paper; model settings as in stage 4.

Domain is not a varied factor — the prompt axis probes the synergy construct —
so asking it inside all ten configurations produced ten judgments that were not
independent: same model, differing only by whichever synergy prompt surrounded
them. Any variation between them is the outcome prompt bleeding into the domain
call, which is contamination rather than signal. `domain` is therefore absent from the
stage-4 outcome schema entirely.

### Prompt

Five categories, assigned by an ordered decision rule — "first that applies"
resolves overlaps deterministically, so boundary cases (neurology vs.
anaesthesia, agricultural vs. clinical antifungal) cannot arise.

```
Title: {title}
Abstract: {abstract}

Assign exactly one category, taking the FIRST that applies:

1. not_a_drug_combination — not a combination of drugs or other chemical
   agents acting on an organism, cell, or pathogen (materials science,
   food chemistry, epidemiological risk factors, plant physiology).
2. environmental_agricultural — targets pests, or concerns effects on
   non-target organisms or ecosystems, or is an agricultural application.
3. antimicrobial — targets bacteria or fungi in a medical or veterinary
   context.
4. oncology — targets cancer.
5. other_therapeutic — any other human or veterinary therapeutic use
   (antiviral, neurological, immunological, anaesthetic, cardiovascular).
```

Schema: `{"domain": {"type": "string", "enum": [...]}}`, required, no
additional properties.

`not_a_drug_combination` doubles as a gate-precision diagnostic: its rate is
the share of the gated corpus that the term-score filter let through in error.

Lost relative to the earlier nine-category list: antiviral, anaesthesia,
immunology and neurology as separate reportables. None was large enough to
report at n = 500 (6, 4, 19 and 51 papers respectively), and the piece reports
antimicrobial and oncology only.

### Run order — and why nothing is excluded here

Domain runs before the outcome grid as a **smoke test**: 1,000 cheap calls that
confirm the gate is behaving, the two models agree on domain, and the
distribution matches projection — all before committing to the 5,000-call grid.

**No papers are excluded on the basis of it.** Dropping the ~73
`not_a_drug_combination` papers would save 730 of 5,000 calls (~$0.75 on the
Sonnet arm) and would cost the scope-guard validation: those papers should come
back "no" from all ten configurations, and any configuration answering "yes" on
one reveals a leaking guard. Excluding them also forces a rule for the case
where the two models disagree about whether a paper is in scope. Running
everything avoids both problems.

The in-scope subset is applied as a **filter in analysis**, not before the API
calls — so the primary rate is reported over papers that actually study drug
combinations, while the validation stays available.

### Resolution

| both models | assignment |
|---|---|
| agree | that domain |
| disagree | `domain_ambiguous` |

Ambiguous papers stay in the overall rate and drop out of per-domain tables
only. The disagreement rate is reported as a diagnostic: if domain agreement is
high, the per-domain breakdown is trustworthy; if it is poor, only the overall
rate is reported.

---

## Stage 4 — Outcome classification

**2 models × 5 prompts = 10 configurations**, all run on the same paper set.

### Model settings

The goal is the lowest-variance configuration each model offers, so the spread
measures specification choices rather than sampling noise. The two models reach
that by different means — Sonnet 5 rejects non-default `temperature`, `top_p`,
and `top_k` with a 400, so temperature cannot be set on that arm.

| arm | settings |
|---|---|
| `mistral-large-2512` | `temperature=0`; minimum 1.0 s between requests |
| `claude-sonnet-5` | omit `temperature`; `thinking={"type": "disabled"}`; `output_config={"effort": "low"}` |

Adaptive thinking is **on by default** on Sonnet 5 — omitting the `thinking`
field does not mean thinking is off. It must be disabled explicitly, or every
call thinks, adding cost, latency and run-to-run variance to what is a simple
classification.

The Mistral interval is a deliberate throttle (not a measured limit) that keeps
the endpoint from dropping requests; it paces the whole run at ~50 min for 3,000
calls, while the Sonnet arm finishes its share in minutes.

### Safety refusals on the Sonnet arm

Sonnet 5 runs safety classifiers that decline a small share of requests with
`stop_reason: "refusal"`. In the pilot this was **7 of 150 Sonnet cells (4.7%)**,
across 2 of 25 papers, both false positives on ordinary pharmacology (a cobra
neurotoxin analgesia study; a baculovirus bioinsecticide review). The refusal
category is recorded with each failure.

Refusals are handled by **paper-level exclusion**: if any configuration refuses
on a paper, that paper is dropped from every column, so all ten configurations
retain an identical denominator. Cell-level exclusion would leave columns with
different denominators and destroy the like-for-like comparison. Excluded papers
and their refusal categories are reported.

Server-side fallback to another model is deliberately **not** used: it would
answer those cells with a different model and contaminate the model contrast.

Because the two arms reach low variance differently, one Sonnet configuration is
re-run on ~100 papers to measure its own run-to-run disagreement. If that is near
zero the confound is immaterial and the SI says so in one sentence.

| contrast | question |
|---|---|
| P2 → P1 → P3 | sensitivity to construct strictness |
| P4 vs. rest | effect of the synergy/antagonism symmetry criterion |
| P5 vs. P1/P2 | how much of the practice is implicit in study design rather than stated |
| model ↔ model, within prompt | vendor / training-corpus effect |

No paraphrase pair: at "hundreds per year" granularity the wording-noise floor
does not change the reported sentence, so all five prompts carry distinct
constructs.

### Shared scaffold

The answer shape is enforced by the API rather than requested in prose — Sonnet 5
via `output_config.format`, Mistral via its JSON mode — so malformed output
cannot occur and no parse-retry path is needed.

```
Title: {title}
Abstract: {abstract}
```

Every prompt is preceded by a shared scope guard. It is phrased as a condition, not an assertion, so it does not
presuppose that the paper qualifies:

```
Answer "no" if this paper is not about a combination of drugs or other
chemical agents acting on an organism, cell, or pathogen — regardless of
how it uses the word "synergy". Materials, food chemistry, and
epidemiological risk-factor studies are "no".
```

Without this, prompts P1–P3 score "yes" on any paper that treats synergy as a
good thing, which includes essentially all materials and food-science work
("Synergistic Effects of Epoxidized Soybean Oil ... on Crumb Rubber Modified
Asphalt"). Such papers are ~14.5% of the gated set. Ecotoxicology and pest
management stay in scope — they use the same reference-model framework
(concentration addition / independent action), and in the previous run both
scored 0% yes, which is itself a check that the construct behaves.

Enforced schema, identical for both arms:

```json
{
  "type": "json_schema",
  "schema": {
    "type": "object",
    "properties": {
      "synergy_desirable": {"type": "string", "enum": ["yes", "no"]}
    },
    "required": ["synergy_desirable"],
    "additionalProperties": false
  }
}
```

No self-reported confidence field: with 10 configurations, a split verdict is a
measured uncertainty signal, whereas a confidence flag is uncalibrated and
differs systematically between models.

### P1 — neutral

```
Does this paper present synergy (a favourable drug-interaction label) as
desirable — as a point in the combination's favour? Judge the authors'
own findings and conclusions, not general background statements about
synergy.
```

### P2 — strict

```
Answer "yes" only if the paper explicitly evaluates a synergistic result
positively — calling the combination promising, effective, advantageous,
or a candidate for further development on the strength of the interaction
label. Reporting synergy without such an evaluation is "no".
```

### P3 — permissive

```
Answer "yes" if synergy is treated as favourable in any way — including
foregrounding synergistic combinations in the title or conclusions,
selecting or recommending them over non-synergistic ones, or presenting
synergy as the study's main positive result. Answer "no" only if
interaction labels are reported neutrally with no preference implied.
```

### P4 — symmetry

```
Answer "yes" only where synergy is the favoured outcome and antagonism
the unfavourable one. A paper that treats synergy and antagonism
symmetrically — both as equally informative about mechanism, structure,
or classification — is NOT presenting synergy as desirable, even if it
measures drug interactions extensively.
```

### P5 — screening design

Judges from study design rather than evaluative language. Papers this variant
catches that P1/P2 miss are quantified by the per-paper consensus analysis —
that gap measures how much of the practice is implicit rather than stated.

```
Consider why this study was done. If it screens or assays multiple drug
combinations and reports interaction labels for them, answer "yes" — such
screens are implicitly searching for favourable (synergistic) combinations —
UNLESS the stated purpose is mechanistic, structural, or classificatory
(understanding how or why interactions arise), in which case answer "no".
For studies of a single combination, answer "yes" only if the interaction
label is presented as evidence in the combination's favour.
```

---

## Analysis

Domain (stage 3) is shared across all configurations; the outcome columns
(stage 4) are independent of each other. Because every configuration is scored
on the same domain assignment, denominators are identical across a row and the
range column reflects differing numerators only — a like-for-like comparison.

Primary output — % yes per domain, per configuration:

| domain | M1·P1 | M1·P2 | … | M2·P5 | range |
|---|---|---|---|---|---|
| antimicrobial | | | | | |
| oncology | | | | | |

Report `n` once per row (the domain's paper count), not per cell.

Secondary outputs:

- **Per-paper consensus**: histogram of how many of the 10 configurations
  answered yes. Bimodal at 0 and 10 means the construct is crisp; a fat middle
  means it is genuinely fuzzy.
- **Threshold slice**: the same table recomputed at score ≥3 and ≥4.

No agreement filtering anywhere. Papers where configurations disagree are the
most informative rows in the dataset, and removing them would guarantee high
agreement by construction.

### Output format

JSON of raw results, plus a spreadsheet with one row per paper:

`pmid | title | term_score | domain_m1 | domain_m2 | domain_resolved | 10 × outcome | n_yes | all_agree`

Identifier is PMID (the corpus records carry no DOI). Title is included so the
disagreement rows are readable — sorted by `n_yes`, the papers nearest 5/10 are
where a manual read would add the most.

---

## Results (n = 500, run 2026-08-13/14)

Grid completeness **5,921/6,000 cells (98.7%)**. All 79 missing cells are Sonnet
safety refusals (`bio` category, plus 6 uncategorised from the pilot) except two
Mistral transport errors. Mistral cells all recovered on retry at 2.5 s.

### Specification curve — % yes per configuration

| configuration | rate | 95% CI | n |
|---|---|---|---|
| mistral · P1 neutral | 57.2% | 53–61 | 500 |
| claude · P5 screening | 58.1% | 54–62 | 487 |
| claude · P2 strict | 58.6% | 54–63 | 488 |
| claude · P1 neutral | 60.2% | 56–64 | 487 |
| claude · P4 symmetry | 62.2% | 58–66 | 487 |
| claude · P3 permissive | 62.3% | 58–66 | 488 |
| mistral · P2 strict | 62.6% | 58–67 | 500 |
| mistral · P4 symmetry | 65.4% | 61–69 | 500 |
| mistral · P3 permissive | 68.0% | 64–72 | 500 |
| mistral · P5 screening | 68.9% | 65–73 | 499 |

**Range 57.2–68.9%, median 62.3%** — a 12-point spread across ten
operationalisations.

| domain | n | range | median |
|---|---|---|---|
| antimicrobial | 104 | 84.6–97.1% | 93.3% |
| oncology | 168 | 78.6–88.7% | 86.8% |

### Domain resolution

Both models agree on **429/500 (86%)**: oncology 168, antimicrobial 104,
other_therapeutic 67, not_a_drug_combination 51, environmental_agricultural 39.
The remaining 71 papers are `domain_ambiguous` and excluded from per-domain
tables only, making the per-domain counts mild under-estimates.

### Consensus and diagnostics

70% of papers (339/486 with a complete row) are unanimous across all ten
configurations — 107 at 0/10 and 232 at 10/10 — so the construct is crisp for
most papers, with a thin middle band.

| diagnostic | result |
|---|---|
| P2(strict)=yes with P3(permissive)=no | 7 cells of ~988 pairs (0.7%) |
| out-of-scope papers scored yes | 26 cells of 510 (5% scope-guard leakage) |

The strict ⊂ permissive nesting holds in aggregate on both arms, so the 0.7%
cell-level violations are model noise rather than a misapplied prompt.

### Implied magnitude

Gated corpus 10,214 over 16 years:

| | papers/year |
|---|---|
| antimicrobial | **131–150** |
| oncology | **196–222** |
| all domains (includes out-of-scope) | 365–440 |

Compare the current manuscript figures of 76 and 64 per year. The increase
follows from the broader construct — "presents synergy as desirable" rather than
"treats interaction labels as a proxy for combination quality".

---

## Open decisions

1. **main.tex:92** currently claims "over 24,000 papers that assess interaction
   labels" — that is the score≥1 population, which is 1.4% YES at its lower
   half. Needs rewording to the gated figure regardless of how the screening
   turns out.
2. **main.tex:94** states "76 and 64 peer-reviewed publications per year".
   To be replaced once the grid has run, at the granularity the design
   supports.


---

## Pilot run (n = 25, 300 calls)

Run before the main screening to check for breakage, not calibration — at n = 25
a single rate carries roughly ±18pp.

| check | result |
|---|---|
| domain agreement between models | 83% (19/23) |
| domain disagreements | 3 of 4 involve the `not_a_drug_combination` boundary; oncology and antimicrobial agreed perfectly |
| outcome yes-rate, all 10 configurations | 67–76% |
| per-paper consensus | strongly bimodal — 18/24 unanimous (5 at 0/10, 13 at 10/10) |
| coherence: P2=yes with P3=no | 1 cell (~4%) |
| scope-guard leakage | 0 |
| Sonnet refusals | 7/150 cells (4.7%), 2 papers |

**Attribution of synergy claims — considered and deliberately not filtered.**
The pilot's yes-rate is 2.5× the previous run, and papers were found scoring
"yes" on the strength of synergy claims attributed to prior work (a phase I/IIa
trial opening "integrin inhibition using cilengitide has shown synergy with
chemotherapy ... in vitro"). A rule excluding such claims was drafted and tested:
it moved both models to "no" on that paper while leaving a positive control at
"yes", so it was technically effective.

It was **rejected on construct grounds**. Citing another group's synergy finding
approvingly, as the rationale for one's own trial, is itself evidence that the
authors treat synergy as desirable — which is the construct being measured. The
prompts therefore judge the abstract as presented, without an attribution filter,
and the pilot's rate stands as a measurement rather than an artifact.

One consequence to carry forward: at ~72% of gated papers the implied figure is
roughly 460/year, at the upper end of "hundreds per year".

Note that a tight consensus across configurations is *not* by itself a defect —
under the meta-analysis framing the ten configurations are ten researchers
operationalising the construct slightly differently, and agreement is a result.
What made this a defect rather than a finding is that P3's criteria are a strict
superset of P2's, so identical output indicated the distinguishing clause was
not being applied.
