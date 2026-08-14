"""Figures for the multiverse screening results.

Both figures plot extrapolated papers per year rather than within-sample counts.
Colour encodes the model, marker shape the prompt, so identity never rests on
colour alone.
"""

import collections
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analyse_screening import (GATED_CORPUS_SIZE, MODELS, PROMPTS, REPORTED_DOMAINS,
                               WINDOW_YEARS, all_configurations, load_successful,
                               resolve_domains)

DATA_DIR = Path(__file__).parent.parent / "data"
FIGURE_DIR = Path(__file__).parent.parent / "figures"
CORPUS_PATH = DATA_DIR / "pubmed_results_all_years.json"
TERM_SCORES_PATH = DATA_DIR / "pubmed_term_scores.json"

GATE_THRESHOLD = 2
FIRST_YEAR = 2010
LAST_YEAR = 2024
SWARM_DOMAINS = REPORTED_DOMAINS + ["other_therapeutic", "environmental_agricultural"]

MODEL_COLOURS = {"mistral-large-2512": "#0072B2", "claude-sonnet-5": "#D55E00"}
PROMPT_MARKERS = {"P2_strict": "o", "P1_neutral": "s", "P3_permissive": "^",
                  "P4_symmetry": "D", "P5_screening": "v"}
MARKER_SIZE = 34
MARKER_EDGE_WIDTH = 0.6
JITTER_WIDTH = 0.26
JITTER_SEED = 7
GRID_ALPHA = 0.25
AXIS_GREY = "#444444"
FIGSIZE_TIMELINE = (7.2, 4.2)
FIGSIZE_SWARM = (7.2, 4.2)


def gated_papers_per_year():
    """Count gated papers per publication year within the analysis window."""
    scores = json.loads(TERM_SCORES_PATH.read_text())
    corpus = json.loads(CORPUS_PATH.read_text())
    years = [int(p["year"]) for p in corpus
             if scores.get(p["pmid"], 0) >= GATE_THRESHOLD and p["year"].isdigit()]
    counts = collections.Counter(y for y in years if FIRST_YEAR <= y <= LAST_YEAR)
    return {year: counts.get(year, 0) for year in range(FIRST_YEAR, LAST_YEAR + 1)}


def configuration_rates(outcome_cells, pmids, keep=None):
    """Map each model-by-prompt configuration to its yes-rate."""
    return {(r["model"], r["prompt"]): r["rate"]
            for r in all_configurations(outcome_cells, pmids, keep)}


def domain_shares(resolved):
    """Return each domain's share of papers both models could resolve."""
    assigned = collections.Counter(d for d in resolved.values() if d)
    total = sum(assigned.values())
    return {domain: assigned[domain] / total for domain in assigned}


def style_axes(axes, ylabel, title):
    """Apply the shared recessive axis styling."""
    axes.set_ylabel(ylabel, color=AXIS_GREY)
    axes.set_title(title, loc="left", color=AXIS_GREY, fontsize=11)
    axes.grid(axis="y", alpha=GRID_ALPHA, linewidth=0.6)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(AXIS_GREY)
    axes.tick_params(colors=AXIS_GREY, labelsize=9)


def encoding_legend(axes, loc_model="upper left", loc_prompt="lower right"):
    """Draw separate legends for the model and prompt encodings."""
    model_handles = [plt.Line2D([], [], marker="o", linestyle="", color=MODEL_COLOURS[m],
                                markersize=6, label=m) for m in MODELS]
    prompt_handles = [plt.Line2D([], [], marker=PROMPT_MARKERS[p], linestyle="", color=AXIS_GREY,
                                 markersize=6, markerfacecolor="none",
                                 label=p.split("_")[1]) for p in PROMPTS]
    first = axes.legend(handles=model_handles, loc=loc_model, frameon=False, fontsize=8)
    axes.add_artist(first)
    axes.legend(handles=prompt_handles, loc=loc_prompt, frameon=False, fontsize=8, ncol=2)


