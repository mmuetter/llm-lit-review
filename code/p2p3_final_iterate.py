"""n=100 Mistral test: the three surviving P3 candidates, plus a loosened P2."""

from p2_iterate import run_candidate, test_set
from prompts import OUTCOME_PROMPTS

COMPARATIVE = """Answer "yes" only if the paper claims the combination is better
than, or preferable to, treatment alternatives (such as monotherapy or
other combinations) on the strength of the interaction result. General
statements of efficacy without an explicit comparative claim are "no"."""

APRIORI_V1 = """Answer "yes" only if the paper's own stated aim or rationale treats
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

P2_LOOSENED = """Does this paper treat synergy as a marker of combination quality? Answer
"yes" if it explicitly or implicitly suggests that synergistic labels
indicate promise or efficacy, or if it screens many combinations,
implying labels identify the most effective ones. Answer "no" if it
focuses on mechanistic understanding of why combinations work (labels
are secondary or not central)."""

papers = test_set()
print(f"n={len(papers)} papers, fixed seed\n")
run_candidate("P1_neutral (anchor)    ", OUTCOME_PROMPTS["P1_neutral"], papers)
run_candidate("P2 current              ", OUTCOME_PROMPTS["P2_mechanism"], papers)
run_candidate("P2 loosened              ", P2_LOOSENED, papers)
run_candidate("P3 comparative           ", COMPARATIVE, papers)
run_candidate("P3 a-priori v1           ", APRIORI_V1, papers)
run_candidate("P3 a-priori v2           ", APRIORI_V2, papers)
