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

**Resolved — the candidate pool was structurally inconsistent with the scoring.**
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
which pairs a paper appears in. Done in the September rerun: scores 2-6 come
from pairwise queries (`rebuild_gated.py`) and score 1 from exclusive queries
(`enumerate_score1.py`), see the last section.

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

**Per-year counts come from the pooled gate, not per-year queries.** PubMed's
`[dp]` field matches both the electronic and the print publication date, so a
paper e-published in one year and printed in the next is returned by two
year-filtered queries. Counting each year separately and summing therefore
double-counts straddlers: the old `year_gate_counts.py` reported 24,405 against
a gate holding 21,767 distinct papers, a 12% overstatement that propagated into
every extrapolated count. `year_gate_counts.py` now dates each gated PMID once
by its `sortpubdate` year, so the per-year series sums to the gate size by
construction and the two artifacts cannot drift apart again. The sample was
never affected: `sampling.py` draws from the deduplicated gate file, so only the
extrapolation base moved.

**The out-of-window papers were swapped, not redrawn — rerun before submission.**
Applying the latest-publication rule put 14 sampled papers in 2026, outside the
window. They were dropped and replaced by continuing the same seeded shuffle
rather than redrawing the sample, because removing PMIDs from the gate changes
the shuffle permutation and would have forced all 12,000 cells to be
reclassified. The result is statistically equivalent: a uniform draw from the
pool stays uniform once filtered on a paper-level property, and topping it back
up from the same shuffle keeps it uniform. It is not, however, reproducible from
a clean run of the seed, so the pipeline should be rebuilt end to end before
final submission, with the window filter applied at gate construction so no
out-of-window paper can enter the sample in the first place.

**Abstract extraction read only the text before the first markup tag.**
`article_record` built the abstract with `node.text`, which in ElementTree
returns the character data *preceding* an element's first child. Any abstract
containing `<sup>`, `<sub>` or `<i>` was therefore cut at that point, so
`IC<sub>50</sub>` yielded "IC" and the rest of the abstract was never read. The
same applied to titles via `findtext`. Both now use `itertext()`.

The defect was self-masking: most truncations stopped mid-token, so the
completeness filter discarded them, and a 31% rejection rate looked like a
property of PubMed rather than a bug. Corrected, the filter rejects 1.3%, not
31%. Two consequences for any run predating the fix -- roughly 30% of the sample
would differ under a correct draw, since the walk reached position 1,565 instead
of 1,011 to collect 1,000 papers, and about 8.5% of classified papers were
judged on truncated text, losing a median 67% of the abstract. The excluded
papers skew toward markup-heavy quantitative pharmacology, so unlike the
punctuation rule this exclusion is not plausibly outcome-neutral.

**Dating and the window filter run before sampling, not after.** A paper's year
is now the later of its print and electronic publication dates, both read from
the same efetch response. (This was first believed to match PubMed's
`sortpubdate`; it does not in 0.6% of papers -- see below.) The
previous source, `PubDate/Year`, returned nothing when the date was a MedlineDate
string and returned the earlier date whenever a paper's issue year preceded its
electronic one. `year_gate_counts.py` persists that mapping, and `gated_pmids`
filters on it, so an out-of-window paper can no longer enter the sample and be
excluded downstream. Sampling raises rather than proceeding if the mapping is
absent, which enforces the order: keywords, then dating and the window filter,
then the completeness filter, then the draw.

**Colour encodes model, marker shape encodes prompt**, so identity never rests on
colour alone.

**Dating uses the latest publication year everywhere, not `sortpubdate`.** The
pool was dated by `sortpubdate` while the sampler and the SI used the later of
the print and electronic years. On 900 pooled papers the two disagree for 0.6%,
always with `sortpubdate` in the earlier year, which matters at the window's
edges (a paper printed in 2026 but sorted into 2025 was counted as in-window).
`year_of` now takes the later of `pubdate` and `epubdate`, falling back to
`sortpubdate` only when both are absent, and the score-1 dating stores the raw
date strings so a rule change never requires refetching.

