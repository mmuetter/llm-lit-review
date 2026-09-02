# Design decisions

Why the pipeline is built the way it is, including approaches that were tried
and rejected.

**This file deliberately contains no result numbers.** The supplementary
(`supplementary/main.tex`) is authoritative for every reported figure; keeping
results out of here means the two cannot disagree. Operational numbers (failure
rates, limits) appear only where they *are* the reason for a decision.

---

## Why ten configurations instead of one screen

Any single prompt embodies one reading of a fuzzy construct. Rather than defend
one reading, we run two models across five prompts and report the distribution.
The configurations are treated as replicate operationalisations by notional
readers who interpret the question slightly differently — agreement between them
is a result, not a precondition.

This framing rules out most "pass/fail" gates on the output. A tight consensus
is a finding; a wide spread is a finding. Only *incoherence* is a defect, which
is why P4's criteria are a subset of P1's: privileging synergy over antagonism
entails presenting synergy favourably, so if P4 ever answers yes where P1
answers no, the model is not applying the distinguishing clause, and that is a
bug rather than a difference of opinion.

## Eligibility gate

**Rejected: MeSH descriptors.** Indexing by *Drug Synergism* / *Drug
Interactions* is curated and phrasing-independent, which is attractive. It fails
on two counts. Yeh, Tschumi & Kishony (2006) — a drug-interaction network study,
and among the most cited in the field — carries only two generic descriptors and
would be missed entirely. And MeSH indexing lags publication, so recent years
are substantially under-indexed, which would distort exactly the trend we report.

**Rejected: keyword matching on stored abstracts.** No usable operating point.
Requiring a named metric (FICI, Loewe, …) drops mechanistic and systems-biology
work that never names an index — biasing *toward* the checkerboard/FICI style of
paper most likely to answer yes. Accepting generic interaction language admits
half the corpus.

**Chosen: term-group scoring through PubMed.** Sixteen indicator-term groups,
each issued as its own PubMed query; a paper's score is the number of groups it
matches. Issuing them as queries rather than matching text ourselves means a
group can match via title, abstract, author keywords or MeSH — so vocabulary
differences are absorbed without depending on MeSH being present.

**Threshold chosen empirically, not by taste.** Scoring an earlier single-prompt
screen against the scale showed a monotonic relationship between score and the
rate at which papers were judged to treat labels as a quality marker. Score-1
papers are dominated by off-topic senses of *interaction* (parent–child
interaction therapy, drug–ultrasound interaction, protein interactions).

**Open — the candidate pool is structurally inconsistent with the scoring.**
Scoring is a count over sixteen groups; the retrieval pool is a conjunction
requiring a synergy/antagonism term AND the literal word "combination" AND a
method term. Two of those constraints are not expressible in the scoring, so the
pool is not implied by the groups — it is a separate, stricter filter underneath
them, an artifact of build order. Consequence: a paper computing FICI but never
writing "synergy" or "combination" is excluded despite scoring well. Measured
against FICI (a term with essentially no meaning outside drug-interaction work),
roughly a quarter of matching papers sit outside the pool. The clean design is
pool = score ≥ 1, gate = score ≥ 2, with no separate query; it is computable
despite the broad groups by querying all group *pairs*, since score ≥ 2 is the
union of pairwise intersections and per-paper group membership falls out of
which pairs a paper appears in. Not yet done.

## Sampling

The seeded shuffle is walked keeping papers whose abstract passes a
deterministic completeness filter, until the target count is reached.

**The stopping rule touches only completeness, never the outcome.** An earlier
proposal stopped once enough papers were "clear" — i.e. once the models agreed.
That is circular: the grid exists to measure disagreement, and pre-selecting for
agreement guarantees the answer. Completeness is evaluated before any
classification, so stopping on it cannot bias the rate.

Truncation detection is deterministic rather than model-judged, so the
denominator cannot move with the classification. The mid-token rule exists
because manual review missed truncations at 590 and 989 characters that a length
check passes but a trailing-token check catches.

## Domain as its own stage

**Decoupled from the outcome grid.** Domain is not a varied factor, so asking it
inside all ten configurations produced ten judgments that were not independent —
same model, differing only by whichever outcome prompt surrounded them. Any
variation between them is the outcome prompt bleeding into the domain call.

The payoff is in the analysis: because every configuration is scored against the
same domain assignment, denominators are identical across a row, so the spread
reflects differing numerators only. While domain lived inside each
configuration, a paper could be assigned different domains by different
configurations and the comparison was not like-for-like.

**Ordered decision rule, five categories.** An earlier nine-category flat list
put four categories below the size at which they could be reported and generated
disagreement at boundaries (neurology vs. anaesthesia, agricultural vs. clinical
antifungal). "First that applies" resolves overlaps deterministically.
`not_a_drug_combination` doubles as a gate-precision diagnostic.

**Domain runs first, but nothing is excluded on it.** Running it first is a cheap
smoke test before committing to the outcome grid. Excluding out-of-scope papers
before the grid would save little and would forfeit the scope-guard validation:
those papers should be answered "no" by every configuration, and any "yes"
reveals a leaking guard. It would also force a rule for the case where the two
models disagree about whether a paper is in scope. The in-scope restriction is
applied as an analysis filter instead.

## Safety refusals

