#set page(
  margin: (left: 2cm, right: 2cm, top: 2.5cm, bottom: 2cm),
)

#set text(size: 11pt)

#set heading(numbering: "1.")

= Automated Literature Analysis: Interaction Label Use as a Quality Marker

_Supporting data for opinion piece on drug interaction label comparisons._

== PubMed Search

=== Query

```
(synergy OR antagonism OR "synergistic" OR "antagonistic")
AND combination
AND (Loewe OR Bliss OR "Chou-Talalay" OR "combination index" OR FICI
  OR "fractional inhibitory" OR "concentration addition" OR HSA
  OR "highest single agent" OR MuSyC OR BRAID OR interaction)
```

Search was performed year-by-year (2010–2026) to avoid PubMed relevance-ranking bias.

=== Retrieved Papers

#table(
  columns: (3fr, 1fr),
  table.header([*Step*], [*N*]),
  [Papers matching query], [24,487],
  [With abstract ≥ 200 characters], [21,434],
)

The 21,434 papers with usable abstracts form the sampling frame for all subsequent analysis.

#figure(
  image("../figures/papers_by_year.pdf", width: 95%),
  caption: [Papers matching the PubMed query per publication year (2010–2026, n = 24,487). 2026 is a partial year.],
)

== LLM Screening

A random sample of 1,000 papers was drawn from the 21,434 eligible papers and each abstract submitted to Mistral Large (`mistral-large-2512`, temperature 0.1; see prompt below).

=== Base: Complete Abstracts

Despite the ≥200-character pre-filter, some abstracts lack results or conclusions. The LLM flags these as incomplete.
The 777 papers with complete abstracts are the base for all relative estimates below.

=== Domain and Quality-Marker Rates

Each complete abstract is assigned to a domain and classified for whether the paper treats synergy as a marker of combination quality (YES/NO). Values are expressed as percentages of the 777 complete papers.

#table(
  columns: (3fr, 1fr, 1fr, 1fr),
  table.header([*Domain*], [*% of complete*], [*YES rate*], [*% of complete that are YES*]),
  [Antimicrobial], [14.3%], [45.9%], [6.6%],
  [Oncology], [30.2%], [18.3%], [5.5%],
  [Neurology], [12.6%], [5.1%], [0.6%],
  [Ecotoxicology], [9.4%], [0.0%], [0.0%],
  [Immunology], [6.7%], [5.8%], [0.4%],
  [Pest management], [4.0%], [0.0%], [0.0%],
  [Antiviral], [1.8%], [14.3%], [0.3%],
  [Anesthesia], [0.5%], [25.0%], [0.1%],
  [Other], [20.5%], [3.8%], [0.8%],
)

Antimicrobial and oncology together account for 85% of all YES cases.

#figure(
  image("../figures/domain_bars.pdf", width: 95%),
  caption: [Screened papers by domain, stacked by classification (YES = treats synergy as a marker of combination quality).],
)


=== Prompt

```
Analyze this research paper abstract and extract the following information:

Title: {title}
Abstract: {abstract}

Respond ONLY with this JSON (no other text):
{
  "domain": "antimicrobial|antiviral|oncology|immunology|anesthesia|
             neurology|ecotoxicology|pest_management|other",
  "labels_as_quality_proxy": "yes|no",
  "abstract_incomplete": "yes|no"
}

PROTOCOL:
- domain: Classify by the TARGET of the combination study:
  antimicrobial (bacterial/fungal infections), antiviral (viral
  infections), oncology (cancer), immunology (immune conditions),
  anesthesia (sedation/analgesia), neurology (epilepsy, Parkinson's,
  pain, etc.), ecotoxicology (toxic effects on non-target
  organisms/ecosystems), pest_management (combinations targeting pest
  organisms in agricultural context), other (unclear or none of above)
- labels_as_quality_proxy: YES = paper treats synergy as a marker of
  combination quality — either by explicitly claiming synergistic labels
  indicate promise/efficacy, or by screening many combinations implying
  labels identify the most effective ones;
  NO = focuses on mechanistic understanding of why combinations work
  (labels are secondary or not central)
- abstract_incomplete: YES if the abstract reads incomplete and was
  likely cut off. NO if it reads as a coherent complete abstract.
```

== Estimated Publication Rate
Here we estimate the number of published papers per year (search window 2010–June 2026 ≈ 16.5 years) that use interaction labels to proxy the quality of a combination.
We estimate by applying the fractions listed above to all 24,487 papers matching the pubmed query. This assumes that papers without usable abstracts follow the same distribution as the screened sample.

#table(
  columns: (3fr, 1fr, 1fr),
  table.header([*Domain*], [*Estimated total*], [*Per year*]),
  [Antimicrobial], [$approx 1250$], [$approx 76$],
  [Oncology], [$approx 1050$], [$approx 64$],
)

These are conservative estimates. The classification is based on the abstract alone, so the screen only captures papers that foreground the interaction label prominently enough to mention it there. Studies that compute or rely on such labels only within the full text are not counted. The true number of papers using interaction labels as a proxy for combination quality is therefore probably higher than reported here.

---

_Analysis date: 2026-06-12. Data: PubMed (NCBI), 24,487 papers (2010–2026), 1,000-paper random sample screened with Mistral Large (`mistral-large-2512`, temperature 0.1). API cost: CHF 1.10._
