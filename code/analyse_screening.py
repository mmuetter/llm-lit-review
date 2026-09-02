"""Analyse the multiverse screening grid and report per-configuration rates.

Treats the ten model-by-prompt configurations as replicate operationalisations
and reports their distribution, rather than pooling them into one estimate.
"""

import collections
import json
import math
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_DIRS = [DATA_DIR / "screening_final"]
FINAL_MANIFEST_PATH = DATA_DIR / "screening_sample_v2.json"
GATED_PAPERS_PER_YEAR_PATH = DATA_DIR / "gated_papers_per_year.json"

MODELS = ["mistral-large-2512", "claude-sonnet-5"]
PROMPTS = ["P2_mechanism", "P1_neutral", "P3_apriori", "P4_symmetry", "P5_screening"]
OUT_OF_SCOPE = "not_a_drug_combination"
REPORTED_DOMAINS = ["antimicrobial", "oncology"]
Z_SCORE = 1.96


def final_sample_pmids():
    """Return the pmids that make up the final reported sample."""
    manifest = json.loads(FINAL_MANIFEST_PATH.read_text())
    return {p["pmid"] for p in manifest["papers"]}


def gated_papers_per_year():
    """Load the true per-year gated-paper counts."""
    return {int(year): count for year, count in json.loads(GATED_PAPERS_PER_YEAR_PATH.read_text()).items()}


