"""Figures for the multiverse screening results.

Both figures plot extrapolated papers per year rather than within-sample counts,
over 2010-2025. The domain swarm scales the mean annual pool by each
configuration's overall rate; the timeline scales each year's pool by the rate
among that year's sampled papers. Colour encodes the model, marker shape the
prompt, so identity never rests on colour alone.
"""

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from analyse_screening import (MODELS, PROMPTS, REPORTED_DOMAINS, all_configurations,
                               domain_shares, domain_weights, final_sample_pmids,
                               headline_fraction, headline_weights, load_successful,
                               weights_for)
from analyse_screening import gated_papers_per_year as load_gated_papers_per_year
from sampling import ELIGIBLE_YEARS_PATH

DATA_DIR = Path(__file__).parent.parent / "data"
FIGURE_DIR = Path(__file__).parent.parent / "figures"
SUPPLEMENTARY_FIGURE_DIR = Path(__file__).parent.parent.parent / "supplementary" / "figures"

FIRST_YEAR = 2010
LAST_YEAR = 2025
ALL_CATEGORY = "all"
SWARM_CATEGORIES = [ALL_CATEGORY] + REPORTED_DOMAINS + ["other_therapeutic",
                                                        "environmental_agricultural"]

MODEL_COLOURS = {"mistral-large-2512": "#045C6E", "claude-sonnet-5": "#FF9127"}
MODEL_LABELS = {"mistral-large-2512": "mistral", "claude-sonnet-5": "sonnet"}
PROMPT_MARKERS = {"P2_mechanism": "o", "P1_neutral": "s", "P3_apriori": "^",
                  "P4_symmetry": "D", "P5_screening": "v"}
COLUMN_WIDTH_INCHES = 7.09
FIGSIZE_COLUMN = (COLUMN_WIDTH_INCHES, 3.40)
BASE_FONTSIZE = 9
TICK_FONTSIZE = 9
LEGEND_FONTSIZE = 8
TIMELINE_TICK_STEP = 2
CATEGORY_LABELS = {"all": "antimicrobial\n+ oncology", "antimicrobial": "antimicrobial",
                   "oncology": "oncology", "other_therapeutic": "other*",
                   "environmental_agricultural": "agricultural*"}

MARKER_SIZE = 38
MARKER_EDGE_WIDTH = 0.9
MARKER_ALPHA = 0.5
TREND_ALPHA = 0.5
TREND_WIDTH = 2.6
MEDIAN_WIDTH = 2.8
MEDIAN_HALF_SPAN = 0.23
JITTER_WIDTH = 0.28
JITTER_SEED = 7
GRID_ALPHA = 0.22
AXIS_GREY = "#333333"



def output_paths(name):
    """Return every directory the figure should be written to."""
    targets = [FIGURE_DIR]
    if SUPPLEMENTARY_FIGURE_DIR.parent.exists():
        SUPPLEMENTARY_FIGURE_DIR.mkdir(exist_ok=True)
        targets.append(SUPPLEMENTARY_FIGURE_DIR)
    return [directory / name for directory in targets]


def save_figure(figure, name):
    """Save one figure to the analysis folder and the supplementary folder."""
    for path in output_paths(name):
        figure.savefig(path)
    plt.close(figure)


