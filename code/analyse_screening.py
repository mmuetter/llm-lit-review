"""Analyse the multiverse screening grid and report per-configuration rates.

Treats the ten model-by-prompt configurations as replicate operationalisations
and reports their distribution, rather than pooling them into one estimate.
"""

import collections
import json
import math
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "data" / "screening_multiverse"
CORPUS_PATH = Path(__file__).parent.parent / "data" / "pubmed_results_all_years.json"

MODELS = ["mistral-large-2512", "claude-sonnet-5"]
PROMPTS = ["P2_strict", "P1_neutral", "P3_permissive", "P4_symmetry", "P5_screening"]
OUT_OF_SCOPE = "not_a_drug_combination"
REPORTED_DOMAINS = ["antimicrobial", "oncology"]
GATED_CORPUS_SIZE = 10214
WINDOW_YEARS = 16
Z_SCORE = 1.96


def load_successful(stage):
    """Load successful cells from a stage checkpoint, keyed by unit."""
    path = RESULTS_DIR / f"{stage}.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {(r["pmid"], r["model"], r["task"]): r["result"] for r in records if "result" in r}


def load_failures(stage):
    """Count failures per model and category for a stage."""
    path = RESULTS_DIR / f"{stage}.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    successful = {(r["pmid"], r["model"], r["task"]) for r in records if "result" in r}
    failed = [r for r in records
              if "result" not in r and (r["pmid"], r["model"], r["task"]) not in successful]
    return collections.Counter((r["model"], r["error"].split(":")[-1].strip()[:24]) for r in failed)


def wilson_interval(successes, total):
    """Return the Wilson score interval for a proportion."""
    if not total:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1 + Z_SCORE**2 / total
    centre = (p + Z_SCORE**2 / (2 * total)) / denominator
    spread = Z_SCORE / denominator * math.sqrt(p * (1 - p) / total + Z_SCORE**2 / (4 * total**2))
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def resolve_domains(domain_cells, pmids):
    """Assign a domain where both models agree, else mark it ambiguous."""
    resolved = {}
    for pmid in pmids:
        votes = [domain_cells.get((pmid, m, "domain"), {}).get("domain") for m in MODELS]
        agreed = votes[0] is not None and votes[0] == votes[1]
        resolved[pmid] = votes[0] if agreed else None
    return resolved


def configuration_cells(outcome_cells, pmids, model, prompt, keep=None):
    """Return yes/no answers for one configuration over the given papers."""
    selected = pmids if keep is None else [p for p in pmids if keep(p)]
    return [outcome_cells[(p, model, prompt)]["synergy_desirable"]
            for p in selected if (p, model, prompt) in outcome_cells]


def rate_row(outcome_cells, pmids, model, prompt, keep=None):
    """Return counts, rate and confidence interval for one configuration."""
    answers = configuration_cells(outcome_cells, pmids, model, prompt, keep)
    yes = sum(a == "yes" for a in answers)
    low, high = wilson_interval(yes, len(answers))
    return {"model": model, "prompt": prompt, "n": len(answers), "yes": yes,
            "rate": yes / len(answers) if answers else 0.0, "low": low, "high": high}


def all_configurations(outcome_cells, pmids, keep=None):
    """Build one rate row per model-by-prompt configuration."""
    return [rate_row(outcome_cells, pmids, m, p, keep) for m in MODELS for p in PROMPTS]


def forest_line(row, width=34):
    """Render one configuration as a text forest-plot line."""
    bar = ["-"] * width
    for index, value in ((int(row["low"] * width), "["), (int(row["high"] * width) - 1, "]"),
                         (int(row["rate"] * width), "*")):
        bar[min(max(index, 0), width - 1)] = value
    label = f"{row['model'].split('-')[0][:8]:<8} {row['prompt']:<14}"
    return (f"  {label} {''.join(bar)} {100 * row['rate']:5.1f}% "
            f"[{100 * row['low']:.0f}-{100 * row['high']:.0f}]  n={row['n']}")


def consensus_counts(outcome_cells, pmids):
    """Count, per paper, how many configurations answered yes."""
    histogram = collections.Counter()
    complete = 0
    for pmid in pmids:
        answers = [outcome_cells[(pmid, m, p)]["synergy_desirable"]
                   for m in MODELS for p in PROMPTS if (pmid, m, p) in outcome_cells]
        if len(answers) == len(MODELS) * len(PROMPTS):
            histogram[sum(a == "yes" for a in answers)] += 1
            complete += 1
    return histogram, complete


def coherence_violations(outcome_cells, pmids):
    """Count cells where the strict prompt says yes but the permissive says no."""
    return [(p, m) for p in pmids for m in MODELS
            if outcome_cells.get((p, m, "P2_strict"), {}).get("synergy_desirable") == "yes"
            and outcome_cells.get((p, m, "P3_permissive"), {}).get("synergy_desirable") == "no"]


def scope_leakage(outcome_cells, resolved):
    """Count yes answers on papers both models called out of scope."""
    out_of_scope = [p for p, d in resolved.items() if d == OUT_OF_SCOPE]
    leaks = [(p, m, pr) for p in out_of_scope for m in MODELS for pr in PROMPTS
             if outcome_cells.get((p, m, pr), {}).get("synergy_desirable") == "yes"]
    return out_of_scope, leaks


