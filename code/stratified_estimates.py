"""Per-score extrapolation of the stratified screening grid, summed across scores.

Within one score the sample is uniform, so each stratum is estimated with the
same functions as the pooled analysis and scaled by its own population; the
strata are then added up. Uniform-sample analyses are the one-stratum case.
"""

import json
import math
import statistics
from collections import Counter, defaultdict

import numpy as np
from scipy import stats

import analyse_screening
from analyse_screening import (DATA_DIR, MODELS, PROMPTS, REPORTED_DOMAINS, Z_SCORE,
                               domain_shares, domain_weights, load_successful, rate_row,
                               weights_for)
from plot_results import (ALL_CATEGORY, SWARM_CATEGORIES, apply_journal_style,
                          plot_swarm_values, plot_timeline_series)
from sampling import (FIRST_YEAR, LAST_YEAR, SCORE1_YEARS_PATH, gated_years,
                      load_stratified_sample, synergy_strata)

STRATIFIED_RESULTS_DIR = DATA_DIR / "screening_v3"

ALL_DOMAINS = ALL_CATEGORY
SWARM_DOMAINS = [category for category in SWARM_CATEGORIES if category != ALL_CATEGORY]
WINDOW_YEARS = LAST_YEAR - FIRST_YEAR + 1
CONFIGURATIONS = [(model, prompt) for model in MODELS for prompt in PROMPTS]
ALL_SCORES = (1, 2, 3, 4, 5, 6)
HEADLINE_SCORES = ALL_SCORES


def configuration_rows(outcome_cells, pmids, weights=None):
    """Return each configuration's rate row over one set of papers."""
    return {(m, p): rate_row(outcome_cells, pmids, m, p, weights) for m, p in CONFIGURATIONS}


def stratum_rates(outcome_cells, domain_cells, pmids):
    """Return per-domain configuration rows and domain shares for one stratum."""
    weights = domain_weights(domain_cells, pmids)
    shares = domain_shares(weights) if any(weights.values()) else {}
    rows = {ALL_DOMAINS: configuration_rows(outcome_cells, pmids)}
    for domain in SWARM_DOMAINS:
        rows[domain] = configuration_rows(outcome_cells, pmids, weights_for(weights, domain))
    return rows, shares


def stratum_counts(rows, shares, population):
    """Return annual problematic-paper counts per domain and configuration."""
    annual = population / WINDOW_YEARS
    counts = {ALL_DOMAINS: {c: annual * row["rate"] for c, row in rows[ALL_DOMAINS].items()}}
    for domain in SWARM_DOMAINS:
        counts[domain] = {c: annual * shares.get(domain, 0.0) * row["rate"]
                          for c, row in rows[domain].items()}
    return counts


def pmids_by_score(papers, answered):
    """Group the answered sampled PMIDs by their score stratum."""
    grouped = defaultdict(list)
    for paper in papers:
        if paper["pmid"] in answered:
            grouped[paper["score"]].append(paper["pmid"])
    return grouped


def estimate_strata(papers, outcome_cells, domain_cells):
    """Return each stratum's configuration rows and domain shares."""
    answered = {key[0] for key in outcome_cells} | {key[0] for key in domain_cells}
    return {score: stratum_rates(outcome_cells, domain_cells, pmids)
            for score, pmids in sorted(pmids_by_score(papers, answered).items())}


def summed_counts(strata_rates, populations, scores):
    """Add the annual counts of the given strata per domain and configuration."""
    total = defaultdict(lambda: defaultdict(float))
    for score in scores:
        if score not in strata_rates:
            continue
        rows, shares = strata_rates[score]
        for domain, by_configuration in stratum_counts(rows, shares, populations[score]).items():
            for configuration, count in by_configuration.items():
                total[domain][configuration] += count
    return total


def spread(values):
    """Return the median, minimum and maximum of a set of values."""
    values = list(values)
    return statistics.median(values), min(values), max(values)


def pooled_rate(strata_rates, populations, scores, configuration):
    """Return one configuration's population-weighted rate and 95% interval."""
    present = [s for s in scores if s in strata_rates]
    total = sum(populations[s] for s in present)
    rows = [(populations[s] / total, strata_rates[s][0][ALL_DOMAINS][configuration])
            for s in present]
    rate = sum(share * row["rate"] for share, row in rows)
    variance = sum(share ** 2 * row["rate"] * (1 - row["rate"]) / row["n"]
                   for share, row in rows if row["n"])
    margin = Z_SCORE * math.sqrt(variance)
    return rate, max(0.0, rate - margin), min(1.0, rate + margin)


