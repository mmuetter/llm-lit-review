# Changes for the stratified rerun

Each item is tagged by what it waits on:
- **[now]** wording or structure, doable before any results
- **[results]** needs both models' classifications and `stratified_estimates.py`

Open items carry a counter (e.g. S2/7); the breakdown is in each heading.
Pure number fill-ins are applied directly; wording needs approval.

## Decided
- **Headline sums all scores** (2026-09-21). No >=2 threshold anywhere in the paper.
- **Synergy-term gate** (2026-09-21): eligible papers must contain synergy,
  synergism or synergistic in title/abstract (exact terms, conservative).
  Found via a 100-paper check of score 1; patched sample (823 reused, 183 new).
- **Prompts unchanged.**
- **Sample-level counts are not flagged** as unweighted; left implicit.

## Pipeline (2 open)
- [x] Enumerate and date score 1; rebuild scores 2-6 on 2026-09-21 (identical to August)
- [x] Synergy gate enumerated (170,408 PMIDs, all years exact); gated sample v4 drawn
- [x] Sonnet on v4 (complete; refusals only)
- [ ] P1/2 Mistral on v4 (running)
- [ ] P2/2 `stratified_estimates.py` -> numbers, figures, trend

## Supplementary information (7 open: all results)
- [x] Aim, section titles, threshold paragraph, Table 1 caption and counts
- [x] Gate sentence (2.1), pool size, draws, sample size, cell count
- [x] Table 2 caption; per-score table structure (tab:scores)
- [x] Section 4: opening, formula, definitions
- [x] Reproducibility: single retrieval date, date-range split
- [ ] S1/7 [results] Per-score table: rates and papers/year
- [ ] S2/7 [results] 3.2 outcome rates, unanimity counts, Table 2
- [ ] S3/7 [results] 3.1 domain paragraph: weights, agreement counts
- [ ] S4/7 [results] 3.3 missing cells: refusal and failure counts
- [ ] S5/7 [results] 4: domain-wise counts, trend, Pearson (text and timeline caption)
- [ ] S6/7 [results] Final figures (both models)
- [ ] S7/7 [results] Zenodo ID

## Main text (1 open: results)
- [x] Lit-review paragraph: 166,349 publications that mention synergy
- [x] "stratified random sample of 1,006"
- [ ] M1/1 [results] "hundreds per year" -> thousands; fields, trajectory;
      abstract ("hundreds of publications each year")

## Conceptual figure (main text; not yet integrated, 3 open)
Mockup in `checkerboard_mockup/` (script + pdf/png, simulated surfaces). Frame:
toxicity is underrepresented in the interaction literature, although it is a
natural complement to the treatment effect (same checkerboard format).
- [ ] F1/3 [now] Text after main.tex line 111 (end of the "treatment effects
      directly" paragraph), wording agreed:
      "Toxicity is a natural complement to the treatment effect, yet it is
      underrepresented in the interaction literature, even though it can be
      measured in the same checkerboard format. Overlaying both shows which
      mixing ratio achieves the strongest effect at a given toxicity level,
      while remaining comparable between combinations (\autoref{fig:checkerboard})."
- [ ] F2/3 [now] Figure block + caption (label `fig:checkerboard`); caption must
      say the surfaces are simulated, define the colour scale (net growth rate;
      killing red), the toxicity isobole and the star (strongest killing on it);
      copy the pdf into main/, check graphicx in the class
- [ ] F3/3 [now] Optional polish: label the isobole and MIC contour, axis and
      colour-bar labels (psi / chi notation), colour-blind check of the red-blue scale