def plot_timeline(rates, per_year, path):
    """Plot extrapolated papers per year for every configuration, with a trend."""
    figure, axes = plt.subplots(figsize=FIGSIZE_TIMELINE)
    xs, ys = [], []
    for (model, prompt), rate in rates.items():
        years = sorted(per_year)
        values = [per_year[y] * rate for y in years]
        axes.scatter(years, values, s=MARKER_SIZE, marker=PROMPT_MARKERS[prompt],
                     facecolors="none", edgecolors=MODEL_COLOURS[model],
                     linewidths=MARKER_EDGE_WIDTH, alpha=0.85)
        xs.extend(years)
        ys.extend(values)
    slope, intercept = np.polyfit(xs, ys, 1)
    span = np.array([min(xs), max(xs)])
    axes.plot(span, slope * span + intercept, color=AXIS_GREY, linewidth=2, zorder=5)
    style_axes(axes, "estimated papers per year",
               f"Papers presenting synergy as desirable  (trend {slope:+.0f}/year)")
    encoding_legend(axes)
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def swarm_positions(count, centre):
    """Spread points around a category centre without implying an ordering."""
    offsets = np.linspace(-JITTER_WIDTH, JITTER_WIDTH, count)
    np.random.default_rng(JITTER_SEED).shuffle(offsets)
    return centre + offsets


def domain_values(outcome_cells, pmids, resolved, shares, domain):
    """Return each configuration's extrapolated annual count for one domain."""
    keep = lambda p: resolved.get(p) == domain
    rates = configuration_rates(outcome_cells, pmids, keep)
    scale = GATED_CORPUS_SIZE * shares[domain] / WINDOW_YEARS
    return {config: rate * scale for config, rate in rates.items()}


def plot_domain_swarm(outcome_cells, pmids, resolved, shares, path):
    """Plot the spread of annual estimates across configurations, by domain."""
    figure, axes = plt.subplots(figsize=FIGSIZE_SWARM)
    for index, domain in enumerate(SWARM_DOMAINS):
        values = domain_values(outcome_cells, pmids, resolved, shares, domain)
        ordered = list(values.items())
        positions = swarm_positions(len(ordered), index)
        for position, ((model, prompt), value) in zip(positions, ordered):
            axes.scatter(position, value, s=MARKER_SIZE, marker=PROMPT_MARKERS[prompt],
                         facecolors="none", edgecolors=MODEL_COLOURS[model],
                         linewidths=MARKER_EDGE_WIDTH)
        median = np.median([v for _, v in ordered])
        axes.plot([index - JITTER_WIDTH * 1.4, index + JITTER_WIDTH * 1.4], [median] * 2,
                  color=AXIS_GREY, linewidth=2, zorder=5)
    axes.set_xticks(range(len(SWARM_DOMAINS)))
    axes.set_xticklabels([d.replace("_", "\n") for d in SWARM_DOMAINS], fontsize=9)
    style_axes(axes, "estimated papers per year",
               "Annual estimate by domain, one point per configuration (bar = median)")
    encoding_legend(axes, loc_model="upper right", loc_prompt="center right")
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def main():
    """Build both result figures."""
    FIGURE_DIR.mkdir(exist_ok=True)
    domain_cells = load_successful("domain")
    outcome_cells = load_successful("outcome")
    pmids = sorted({k[0] for k in domain_cells} | {k[0] for k in outcome_cells})
    resolved = resolve_domains(domain_cells, pmids)
    shares = domain_shares(resolved)
    plot_timeline(configuration_rates(outcome_cells, pmids), gated_papers_per_year(),
                  FIGURE_DIR / "timeline_extrapolated.pdf")
    plot_domain_swarm(outcome_cells, pmids, resolved, shares,
                      FIGURE_DIR / "swarm_by_domain.pdf")
    print(f"wrote {FIGURE_DIR}/timeline_extrapolated.pdf and swarm_by_domain.pdf")


if __name__ == "__main__":
    main()
