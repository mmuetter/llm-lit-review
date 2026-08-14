"""Prompts and enforced output schemas for the multiverse screening design.

Five outcome prompts vary the construct; one domain prompt is not a varied
factor. Both arms enforce identical JSON schemas.
"""

SCOPE_GUARD = """Answer "no" if this paper is not about a combination of drugs or other
chemical agents acting on an organism, cell, or pathogen — regardless of
how it uses the word "synergy". Materials, food chemistry, and
epidemiological risk-factor studies are "no"."""

OUTCOME_PROMPTS = {
    "P1_neutral": """Does this paper present synergy (a favourable drug-interaction label) as
desirable — as a point in the combination's favour? Judge the authors'
own findings and conclusions, not general background statements about
synergy.""",
    "P2_strict": """Answer "yes" only if the paper explicitly evaluates a synergistic result
positively — calling the combination promising, effective, advantageous,
or a candidate for further development on the strength of the interaction
label. Reporting synergy without such an evaluation is "no".""",
    "P3_permissive": """Answer "yes" if synergy is treated as favourable in any way — including
foregrounding synergistic combinations in the title or conclusions,
selecting or recommending them over non-synergistic ones, or presenting
synergy as the study's main positive result. Answer "no" only if
interaction labels are reported neutrally with no preference implied.""",
    "P4_symmetry": """Answer "yes" only where synergy is the favoured outcome and antagonism
the unfavourable one. A paper that treats synergy and antagonism
symmetrically — both as equally informative about mechanism, structure,
or classification — is NOT presenting synergy as desirable, even if it
measures drug interactions extensively.""",
    "P5_screening": """Consider why this study was done. If it screens or assays multiple drug
combinations and reports interaction labels for them, answer "yes" — such
screens are implicitly searching for favourable (synergistic) combinations —
UNLESS the stated purpose is mechanistic, structural, or classificatory
(understanding how or why interactions arise), in which case answer "no".
For studies of a single combination, answer "yes" only if the interaction
label is presented as evidence in the combination's favour.""",
}

DOMAIN_PROMPT = """Assign exactly one category, taking the FIRST that applies:

1. not_a_drug_combination — not a combination of drugs or other chemical
   agents acting on an organism, cell, or pathogen (materials science,
   food chemistry, epidemiological risk factors, plant physiology).
2. environmental_agricultural — targets pests, or concerns effects on
   non-target organisms or ecosystems, or is an agricultural application.
3. antimicrobial — targets bacteria or fungi in a medical or veterinary
   context.
4. oncology — targets cancer.
5. other_therapeutic — any other human or veterinary therapeutic use
   (antiviral, neurological, immunological, anaesthetic, cardiovascular)."""

DOMAIN_CATEGORIES = [
    "not_a_drug_combination",
    "environmental_agricultural",
    "antimicrobial",
    "oncology",
    "other_therapeutic",
]

OUTCOME_SCHEMA = {
    "type": "object",
    "properties": {"synergy_desirable": {"type": "string", "enum": ["yes", "no"]}},
    "required": ["synergy_desirable"],
    "additionalProperties": False,
}

DOMAIN_SCHEMA = {
    "type": "object",
    "properties": {"domain": {"type": "string", "enum": DOMAIN_CATEGORIES}},
    "required": ["domain"],
    "additionalProperties": False,
}


def paper_block(paper):
    """Render a paper's title and abstract as prompt input."""
    return f"Title: {paper['title']}\nAbstract: {paper['abstract']}"


def outcome_prompt(paper, prompt_name):
    """Build the full outcome prompt for one paper and prompt variant."""
    return f"{paper_block(paper)}\n\n{SCOPE_GUARD}\n\n{OUTCOME_PROMPTS[prompt_name]}"


def domain_prompt(paper):
    """Build the full domain-classification prompt for one paper."""
    return f"{paper_block(paper)}\n\n{DOMAIN_PROMPT}"
