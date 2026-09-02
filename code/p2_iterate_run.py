"""Driver: compare P2 wording candidates against known anchors, same 100 papers."""

from p2_iterate import run_candidate, test_set
from prompts import OUTCOME_PROMPTS

OLD_PROMPT = """Does this paper treat synergy as a marker of combination quality? Answer
"yes" if it explicitly claims synergistic labels indicate promise or
efficacy, or if it screens many combinations, implying labels identify
the most effective ones. Answer "no" if it focuses on mechanistic
understanding of why combinations work (labels are secondary or not
central)."""

PREVIOUS_P2_STRICT = """Answer "yes" only if the paper explicitly evaluates a synergistic result
positively — calling the combination promising, effective, advantageous,
or a candidate for further development on the strength of the interaction
label. Reporting synergy without such an evaluation is "no"."""

TESTED_P2_MECHANISM = """Answer "no" if the paper's own interpretation treats the interaction
primarily as a route to mechanistic or classificatory insight, with no
accompanying claim of therapeutic promise or advantage. Discussing
mechanism alongside an explicit favourable claim does not disqualify —
answer "yes" in that case. Answer "no" only when no favourable claim is
made anywhere in the paper's own conclusions."""

DROP_ONLY = """Answer "no" if the paper's own interpretation treats the interaction
primarily as a route to mechanistic or classificatory insight, with no
accompanying claim of therapeutic promise or advantage. Discussing
mechanism alongside an explicit favourable claim does not disqualify —
answer "yes" in that case. Answer "no" when no favourable claim is
made anywhere in the paper's own conclusions."""

papers = test_set()
print(f"n={len(papers)} papers, fixed seed\n")
run_candidate("old prompt (2026-06, true)", OLD_PROMPT, papers)