Refused cells are excluded **cell by cell**, not paper by paper. Paper-level
exclusion would keep denominators uniform but discards good cells to correct a
bias well under a percentage point at the observed refusal rate.

**Server-side fallback to another model was rejected.** It would answer refused
cells with a different model and contaminate the model contrast — the one
comparison the two-arm design exists to make. Refusals are recorded with their
category and reported instead.

Because refusals are content-dependent they are not missing at random, so the
affected papers are attributed to domains using the other model's vote and the
resulting imbalance is reported.

## Construct

**Attribution filter: drafted, tested, rejected.** Papers were found answering
"yes" on the strength of synergy claims attributed to prior work. A rule
excluding such claims was written and tested; it moved both models to "no" on
the motivating case while leaving a positive control at "yes", so it worked.
It was rejected on construct grounds: citing another group's synergy finding
approvingly, as the rationale for one's own study, is itself evidence that the
authors treat synergy as desirable — which is what is being measured.

**No paraphrase pair.** An early design included two prompts differing only in
wording, to establish a noise floor. At the reported granularity the wording
floor does not change the claim, so all five prompts carry distinct constructs
instead.

**P2 redefined from evaluative-language strictness to mechanism exclusion.**
The original P2 required explicit evaluative language ("promising", "effective",
"advantageous") and was intended as the strict anchor of the range, but
empirically landed in the middle of it — P1 turned out stricter in practice
without asking for that language explicitly. Separately, a pre-multiverse
single-prompt run had excluded papers whose stated purpose was mechanistic,
and no current prompt tests that dimension at all — P4 and P5 approach it
obliquely (symmetry, screening purpose) but neither asks it directly. An A/B
test on 30 oncology papers under the old mechanistic-exclusion wording found
it over-fired: 13 of 14 papers it excluded discussed mechanism *alongside* an
explicit favourable claim, which the old wording didn't distinguish from
mechanism with no favourable claim at all (the Yeh/Kishony case). New P2
excludes only the latter.

**P2 loosened from "explicitly claims" to "explicitly or implicitly suggests."**
The corrected P2 above still read as unreasonably strict once real full-sample
numbers came in. Loosening the evidentiary bar for the yes-branch (implicit
suggestion now counts, not just explicit claims) softened it without touching
the mechanism-exclusion logic that P2 exists to test.

**P3 redefined from a leniency threshold to a-priori valuation.** The original
P3 varied the same axis as P1 (how lenient a bar for "favourable"), which made
it near-redundant with P1 in practice. Several replacement axes were tried and
rejected: a salience criterion ("recommends" vs. "reports") turned out to be
incoherent — stating a paper found a favourable effect functions as a
recommendation in scientific writing, there is no real category that sits
between the two. A "compares against alternatives" criterion moved the wrong
direction (more permissive than P1, not a novel low anchor). What survived is
whether the paper's own stated rationale treats synergy as the a priori sought
outcome, rather than judging the conclusion after the fact — a genuinely
different axis from P1 (conclusion-framing), P2/P5 (purpose), and P4
(symmetry). Note the empirical screens (n=25, n=100, Mistral) could never
separate this from P1 on the sampled subsets; the decision to keep it rests on
the axis being conceptually distinct, not on a demonstrated rate difference.
Folding a mechanism clause into the same prompt (excluding both "neutral about
outcome type" and "exploring mechanism" from yes) was kept deliberately
disjunctive rather than split into two prompts: only the final yes/no is ever
consumed, so which clause fired is not information the design needs, the same
as every other prompt already packing multiple conditions into one verdict.

**Scope guard.** Without it, prompts answer "yes" for any paper treating synergy
as a good thing — which includes essentially all materials and food-science work.
The guard is phrased as a condition rather than an assertion so it does not
presuppose that a paper qualifies.

## Operational

**Mistral request spacing: 2.5 s.** At 1 s, 18.5% of calls failed after five
retries; at 2.5 s, none failed across the pilot and the gap-fill. The limit sits
between the two. This was originally set at 2.5 s by hand and briefly reduced —
the reduction was a mistake.

**Resume must skip only successful cells.** The first checkpoint implementation
treated any recorded cell as complete, including failures, so a re-run would have
silently locked in the missing cells and every downstream rate would have been
computed on an incomplete grid with no error surfaced.

**Schemas are enforced through the API**, not requested in prose. Asked for JSON
in the prompt, one model returned a different field name, a different type and an
extra field. Both arms now enforce an identical schema, so malformed output
cannot occur and no parse-retry path is needed.

## Figures

**Per-year rates are not estimated separately.** With roughly thirty sampled
papers per year, a yearly rate carries an interval wide enough that plotting them
would render sampling noise as signal. The trend comes from the corpus counts,
which are measured exactly; the configurations appear as a spread band.

**Window extended to include 2025.** Live re-querying showed the 2025 jump is
not a database artifact: general PubMed volume grew ~8% 2024→2025 while the
gated topic query grew ~68%, continuing an accelerating multi-year trend, not a
step function. 2025's larger gated pool is folded in by drawing a
proportionally-sized addition and re-drawing the final reported sample from the
combined pool, so its year keeps the same per-paper sampling weight as every
other year rather than being capped to an average year's size.

**Colour encodes model, marker shape encodes prompt**, so identity never rests on
colour alone.
