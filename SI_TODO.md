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

## Conceptual figure (main text; 1 open)
Mockup script: `checkerboard_mockup/checkerboard_mockup.py` (simulated surfaces);
the figure is copied to `main/figures/checkerboard.pdf`.
- [x] Text after the "treatment effects directly" paragraph (main.tex 112-114)
- [x] Figure block and caption (fig:checkerboard), pushed to Overleaf
- [ ] F1/1 Optional polish: label the isobole and MIC contour, colour-blind
      check of the red-blue scale, figure width (currently 0.48 columnwidth);
      optional citation for "underrepresented" (Lehar et al. 2009, Nat Biotechnol,
      selectivity of combinations on disease vs control cells; verify first)
