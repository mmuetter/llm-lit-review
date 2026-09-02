"""Preview the two result figures on the clean-restart sample, Mistral only.

Throwaway/exploratory: points the shared plotting code at the fresh sample and
screening_final/ results, and restricts to one model, without touching the
constants the real two-model pipeline will need once Sonnet completes.
"""

from pathlib import Path

import analyse_screening
import plot_results
from sampling import load_sample

DATA_DIR = Path(__file__).parent.parent / "data"
PREVIEW_FIGURE_DIR = Path(__file__).parent.parent / "figures_mistral_preview"

analyse_screening.RESULTS_DIRS = [DATA_DIR / "screening_final"]
analyse_screening.MODELS = ["mistral-large-2512"]
plot_results.MODELS = analyse_screening.MODELS
plot_results.FIGURE_DIR = PREVIEW_FIGURE_DIR
plot_results.SUPPLEMENTARY_FIGURE_DIR = PREVIEW_FIGURE_DIR


def main():
    """Build both figures against the Mistral-only clean-restart data."""
    plot_results.apply_journal_style()
    PREVIEW_FIGURE_DIR.mkdir(exist_ok=True)
    papers, _ = load_sample()
    domain_cells = analyse_screening.load_successful("domain")
    outcome_cells = analyse_screening.load_successful("outcome")
    available = {k[0] for k in domain_cells} | {k[0] for k in outcome_cells}
    pmids = sorted({p["pmid"] for p in papers} & available)
    weights = analyse_screening.domain_weights(domain_cells, pmids)
    per_year = plot_results.gated_papers_per_year()
    rates = plot_results.configuration_rates(outcome_cells, pmids)
    plot_results.plot_timeline(rates, per_year, "timeline_extrapolated_mistral.pdf")
    plot_results.plot_category_swarm(outcome_cells, pmids, weights,
                                     analyse_screening.domain_shares(weights),
                                     plot_results.annual_scale(per_year),
                                     "swarm_by_category_mistral.pdf")
    print(f"n = {len(pmids)} papers, figures written to {PREVIEW_FIGURE_DIR}")


if __name__ == "__main__":
    main()