**The stored corpus is not used for abstracts.** `pubmed_results_all_years.json`
kept only the first section of structured abstracts: on a random 300 of its
records, 52% were shorter than a fresh fetch, typically ending after the
Background sentence (e.g. PMID 27050162: 330 of 1,583 characters). Such
fragments end in a full stop and pass the completeness filter, so the defect is
invisible downstream. 299 papers of the v2 sample came from this corpus. The
stratified draw fetches every record fresh.

## Stratified rerun (September 2026)

**The sample is stratified by group score, including score 1.** Following
Roland's suggestion, papers matching a single indicator group are sampled too,
removing the threshold as a design choice. Each score is its own stratum: 250
papers where the score has more, otherwise every paper (scores 5 and 6 are
censuses). Each stratum is estimated with the unchanged pooled functions --
within a stratum the draw is uniform -- scaled by its own population, and the
strata are summed. A uniform sample is the one-stratum case, and on the v2 data
the stratified code reproduces every reported figure exactly, which is how it
was verified. A single weight function (for example proportional to score)
cannot work here: score 1 is seventeen times the size of the pool, so it would
still take about 890 of 1,000 draws.

**Score-1 papers are enumerated by exclusive queries with date bisection.**
Single groups exceed PubMed's 9,999-record retrieval limit (2024 alone has
24,227 labelling-only papers), which is why the gate was built from pairwise
intersections and score 1 was never materialised. Each group's exclusive set
(`group NOT any other group`) is queried per year and bisected by date until
every slice is retrievable; every group-year was checked against PubMed's own
count and all 96 matched exactly. This replaces the SI's earlier score-1 count
of 372,093, which had no source in the code or data.

**Pooled configuration rates carry stratified intervals, not Wilson intervals.**
A rate pooled over strata is a population-weighted sum of stratum rates, so its
95% interval uses the stratified variance, the sum over strata of
(N_h/N)^2 p_h(1-p_h)/n_h. With one stratum this reduces to the normal
approximation, which agrees with the previous Wilson intervals to the reported
precision.


**Eligibility requires a synergy term in the title or abstract.** A hand check of
100 random score-1 papers (labelled by an LLM, not a human, against the outcome
prompts' construct) showed that Sonnet counted 2-12% of papers as presenting
synergy as desirable that the check did not: combination-therapy papers that
report a benefit but never mention synergy. Errors ran one way (Sonnet-only
"yes" 2-12, check-only "yes" 0-1 per prompt), so this was a bias, not noise.
Every paper the check judged "yes" contained "synerg", so the gate loses no true
positive. The gate is the three exact terms (synergy, synergism, synergistic),
not the wildcard `synerg*`: the wildcard adds 54,598 papers (2010-2025), and
the exact terms make the estimate conservative and match the keyword list the
SI describes. With the gate, agreement with the check is 96-98% across
prompts (88-97% before). The gate is applied before sampling, so gated-out
papers leave the eligible population instead of being counted as "no";
stratification then stays valid because each stratum is uniform. The gated pool
is 166,349 papers (scores 1-6: 146,881 / 17,037 / 2,137 / 287 / 6 / 1).

**The gated sample patches the ungated one.** Each score keeps the seeded order of
its earlier shuffle, skips papers failing the gate, and continues down the list
until 250 complete abstracts are reached, so it is the draw the gated stratum
would have produced from scratch. 823 of 1,006 papers (and their stored
answers) were reused; 183 are new. The gated population is exactly "all papers
with a synergy term", so stratification no longer changes what is estimated,
only how precisely each score and the total are known; both designs are
unbiased. The stratified sample is kept because the per-score rates are
informative and the classification is already done.

**All PubMed queries are from one snapshot (2026-09-21).** Scores 2-6 were
rebuilt from pairwise group queries on the same day as score 1
(`rebuild_gated.py`); the result was identical to the August pool (21,438
papers in the window, no paper changed score or year), so no redraw was needed.
PubMed's summary endpoint silently skipped 1,100 papers on the first dating
pass, so the script now refuses to finish while any paper is undated.

**The code folder holds only the current pipeline.** The earlier single-pool
scripts (`run_clean_*`, `run_p2*`, `p2/p3_*`, the 2025 spike analysis and other
one-off scripts) were removed; they remain in git history (commit `cdb7883` and
earlier). Dead code left inside `sampling.py`, `analyse_screening.py` and
`year_gate_counts.py` (the single-pool draw and loaders) is still to be removed
once the Mistral run has finished.
