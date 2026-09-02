"""Driver: find a P3 replacement that fills the gap between P2 (~62%) and
the P1/P4/P5 cluster (~76-86%), same cheap Mistral harness as the P2 search."""

from p2_iterate import run_candidate, test_set
from prompts import OUTCOME_PROMPTS

SALIENCE = """Answer "yes" only if the paper explicitly recommends, selects, or
highlights a specific combination as the preferred or most promising
option — not merely reporting that it produced a synergistic or
favourable effect. Describing a favourable interaction without
recommending the combination for further use or development is "no"."""

COMPARATIVE = """Answer "yes" only if the paper claims the combination is better
than, or preferable to, treatment alternatives (such as monotherapy or
other combinations) on the strength of the interaction result. General
statements of efficacy without an explicit comparative claim are "no"."""

papers = test_set()
print(f"n={len(papers)} papers, fixed seed\n")
run_candidate("P1_neutral (current)   ", OUTCOME_PROMPTS["P1_neutral"], papers)
run_candidate("P2_mechanism (final)   ", OUTCOME_PROMPTS["P2_mechanism"], papers)
run_candidate("salience candidate     ", SALIENCE, papers)
run_candidate("comparative candidate  ", COMPARATIVE, papers)
