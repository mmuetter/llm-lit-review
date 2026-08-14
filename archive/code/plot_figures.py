#!/usr/bin/env python3
"""
Generate all figures for the opinion piece.

Figures:
  1. papers_by_year.pdf      - PubMed hits per year (2026 highlighted as partial)
  2. domain_bars.pdf         - Stacked yes/no bars by domain
  3. yes_by_year.pdf         - Estimated YES papers per year (scaled from sample)
  4. eval_pies.pdf           - Two pies: evaluable composition & YES composition
"""

import json
from pathlib import Path
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
FIGS = ROOT / "figures"
FIGS.mkdir(exist_ok=True)

# ── load data ───────────────────────────────────────────────────────────────
with open(DATA / "pubmed_results_all_years.json") as f:
    all_papers = json.load(f)
papers_by_pmid = {p["pmid"]: p for p in all_papers}

# Use combined results if available, else fall back to screening_100
combined = DATA / "screening_all_results" / "screening_results.json"
batch100  = DATA / "screening_100" / "screening_results.json"
results_path = combined if combined.exists() else batch100
with open(results_path) as f:
    results = json.load(f)

# ── style ────────────────────────────────────────────────────────────────────
DOMAIN_ORDER = [
    "antimicrobial", "antiviral", "oncology", "immunology",
    "anesthesia", "neurology", "ecotoxicology", "pest_management", "other",
]
DOMAIN_COLORS = {
    "antimicrobial":  "#4C72B0",
    "antiviral":      "#DD8452",
    "oncology":       "#55A868",
    "immunology":     "#C44E52",
    "anesthesia":     "#8172B3",
    "neurology":      "#937860",
    "ecotoxicology":  "#DA8BC3",
    "pest_management":"#8C8C8C",
    "other":          "#E0E0E0",
}
YES_COLOR  = "#2196F3"
NO_COLOR   = "#CFD8DC"
YEAR_COLOR = "#546E7A"
PARTIAL_COLOR = "#B0BEC5"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ── helpers ──────────────────────────────────────────────────────────────────
def is_complete(r):
    return (r.get("abstract_incomplete") != "yes"
            and r.get("domain") is not None
            and "error" not in r)

def is_yes(r):
    return is_complete(r) and r.get("labels_as_quality_proxy") == "yes"

# ── Figure 1: PubMed hits per year ───────────────────────────────────────────
years_count = Counter(p["year"] for p in all_papers if p.get("year"))
years = sorted(years_count)
counts = [years_count[y] for y in years]
colors_bar = [PARTIAL_COLOR if y == "2026" else YEAR_COLOR for y in years]

fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(years, counts, color=colors_bar, width=0.7, edgecolor="white", linewidth=0.5)
ax.set_xlabel("Year")
ax.set_ylabel("Papers")
ax.set_title("PubMed search hits per year")
ax.tick_params(axis="x", rotation=45)

legend_patches = [
    mpatches.Patch(color=YEAR_COLOR,    label="Full year"),
    mpatches.Patch(color=PARTIAL_COLOR, label="2026 (partial)"),
]
ax.legend(handles=legend_patches, frameon=False)
fig.tight_layout()
fig.savefig(FIGS / "papers_by_year.pdf")
plt.close(fig)
print("✓ papers_by_year.pdf")

# ── Figure 2: Stacked yes/no bars by domain ──────────────────────────────────
domain_yes = Counter()
domain_no  = Counter()
for r in results:
    if not is_complete(r):
        continue
    d = r.get("domain")
    if d in DOMAIN_ORDER:
        if r.get("labels_as_quality_proxy") == "yes":
            domain_yes[d] += 1
        else:
            domain_no[d] += 1

domains_present = [d for d in DOMAIN_ORDER if domain_yes[d] + domain_no[d] > 0]
yes_vals = [domain_yes[d] for d in domains_present]
no_vals  = [domain_no[d]  for d in domains_present]
x = np.arange(len(domains_present))

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(x, no_vals,  color=NO_COLOR,  label="No",  width=0.6)
ax.bar(x, yes_vals, bottom=no_vals, color=YES_COLOR, label="Yes", width=0.6)
ax.set_xticks(x)
ax.set_xticklabels([d.replace("_", "\n") for d in domains_present], fontsize=9)
ax.set_ylabel("Papers (screened sample)")
ax.set_title("Labels as quality proxy by domain")
ax.legend(title="Labels as\nquality proxy", frameon=False)
fig.tight_layout()
fig.savefig(FIGS / "domain_bars.pdf")
plt.close(fig)
print("✓ domain_bars.pdf")

# ── Figure 3: Estimated YES papers per year (scaled from sample) ─────────────
# For each screened paper, look up its publication year
screened_total = len([r for r in results if "error" not in r])
full_total = len(all_papers)
scale = full_total / screened_total if screened_total else 1

yes_by_year = Counter()
eval_by_year = Counter()
for r in results:
    if "error" in r:
        continue
    pmid = r.get("pmid")
    year = papers_by_pmid.get(pmid, {}).get("year")
    if not year:
        continue
    if is_complete(r):
        eval_by_year[year] += 1
    if is_yes(r):
        yes_by_year[year] += 1

# Scale up to full dataset
all_years = sorted(set(years_count.keys()))
yes_scaled  = [yes_by_year.get(y, 0) * scale for y in all_years]
eval_scaled = [eval_by_year.get(y, 0) * scale for y in all_years]
colors_bar2 = [PARTIAL_COLOR if y == "2026" else YES_COLOR for y in all_years]

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(all_years, yes_scaled, color=colors_bar2, width=0.7,
       edgecolor="white", linewidth=0.5)
ax.set_xlabel("Year")
ax.set_ylabel("Estimated papers (scaled from sample)")
ax.set_title("Estimated papers using labels as quality proxy per year")
ax.tick_params(axis="x", rotation=45)
legend_patches = [
    mpatches.Patch(color=YES_COLOR,     label="Full year"),
    mpatches.Patch(color=PARTIAL_COLOR, label="2026 (partial)"),
]
ax.legend(handles=legend_patches, frameon=False)
fig.tight_layout()
fig.savefig(FIGS / "yes_by_year.pdf")
plt.close(fig)
print("✓ yes_by_year.pdf")

# ── Figure 4: Two pie charts ─────────────────────────────────────────────────
# Pie 1: composition of complete papers by domain
eval_by_domain = Counter(
    r.get("domain") for r in results if is_complete(r)
)
# Pie 2: composition of YES papers by domain
yes_by_domain = Counter(
    r.get("domain") for r in results if is_yes(r)
)

fig, axes = plt.subplots(1, 2, figsize=(10, 5))

def make_pie(ax, counter, title):
    domains = [d for d in DOMAIN_ORDER if counter[d] > 0]
    vals    = [counter[d] for d in domains]
    colors  = [DOMAIN_COLORS[d] for d in domains]
    labels  = [f"{d.replace('_', ' ')}\n({v})" for d, v in zip(domains, vals)]
    wedges, texts, autotexts = ax.pie(
        vals, labels=labels, colors=colors,
        autopct="%1.0f%%", startangle=90,
        pctdistance=0.75,
        textprops={"fontsize": 8},
    )
    for at in autotexts:
        at.set_fontsize(7)
    ax.set_title(title, fontsize=10, pad=12)

make_pie(axes[0], eval_by_domain, "Complete papers\nby domain")
make_pie(axes[1], yes_by_domain,  "YES papers\nby domain")

fig.tight_layout()
fig.savefig(FIGS / "eval_pies.pdf")
plt.close(fig)
print("✓ eval_pies.pdf")