def stage_records(stage):
    """Load every record for a stage across all result directories."""
    records = []
    for results_dir in RESULTS_DIRS:
        path = results_dir / f"{stage}.jsonl"
        records += [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return records


def load_successful(stage):
    """Load successful cells from every stage checkpoint, keyed by unit."""
    return {(r["pmid"], r["model"], r["task"]): r["result"]
            for r in stage_records(stage) if "result" in r}


def load_failures(stage, pmids):
    """Count failures per model and category for a stage, restricted to pmids."""
    valid_tasks = set(PROMPTS) if stage == "outcome" else {"domain"}
    records = stage_records(stage)
    successful = {(r["pmid"], r["model"], r["task"]) for r in records if "result" in r}
    last_failure = {}
    for r in records:
        if "result" in r or r["pmid"] not in pmids or r["task"] not in valid_tasks:
            continue
        key = (r["pmid"], r["model"], r["task"])
        if key not in successful:
            last_failure[key] = r
    return collections.Counter((r["model"], r["error"].split(":")[-1].strip()[:24])
                               for r in last_failure.values())


def wilson_interval(successes, total):
    """Return the Wilson score interval for a proportion."""
    if not total:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1 + Z_SCORE**2 / total
    centre = (p + Z_SCORE**2 / (2 * total)) / denominator
    spread = Z_SCORE / denominator * math.sqrt(p * (1 - p) / total + Z_SCORE**2 / (4 * total**2))
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def domain_weights(domain_cells, pmids):
    """Split each paper's weight equally across the domains its models assigned."""
    weights = {}
    for pmid in pmids:
        votes = [domain_cells.get((pmid, m, "domain"), {}).get("domain") for m in MODELS]
        votes = [v for v in votes if v]
        weights[pmid] = {d: votes.count(d) / len(votes) for d in set(votes)} if votes else {}
    return weights


def weights_for(domain_weights_by_pmid, domain):
    """Return each paper's weight in one domain."""
    return {pmid: w.get(domain, 0.0) for pmid, w in domain_weights_by_pmid.items()}


def domain_shares(weights):
    """Return each domain's share of the total weighted paper mass."""
    mass = collections.Counter()
    for paper_weights in weights.values():
        for domain, weight in paper_weights.items():
            mass[domain] += weight
    total = sum(mass.values())
    return {domain: value / total for domain, value in mass.items()}


def resolve_domains(domain_cells, pmids):
    """Resolve each paper to a single domain, or None if the models disagree."""
    resolved = {}
    for pmid in pmids:
        votes = {domain_cells.get((pmid, m, "domain"), {}).get("domain") for m in MODELS}
        votes.discard(None)
        resolved[pmid] = votes.pop() if len(votes) == 1 else None
    return resolved


def rate_row(outcome_cells, pmids, model, prompt, weights=None):
    """Return the weighted rate and interval for one configuration."""
    pairs = [(weights.get(p, 0.0) if weights else 1.0,
              outcome_cells[(p, model, prompt)]["synergy_desirable"])
             for p in pmids if (p, model, prompt) in outcome_cells]
    total = sum(w for w, _ in pairs)
    yes = sum(w for w, a in pairs if a == "yes")
    low, high = wilson_interval(round(yes), round(total))
    return {"model": model, "prompt": prompt, "n": total, "yes": yes,
            "rate": yes / total if total else 0.0, "low": low, "high": high}


def all_configurations(outcome_cells, pmids, weights=None):
    """Build one rate row per model-by-prompt configuration."""
    return [rate_row(outcome_cells, pmids, m, p, weights) for m in MODELS for p in PROMPTS]


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
    """Count cells where the narrower prompt says yes but the broader one says no."""
    return [(p, m) for p in pmids for m in MODELS
            if outcome_cells.get((p, m, "P4_symmetry"), {}).get("synergy_desirable") == "yes"
            and outcome_cells.get((p, m, "P1_neutral"), {}).get("synergy_desirable") == "no"]


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
    """Report how much of the final sample's grid was answered."""
    print_header("GRID COMPLETENESS")
    expected = len(pmids) * len(MODELS) * (1 + len(PROMPTS))
    got = (sum(1 for k in domain_cells if k[0] in pmids)
           + sum(1 for k in outcome_cells if k[0] in pmids and k[2] in PROMPTS))
    print(f"  {got}/{expected} cells answered ({100 * got / expected:.1f}%)")
    for stage in ("domain", "outcome"):
        for (model, category), count in sorted(load_failures(stage, pmids).items()):
            print(f"    missing [{stage}] {model}: {count} ({category})")


def report_domains(resolved):
    """Report domain resolution and agreement."""
    print_header("DOMAIN RESOLUTION")
    assigned = {p: d for p, d in resolved.items() if d}
    print(f"  both models agree: {len(assigned)}/{len(resolved)} "
          f"({100 * len(assigned) / len(resolved):.0f}%)")
    for domain, count in collections.Counter(assigned.values()).most_common():
        print(f"    {domain:28s} {count:4d}")


def report_configurations(outcome_cells, pmids, weights):
    """Report the specification curve overall and for reported domains."""
    print_header("SPECIFICATION CURVE — % yes per configuration")
    rows = sorted(all_configurations(outcome_cells, pmids), key=lambda r: r["rate"])
    for row in rows:
        print(forest_line(row))
    rates = [r["rate"] for r in rows]
    print(f"\n  range {100 * min(rates):.1f}-{100 * max(rates):.1f}%  "
          f"median {100 * sorted(rates)[len(rates) // 2]:.1f}%")
    for domain in REPORTED_DOMAINS:
        subset = sorted(all_configurations(outcome_cells, pmids, weights_for(weights, domain)),
                        key=lambda r: r["rate"])
        span = [r["rate"] for r in subset]
        print(f"  {domain:16s} n={subset[0]['n']:.0f}  "
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
    print(f"  P4(symmetry)=yes with P1(neutral)=no: {len(violations)} cells")
    out_of_scope, leaks = scope_leakage(outcome_cells, resolved)
    print(f"  papers both models call out of scope: {len(out_of_scope)}")
    print(f"    of which scored yes by some configuration: {len(leaks)} cells")


def report_magnitude(outcome_cells, pmids, weights, per_year):
    """Report implied annual publication counts from the configuration range."""
    print_header("IMPLIED MAGNITUDE")
    mean_annual_gated = sum(per_year.values()) / len(per_year)
    rates = [r["rate"] for r in all_configurations(outcome_cells, pmids)]
    counts = [mean_annual_gated * r for r in rates]
    print(f"  mean gated papers/year {mean_annual_gated:.0f} "
          f"({min(per_year)}-{max(per_year)}, {len(per_year)} years)")
    print(f"  all domains: {min(counts):.0f}-{max(counts):.0f} papers/year")
    shares = domain_shares(weights)
    for domain in REPORTED_DOMAINS:
        share = shares[domain]
        span = [r["rate"] for r in all_configurations(outcome_cells, pmids, weights_for(weights, domain))]
        domain_counts = [mean_annual_gated * share * r for r in span]
        print(f"  {domain:16s} share {100 * share:.0f}%  "
              f"{min(domain_counts):.0f}-{max(domain_counts):.0f} papers/year")


def main():
    """Run every report over the screening grid."""
    domain_cells = load_successful("domain")
    outcome_cells = load_successful("outcome")
    pmids = sorted(final_sample_pmids() & ({key[0] for key in domain_cells} | {key[0] for key in outcome_cells}))
    resolved = resolve_domains(domain_cells, pmids)
    weights = domain_weights(domain_cells, pmids)
    report_completeness(domain_cells, outcome_cells, pmids)
    report_domains(resolved)
    report_configurations(outcome_cells, pmids, weights)
    report_consensus(outcome_cells, pmids)
    report_checks(outcome_cells, pmids, resolved)
    report_magnitude(outcome_cells, pmids, weights, gated_papers_per_year())


if __name__ == "__main__":
    main()