def apply_journal_style():
    """Set a Times-compatible serif at journal-column sizes."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": BASE_FONTSIZE,
        "axes.labelsize": BASE_FONTSIZE,
        "xtick.labelsize": TICK_FONTSIZE,
        "ytick.labelsize": TICK_FONTSIZE,
        "axes.linewidth": 0.7,
    })


def gated_papers_per_year():
    """Return the true, live-queried gated-paper count for each analysis-window year."""
    counts = load_gated_papers_per_year()
    return {year: counts[year] for year in range(FIRST_YEAR, LAST_YEAR + 1)}


def annual_scale(per_year):
    """Return the mean number of gated papers per year in the window."""
    return sum(per_year.values()) / len(per_year)


def configuration_rates(outcome_cells, pmids, weights=None):
    """Map each model-by-prompt configuration to its yes-rate."""
    return {(r["model"], r["prompt"]): r["rate"]
            for r in all_configurations(outcome_cells, pmids, weights)}


def style_axes(axes, ylabel):
    """Apply the shared boxed, recessive axis styling."""
    axes.set_ylabel(ylabel, color=AXIS_GREY)
    axes.grid(axis="y", alpha=GRID_ALPHA, linewidth=0.6)
    axes.set_axisbelow(True)
    for spine in axes.spines.values():
        spine.set_visible(True)
        spine.set_color(AXIS_GREY)
        spine.set_linewidth(0.8)
    axes.tick_params(colors=AXIS_GREY, labelsize=TICK_FONTSIZE)


def encoding_handles():
    """Build legend handles: model colours first, then prompt marker shapes."""
    models = [plt.Line2D([], [], marker="o", linestyle="", markerfacecolor="none",
                         markeredgecolor=MODEL_COLOURS[m], markeredgewidth=MARKER_EDGE_WIDTH,
                         markersize=4.5, alpha=MARKER_ALPHA, label=MODEL_LABELS[m])
              for m in MODELS]
    prompts = [plt.Line2D([], [], marker=PROMPT_MARKERS[p], linestyle="", markerfacecolor="none",
                          markeredgecolor=AXIS_GREY, markeredgewidth=MARKER_EDGE_WIDTH,
                          markersize=4.5, alpha=MARKER_ALPHA, label=p.split("_")[0])
               for p in sorted(PROMPTS)]
    return models + prompts


def configuration_legend(axes, loc="upper left", ncol=1):
    """Draw one boxed legend combining the model and prompt encodings."""
    legend = axes.legend(handles=encoding_handles(), loc=loc, frameon=True,
                         fontsize=LEGEND_FONTSIZE, ncol=ncol, framealpha=1.0,
                         edgecolor=AXIS_GREY, labelspacing=0.25, handletextpad=0.4,
                         columnspacing=0.9, borderpad=0.35, handlelength=1.2)
    legend.get_frame().set_linewidth(0.6)


def draw_points(axes, xs, ys, model, prompt):
    """Scatter filled markers for one configuration."""
    axes.scatter(xs, ys, s=MARKER_SIZE, marker=PROMPT_MARKERS[prompt],
                 facecolors="none", edgecolors=MODEL_COLOURS[model],
                 linewidths=MARKER_EDGE_WIDTH, alpha=MARKER_ALPHA, zorder=3)


def yearly_rates(outcome_cells, pmids, weights):
    """Map each configuration to its antimicrobial-plus-oncology yes-share per sampled year."""
    years = json.loads(ELIGIBLE_YEARS_PATH.read_text())
    headline = headline_weights(weights)
    by_year = defaultdict(list)
    for pmid in pmids:
        by_year[years[pmid]].append(pmid)
    return {(model, prompt): {year: headline_fraction(outcome_cells, by_year[year], model, prompt,
                                                      headline)
                              for year in range(FIRST_YEAR, LAST_YEAR + 1)}
            for model in MODELS for prompt in PROMPTS}


def yearly_series(rates_by_year, per_year):
    """Scale each year's eligible pool by each configuration's rate for that year."""
    return {c: {year: per_year[year] * rates[year] for year in per_year}
            for c, rates in rates_by_year.items()}


def trend_statistics(series):
    """Return the slope and year-level Spearman correlation of the configuration mean."""
    years = sorted(next(iter(series.values())))
    mean_by_year = [np.mean([by_year[y] for by_year in series.values()]) for y in years]
    correlation, p_value = stats.spearmanr(years, mean_by_year)
    slope = float(np.polyfit(years, mean_by_year, 1)[0])
    return slope, correlation, p_value


def draw_trend(axes, xs, ys):
    """Draw a least-squares line through all plotted points."""
    fit = np.polyfit(xs, ys, 1)
    span = np.array([min(xs), max(xs)])
    axes.plot(span, np.polyval(fit, span), color=AXIS_GREY, linewidth=TREND_WIDTH,
              alpha=TREND_ALPHA, zorder=2)


def plot_timeline_series(series, path):
    """Plot per-configuration annual series with a pooled trend line."""
    figure, axes = plt.subplots(figsize=FIGSIZE_COLUMN)
    pooled_x, pooled_y = [], []
    for (model, prompt), by_year in series.items():
        years = sorted(by_year)
        draw_points(axes, years, [by_year[y] for y in years], model, prompt)
        pooled_x.extend(years)
        pooled_y.extend(by_year[y] for y in years)
    draw_trend(axes, pooled_x, pooled_y)
    axes.set_xticks(sorted(set(pooled_x))[::TIMELINE_TICK_STEP])
    style_axes(axes, "estimated papers per year")
    configuration_legend(axes, ncol=2)
    figure.tight_layout()
    save_figure(figure, path)


def swarm_positions(count, centre):
    """Spread points around a category centre without implying an ordering."""
    offsets = np.linspace(-JITTER_WIDTH, JITTER_WIDTH, count)
    np.random.default_rng(JITTER_SEED).shuffle(offsets)
    return centre + offsets


def category_values(outcome_cells, pmids, weights, shares, category, scale):
    """Return each configuration's annual estimate for one category."""
    if category == ALL_CATEGORY:
        headline = headline_weights(weights)
        return {(m, p): scale * headline_fraction(outcome_cells, pmids, m, p, headline)
                for m in MODELS for p in PROMPTS}
    rates = configuration_rates(outcome_cells, pmids, weights_for(weights, category))
    return {c: r * scale * shares[category] for c, r in rates.items()}