def populations_by_year():
    """Map each score to its eligible synergy-term paper count per year."""
    years = {**gated_years(), **json.loads(SCORE1_YEARS_PATH.read_text())}
    by_year = defaultdict(Counter)
    for score, pmids in synergy_strata().items():
        for pmid in pmids:
            by_year[score][years[pmid]] += 1
    return by_year


def annual_series(strata_rates, by_year, scores):
    """Return each configuration's summed estimate per year across strata."""
    years = range(FIRST_YEAR, LAST_YEAR + 1)
    present = [s for s in scores if s in strata_rates]
    return {c: {y: sum(by_year[s][y] * strata_rates[s][0][ALL_DOMAINS][c]["rate"]
                       for s in present) for y in years}
            for c in CONFIGURATIONS}


def trend_statistics(series, by_year, scores):
    """Return the configuration-mean slope and the pool's year-level Pearson r."""
    years = list(range(FIRST_YEAR, LAST_YEAR + 1))
    mean_by_year = [np.mean([series[c][y] for c in CONFIGURATIONS]) for y in years]
    slope = float(np.polyfit(years, mean_by_year, 1)[0])
    pool = [sum(by_year[s][y] for s in scores) for y in years]
    correlation, p_value = stats.pearsonr(years, pool)
    return slope, correlation, p_value


def report_scores(strata_rates, sampled):
    """Print the per-score table: population, sample, rate and annual count."""
    print("\nPER SCORE (median and range across configurations)")
    for score, (rows, shares) in strata_rates.items():
        rates = [row["rate"] for row in rows[ALL_DOMAINS].values()]
        counts = stratum_counts(rows, shares, sampled[score]["population"])[ALL_DOMAINS]
        rate_median, rate_low, rate_high = spread(rates)
        count_median, count_low, count_high = spread(counts.values())
        print(f"  score {score}: N {sampled[score]['population']:7d}  n {sampled[score]['kept']:4d}  "
              f"rate {100 * rate_median:5.1f}% ({100 * rate_low:.1f}-{100 * rate_high:.1f})  "
              f"{count_median:7.1f} ({count_low:.1f}-{count_high:.1f}) papers/year")


def report_totals(strata_rates, populations, label, scores):
    """Print the summed annual counts for one set of scores, per domain."""
    total = summed_counts(strata_rates, populations, scores)
    print(f"\n{label} (scores {', '.join(map(str, scores))})")
    for domain in [ALL_DOMAINS, *REPORTED_DOMAINS]:
        median, low, high = spread(total[domain].values())
        print(f"  {domain:14s} median {median:7.1f}  range {low:7.1f}-{high:7.1f} papers/year")


def report_configurations(strata_rates, populations, scores):
    """Print each configuration's pooled rate with its stratified interval."""
    print(f"\nCONFIGURATION RATES, pooled over scores {', '.join(map(str, scores))}")
    rows = [(c, *pooled_rate(strata_rates, populations, scores, c)) for c in CONFIGURATIONS]
    for (model, prompt), rate, low, high in sorted(rows, key=lambda row: row[1]):
        print(f"  {model:20s} {prompt:14s} {100 * rate:5.1f}%  ({100 * low:.0f}-{100 * high:.0f})")


def build_figures(strata_rates, populations, scores):
    """Draw both result figures for the given scores and report the trend."""
    apply_journal_style()
    total = summed_counts(strata_rates, populations, scores)
    plot_swarm_values({category: total[category] for category in SWARM_CATEGORIES},
                      "swarm_by_category.pdf")
    by_year = populations_by_year()
    series = annual_series(strata_rates, by_year, scores)
    plot_timeline_series(series, "timeline_extrapolated.pdf")
    slope, correlation, p_value = trend_statistics(series, by_year, scores)
    print(f"\nTREND slope {slope:+.1f} papers/year, Pearson r = {correlation:.3f}, "
          f"p = {p_value:.2e} (n = {WINDOW_YEARS} years)")


def main():
    """Report per-score and summed estimates and draw the headline figures."""
    analyse_screening.RESULTS_DIRS = [STRATIFIED_RESULTS_DIR]
    papers, sampled = load_stratified_sample()
    populations = {score: s["population"] for score, s in sampled.items()}
    strata_rates = estimate_strata(papers, load_successful("outcome"), load_successful("domain"))
    report_scores(strata_rates, sampled)
    report_totals(strata_rates, populations, "HEADLINE", HEADLINE_SCORES)
    report_totals(strata_rates, populations, "ALL SCORES", ALL_SCORES)
    report_configurations(strata_rates, populations, HEADLINE_SCORES)
    build_figures(strata_rates, populations, HEADLINE_SCORES)


if __name__ == "__main__":
    main()
