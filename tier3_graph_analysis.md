# Tier 3 Graph Pipeline — Analysis & Documentation

This document describes the Tier 3 analysis pipeline, which breaks down the generic **"Other / Domain-Specific"** category from the Tier 2 long-tail chart into meaningful sub-categories, and also categorizes papers by the real-world problem domains they address.

---

## Background

The Tier 2 long-tail chart groups datasets into 13 benchmark families (BBOB, CEC, DTLZ, ZDT, WFG, TSP, etc.). Any dataset that doesn't match these families falls into **"Other / Domain-Specific"** — which in 2020 alone contained **298 datasets**.

Our analysis revealed that **only ~50-60% of these 298 entries are genuine real-world datasets**. The rest are:
- Synthetic test functions (e.g., `Jump`, `Ridge`, `Branin`)
- Program synthesis benchmarks (e.g., `Cmp6`, `Dsc1`, `Mux6`)
- Bit-string/Boolean problems (e.g., `10-bit Parity`, `70-bit Multiplexer`)
- RL/Game environments (e.g., `CartPole`, `Flappy Bird`)
- Problem instance libraries (e.g., `OR-Library`, `MIPLIB`)
- Opaque/generic labels (e.g., `339`, `DS1`, `DS2`)

---

## Tier 3 Sub-Categories

The Tier 3 pipeline reclassifies "Other / Domain-Specific" datasets into 7 sub-categories:

| Sub-Category | Description | Examples |
|---|---|---|
| **Genuine Real-World Datasets** | Actual datasets from UCI, Kaggle, domain repos | `Iris`, `Adult`, `Wine`, `Boston Housing` |
| **Pure Math / Test Functions** | Synthetic optimization test functions | `Jump`, `Ridge`, `Branin`, `Camelback`, `YABBOB` |
| **Bit-String / Boolean Problems** | Synthetic boolean/bitstring formulations | `10-bit Parity`, `70-bit Multiplexer`, `16Chain` |
| **Program Synthesis Benchmarks** | I/O specification benchmarks for GP | `Cmp6`, `Dsc1–5`, `Mal1–5`, `Mux6`, `Par5` |
| **RL / Game Environments** | Reinforcement learning environments | `CartPole`, `DoomTakeCover`, `Flappy Bird` |
| **Problem Instance Libraries** | Combinatorial optimization instance sets | `OR-Library`, `MIPLIB 2017`, `Covering Array` |
| **Opaque / Generic Labels** | Extraction artifacts or unlabeled entries | `339`, `DS1`, `DS2`, `Toy Problem` |

---

## Domain Analysis

Separately from the dataset-level Tier 3 breakdown, we also categorize papers by the **real-world problem domain** they are trying to solve. This uses the `Problem_Context` column from the CSV.

Papers that purely evaluate mathematical landscapes are excluded to highlight applied work.

| Domain | Keyword Patterns |
|---|---|
| Navigation & Pathfinding | navigation, maze, path, autonomous driving |
| Routing & Logistics | routing, TSP, vehicle, bin-packing |
| Software Testing & Verification | test generation, test case, software, bug |
| Classification & Detection | classification, detection, recognition, diagnosis |
| Regression & Prediction | regression, prediction, forecasting |
| Scheduling & Planning | scheduling, tardiness, planning, timetable |
| Game Playing & RL Environments | game, reinforcement learning, RL, agent |
| Combinatorial Optimization | MAX-SAT, knapsack, spanning tree |
| Design & Engineering | design, structure, turbine, controller |
| ML Tuning & Feature Selection | hyperparameter, feature selection, tuning |
| Image & Computer Vision | image, vision, pixel, CNN, neural network |

---

## Generated Outputs

### Per Year (2020–2026)

For each year, the pipeline generates three outputs:

1. **Tier 3 Chart** — `data/reports/dataset_tier3_chart_YYYY.png`
   Stacked horizontal bar chart showing the breakdown of "Other" datasets into sub-categories, split by Applied vs Theory.

2. **Domain Analysis Chart** — `data/reports/domain_analysis_chart_YYYY.png`
   Horizontal bar chart showing the top real-world problem domains addressed by papers.

3. **Paper-to-Domain Mapping** — `data/reports/paper_domains_YYYY.md`
   Markdown table mapping every unique paper to its assigned domain.

### File Listing

| Year | Tier 3 Chart | Domain Chart | Paper Mapping |
|---|---|---|---|
| 2020 | `dataset_tier3_chart_2020.png` | `domain_analysis_chart_2020.png` | `paper_domains_2020.md` |
| 2021 | `dataset_tier3_chart_2021.png` | `domain_analysis_chart_2021.png` | `paper_domains_2021.md` |
| 2022 | `dataset_tier3_chart_2022.png` | `domain_analysis_chart_2022.png` | `paper_domains_2022.md` |
| 2023 | `dataset_tier3_chart_2023.png` | `domain_analysis_chart_2023.png` | `paper_domains_2023.md` |
| 2024 | `dataset_tier3_chart_2024.png` | `domain_analysis_chart_2024.png` | `paper_domains_2024.md` |
| 2025 | `dataset_tier3_chart_2025.png` | `domain_analysis_chart_2025.png` | `paper_domains_2025.md` |
| 2026 | `dataset_tier3_chart_2026.png` | `domain_analysis_chart_2026.png` | `paper_domains_2026.md` |

---

## Usage

```bash
# Generate for a specific year
python3 tier3_analysis.py --year 2020

# Generate for all years
python3 tier3_analysis.py --all-years

# Default (no args) also generates for all years
python3 tier3_analysis.py
```

---

## Classification Logic

### Tier 3 Classification (datasets)
1. First, the Tier 2 classification runs to identify datasets in "Other / Domain-Specific".
2. Then, a second set of regex rules (`TIER3_FAMILIES`) is applied to sub-classify these into the 7 categories listed above.
3. Any dataset that doesn't match a Tier 3 pattern falls into "Genuine Real-World Datasets".

### Domain Classification (papers)
1. The `Problem_Context` column is matched against keyword patterns for each domain.
2. Papers with `Problem_Context = "Evaluating mathematical landscapes"` or `Category = "Theory"` are labeled as **Pure Math / Theory**.
3. All other unmatched applied papers go into "Other Applied Problems".

---

## Key Findings (2020)

- **298 datasets** fall into "Other / Domain-Specific" in Tier 2.
- Of these, **~157 are genuine real-world datasets** and **~75 are synthetic test functions** that were missed by the Tier 2 regex.
- The top applied problem domains are **Design & Engineering**, **Classification & Detection**, and **Other Applied Problems** (diverse one-off domains).
- **BBOB variants** like `YABBOB`, `YAHDBBOB`, `YANOISYBBOB` and **alternate spellings** like `Griewangk` were identified as regex gaps in Tier 2.
