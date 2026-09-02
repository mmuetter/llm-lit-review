"""Report the 2025 spike decomposition from the stored count and corpus files."""

import collections
import json
from pathlib import Path

import numpy as np
from scipy import stats

from analyse_screening import gated_papers_per_year

DATA_DIR = Path(__file__).parent.parent / "data"
COUNTS_PATH = DATA_DIR / "spike2025_counts.json"
MEMBERSHIP_PATH = DATA_DIR / "spike2025_memberships.json"
JOURNAL_PATH = DATA_DIR / "spike2025_journals.json"
BASE_YEAR = 2024
SPIKE_YEAR = 2025
TOP_JOURNALS = 8
TOP_GAINERS = 15


def load_counts():
    """Load every per-year count series, keyed by integer year."""
    raw = json.loads(COUNTS_PATH.read_text())
    return {name: {int(y): c for y, c in series.items()} for name, series in raw.items()}


def growth(series):
    """Return percentage growth from the base year to the spike year."""
    return 100 * (series[SPIKE_YEAR] / series[BASE_YEAR] - 1)


def report_growth(counts, names, heading):
    """Print base-to-spike growth for a group of series."""
    print(f"\n{heading}")
    for name in names:
        series = counts[name]
        print(f"  {name:28s} {series[BASE_YEAR]:8d} -> {series[SPIKE_YEAR]:8d}  {growth(series):+7.1f}%")


def report_trend():
    """Print the trend fit with and without the spike year."""
    gated = gated_papers_per_year()
    years = np.array(sorted(gated))
    values = np.array([gated[y] for y in years], float)
    print("\ntrend in the gated corpus")
    for last in (SPIKE_YEAR, BASE_YEAR):
        keep = years <= last
        correlation, p_value = stats.pearsonr(years[keep], values[keep])
        slope = np.polyfit(years[keep], values[keep], 1)[0]
        print(f"  2010-{last}: slope {slope:+7.1f} gated papers/yr  "
              f"r = {correlation:.3f}  p = {p_value:.1e}  mean = {values[keep].mean():.0f}")


def report_spike_residual():
    """Print how far the spike year sits above the preceding trend."""
    gated = gated_papers_per_year()
    years = np.array([y for y in sorted(gated) if y <= BASE_YEAR])
    values = np.array([gated[y] for y in years], float)
    fit = np.polyfit(years, values, 1)
    predicted = np.polyval(fit, SPIKE_YEAR)
    residuals = values - np.polyval(fit, years)
    excess = gated[SPIKE_YEAR] - predicted
    print(f"  {SPIKE_YEAR} predicted {predicted:.0f}, actual {gated[SPIKE_YEAR]}  "
          f"({excess:+.0f}, {excess / residuals.std(ddof=2):.1f} SD)")


def group_prevalence(memberships):
    """Print how often each term group appears inside the gated set."""
    print("\nterm-group prevalence within the gated set")
    for year, papers in sorted(memberships.items()):
        matched = collections.Counter(g for groups in papers.values() for g in groups)
        shares = "  ".join(f"{g}={100 * n / len(papers):.1f}%" for g, n in sorted(matched.items()))
        print(f"  {year} n={len(papers):5d}  {shares}")


def journal_counts(records):
    """Count gated papers per journal for one year."""
    return collections.Counter(r["journal"] for r in records.values() if r.get("journal"))


def report_concentration(journals):
    """Print journal spread and top venues for each year."""
    print("\njournal concentration in the gated set")
    for year, records in sorted(journals.items()):
        counts = journal_counts(records)
        total = sum(counts.values())
        top = sum(n for _, n in counts.most_common(10))
        print(f"  {year} n={total:5d}  journals={len(counts):4d}  top-10 share={100 * top / total:.1f}%")


def report_gainers(journals):
    """Print the journals contributing most to the base-to-spike increase."""
    before = journal_counts(journals[str(BASE_YEAR)])
    after = journal_counts(journals[str(SPIKE_YEAR)])
    increase = sum(after.values()) - sum(before.values())
    print(f"\njournals driving the +{increase} increase")
    gains = sorted(((after[j] - before[j], j) for j in set(before) | set(after)), reverse=True)
    cumulative = 0
    for gain, journal in gains[:TOP_GAINERS]:
        cumulative += gain
        print(f"  {gain:+5d} ({before[journal]:4d}->{after[journal]:4d})  "
              f"cum {100 * cumulative / increase:5.1f}%  {journal}")


def main():
    """Print every table in the 2025 spike decomposition."""
    counts = load_counts()
    report_growth(counts, [n for n in counts if n.startswith("pubmed_")], "corpus denominators")
    report_growth(counts, [n for n in counts if n.startswith("group_")], "gate term groups")
    report_growth(counts, [n for n in counts if n.startswith("term_")], "vocabulary")
    report_growth(counts, [n for n in counts if n.startswith(("gate_", "mesh_", "synergistic_"))],
                  "gate splits, MeSH probes and field slices")
    report_trend()
    report_spike_residual()
    group_prevalence(json.loads(MEMBERSHIP_PATH.read_text()))
    journals = json.loads(JOURNAL_PATH.read_text())
    report_concentration(journals)
    report_gainers(journals)


if __name__ == "__main__":
    main()