def plot_category_swarm(outcome_cells, pmids, weights, shares, scale, path):
    """Plot the spread of annual estimates across configurations, by category."""
    values = {category: category_values(outcome_cells, pmids, weights, shares, category, scale)
              for category in SWARM_CATEGORIES}
    plot_swarm_values(values, path)


def draw_category(axes, index, values):
    """Draw one category's configuration points and their median bar."""
    entries = list(values.items())
    for position, ((model, prompt), value) in zip(swarm_positions(len(entries), index), entries):
        draw_points(axes, [position], [value], model, prompt)
    median = float(np.median([value for _, value in entries]))
    axes.plot([index - MEDIAN_HALF_SPAN, index + MEDIAN_HALF_SPAN], [median] * 2,
              color=AXIS_GREY, linewidth=MEDIAN_WIDTH, alpha=TREND_ALPHA, zorder=2)


def plot_swarm_values(values_by_category, path):
    """Plot precomputed annual estimates per category and configuration."""
    figure, axes = plt.subplots(figsize=FIGSIZE_COLUMN)
    for index, category in enumerate(SWARM_CATEGORIES):
        draw_category(axes, index, values_by_category[category])
    axes.set_xticks(range(len(SWARM_CATEGORIES)))
    axes.set_xticklabels([CATEGORY_LABELS[c] for c in SWARM_CATEGORIES],
                         fontsize=TICK_FONTSIZE)
    style_axes(axes, "estimated papers per year")
    configuration_legend(axes, loc="upper right")
    figure.tight_layout()
    save_figure(figure, path)


def main():
    """Build both result figures and report the trend statistics."""
    apply_journal_style()
    FIGURE_DIR.mkdir(exist_ok=True)
    domain_cells = load_successful("domain")
    outcome_cells = load_successful("outcome")
    available = {k[0] for k in domain_cells} | {k[0] for k in outcome_cells}
    pmids = sorted(final_sample_pmids() & available)
    weights = domain_weights(domain_cells, pmids)
    per_year = gated_papers_per_year()
    series = yearly_series(yearly_rates(outcome_cells, pmids, weights), per_year)
    plot_timeline_series(series, "timeline_extrapolated.pdf")
    plot_category_swarm(outcome_cells, pmids, weights, domain_shares(weights),
                        annual_scale(per_year), "swarm_by_category.pdf")
    slope, correlation, p_value = trend_statistics(series)
    print(f"figures written to: {[str(d) for d in output_paths('')]}")
    print(f"window {FIRST_YEAR}-{LAST_YEAR}, mean gated {annual_scale(per_year):.0f}/year")
    print(f"trend slope {slope:+.1f} papers/year (mean across configurations, yearly rates)")
    print(f"Spearman rho = {correlation:.3f}, p = {p_value:.2e} (n = {len(per_year)} years)")


if __name__ == "__main__":
    main()