def print_header(title):
    """Print a section heading."""
    print(f"\n{title}\n" + "=" * len(title))


def report_completeness(domain_cells, outcome_cells, pmids):
    """Report how much of the grid was answered."""
    print_header("GRID COMPLETENESS")
    expected = len(pmids) * len(MODELS) * (1 + len(PROMPTS))
    got = len(domain_cells) + len(outcome_cells)
    print(f"  {got}/{expected} cells answered ({100 * got / expected:.1f}%)")
    for stage in ("domain", "outcome"):
        for (model, category), count in sorted(load_failures(stage).items()):
            print(f"    missing [{stage}] {model}: {count} ({category})")


def report_domains(resolved):
    """Report domain resolution and agreement."""
    print_header("DOMAIN RESOLUTION")
    assigned = {p: d for p, d in resolved.items() if d}
    print(f"  both models agree: {len(assigned)}/{len(resolved)} "
          f"({100 * len(assigned) / len(resolved):.0f}%)")
    for domain, count in collections.Counter(assigned.values()).most_common():
        print(f"    {domain:28s} {count:4d}")


def report_configurations(outcome_cells, pmids, resolved):
    """Report the specification curve overall and for reported domains."""
    print_header("SPECIFICATION CURVE — % yes per configuration")
    rows = sorted(all_configurations(outcome_cells, pmids), key=lambda r: r["rate"])
    for row in rows:
        print(forest_line(row))
    rates = [r["rate"] for r in rows]
    print(f"\n  range {100 * min(rates):.1f}-{100 * max(rates):.1f}%  "
          f"median {100 * sorted(rates)[len(rates) // 2]:.1f}%")
    for domain in REPORTED_DOMAINS:
        keep = lambda p, d=domain: resolved.get(p) == d
        subset = sorted(all_configurations(outcome_cells, pmids, keep), key=lambda r: r["rate"])
        span = [r["rate"] for r in subset]
        print(f"  {domain:16s} n={subset[0]['n']:4d}  "
              f"range {100 * min(span):.1f}-{100 * max(span):.1f}%  "
              f"median {100 * sorted(span)[len(span) // 2]:.1f}%")


def report_consensus(outcome_cells, pmids):
    """Report the per-paper consensus histogram."""
    print_header("PER-PAPER CONSENSUS (yes-count across 10 configurations)")
    histogram, complete = consensus_counts(outcome_cells, pmids)
    for value in range(len(MODELS) * len(PROMPTS) + 1):
        if histogram[value]:
            bar = "#" * max(1, round(60 * histogram[value] / complete))
            print(f"  {value:2d}/10 {bar} {histogram[value]}")
    unanimous = histogram[0] + histogram[10]
    print(f"  unanimous: {unanimous}/{complete} ({100 * unanimous / complete:.0f}%)")


def report_checks(outcome_cells, pmids, resolved):
    """Report coherence and scope-guard diagnostics."""
    print_header("DIAGNOSTICS")
    violations = coherence_violations(outcome_cells, pmids)
    print(f"  P2(strict)=yes with P3(permissive)=no: {len(violations)} cells")
    out_of_scope, leaks = scope_leakage(outcome_cells, resolved)
    print(f"  papers both models call out of scope: {len(out_of_scope)}")
    print(f"    of which scored yes by some configuration: {len(leaks)} cells")


def report_magnitude(outcome_cells, pmids, resolved):
    """Report implied annual publication counts from the configuration range."""
    print_header("IMPLIED MAGNITUDE")
    rates = [r["rate"] for r in all_configurations(outcome_cells, pmids)]
    per_year = [GATED_CORPUS_SIZE * r / WINDOW_YEARS for r in rates]
    print(f"  gated corpus {GATED_CORPUS_SIZE} over {WINDOW_YEARS} years")
    print(f"  all domains: {min(per_year):.0f}-{max(per_year):.0f} papers/year")
    assigned = collections.Counter(d for d in resolved.values() if d)
    for domain in REPORTED_DOMAINS:
        share = assigned[domain] / sum(assigned.values())
        keep = lambda p, d=domain: resolved.get(p) == d
        span = [r["rate"] for r in all_configurations(outcome_cells, pmids, keep)]
        counts = [GATED_CORPUS_SIZE * share * r / WINDOW_YEARS for r in span]
        print(f"  {domain:16s} share {100 * share:.0f}%  "
              f"{min(counts):.0f}-{max(counts):.0f} papers/year")


def main():
    """Run every report over the screening grid."""
    domain_cells = load_successful("domain")
    outcome_cells = load_successful("outcome")
    pmids = sorted({key[0] for key in domain_cells} | {key[0] for key in outcome_cells})
    resolved = resolve_domains(domain_cells, pmids)
    report_completeness(domain_cells, outcome_cells, pmids)
    report_domains(resolved)
    report_configurations(outcome_cells, pmids, resolved)
    report_consensus(outcome_cells, pmids)
    report_checks(outcome_cells, pmids, resolved)
    report_magnitude(outcome_cells, pmids, resolved)


if __name__ == "__main__":
    main()
