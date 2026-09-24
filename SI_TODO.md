# SI changes for the simple synerg* design

Design fixed 2026-09-23 (see DECISIONS.md, last section). The stratified
version of this checklist and of the SI is at git tag `stratified-v4`.
Pure number fill-ins are applied directly; wording needs approval.
Line numbers refer to `supplementary/main.tex` as of 2026-09-23.

Passages 1-12 were agreed and applied on 2026-09-23 (supplementary 556d830).
Numbers that depend on the run are marked \textbf{XX} in main.tex.

## Results
All run-dependent numbers filled 2026-09-24 from the complete run (both
models; Sonnet refusals retried once, 90 of 91 repeated). Report:
`data/analysis_v5.txt`.

## Open (before forwarding / sending to Roland)
- Antimicrobial precision: ~75 sampled papers (weighted); enlarge the sample?
- Main l134 "mostly from oncology and antimicrobial research": holds (~70% of
  the total), but other therapeutic (~1,000/yr) exceeds antimicrobial (~750/yr).
- SI l98 failure reasons changed to "rate limits or server errors" (the run's
  actual 429/503 errors); check wording.
- Coherence diagnostic: 91 cells with P4 = yes but P1 = no (DECISIONS calls
  this a defect); inspect before sending.
- Passage 13 (back-reference to the stratified analysis): drop if it stays
  unmentioned.
- Zenodo ID (SI l168).

## Main text
Done 2026-09-23 (main e8a11be, ca586f0): pool 219,871, "a random sample of
1,000", "thousands" in l26 and l134. Check "thousands", "mostly oncology and
antimicrobial" and "clear upwards trajectory" against the final numbers.
