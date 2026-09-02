"""Driver: test the a-priori-valuation candidate for the P3 slot, n=100 Mistral."""

from p2_iterate import run_candidate, test_set
from prompts import OUTCOME_PROMPTS

APRIORI = """Answer "yes" only if the paper's own stated aim or rationale treats
synergy as the outcome being sought — the study is motivated by
finding synergistic combinations specifically, treating synergy as
inherently more valuable than antagonistic or additive outcomes.
Answer "no" if the study is neutral about which interaction type it
expects, even if synergy is found and reported favourably."""

APRIORI_V2 = """Answer "yes" only if the paper's own stated aim or rationale treats
synergy as the outcome being sought — the study is motivated by
finding synergistic combinations specifically, treating synergy as
inherently more valuable than antagonistic or additive outcomes.
Answer "no" if the study is neutral about which interaction type it
expects, or in exploring the mechanistic reasons for synergy"""

papers = test_set()
print(f"n={len(papers)} papers, fixed seed\n")
run_candidate("P1_neutral (current)   ", OUTCOME_PROMPTS["P1_neutral"], papers)
run_candidate("P2_mechanism (final)   ", OUTCOME_PROMPTS["P2_mechanism"], papers)
run_candidate("a-priori v1             ", APRIORI, papers)
run_candidate("a-priori v2 (mech excl)", APRIORI_V2, papers)
