# GECCO Chart Pipeline

One-click graph generator for Tier 3 and Tier 4 analysis of GECCO paper datasets.

## Quick Start

```bash
# 1. Install the one dependency
pip install matplotlib

# 2. Put your CSVs in the input folder
cp 2020_dataset.csv  gecco_chart_pipeline/input_csvs/
cp 2021_dataset.csv  gecco_chart_pipeline/input_csvs/
# ... any year CSVs

# 3. Run the pipeline
cd gecco_chart_pipeline
python3 run_pipeline.py
```

All charts and reports appear in the `output/` folder.

## What It Generates

For **each year CSV** placed in `input_csvs/`, the pipeline generates:

| File | Description |
|---|---|
| `dataset_tier3_chart_YYYY.png` | **Tier 3 Chart** — Breaks down the "Other / Domain-Specific" datasets into sub-categories (Pure Math, RL Environments, Program Synthesis, Genuine Real-World, etc.) |
| `domain_analysis_chart_YYYY.png` | **Tier 4 Chart** — Shows the real-world problem domains papers are solving (Navigation, Routing, Classification, Design, etc.) |
| `paper_classification_YYYY.md` | **Full Report** — Every paper mapped to its domain + datasets listed with their classification |

## CSV Format

The input CSVs must have these columns (as produced by the GECCO extraction pipeline):

- `Paper_ID`
- `Paper_Title`
- `Category` (Applied or Theory)
- `Problem_Context`
- `Evaluation_Dataset`
- `Benchmark_Name`

## Options

```bash
# Process all CSVs in the default input folder
python3 run_pipeline.py

# Process only one year
python3 run_pipeline.py --year 2020

# Custom input/output folders
python3 run_pipeline.py --input /path/to/csvs --output /path/to/output
```

## Tier 3 — Dataset Sub-Categories

Datasets that fall into the generic "Other / Domain-Specific" category from the Tier 2 long-tail chart are broken into:

| Sub-Category | Examples |
|---|---|
| Genuine Real-World Datasets | Iris, Adult, Wine, Boston Housing |
| Pure Math / Test Functions | Jump, Ridge, Branin, Camelback |
| Bit-String / Boolean Problems | 10-bit Parity, 70-bit Multiplexer |
| Program Synthesis Benchmarks | Cmp6, Dsc1, Mal5, Mux6 |
| RL / Game Environments | CartPole, DoomTakeCover, Flappy Bird |
| Problem Instance Libraries | OR-Library, MIPLIB 2017 |
| Opaque / Generic Labels | 339, DS1, DS2, Toy Problem |

## Tier 4 — Problem Domains

Papers are categorized by the real-world problem they are solving:

| Domain | Keyword Patterns |
|---|---|
| Navigation & Pathfinding | navigation, maze, path, autonomous driving |
| Routing & Logistics | routing, TSP, vehicle, bin-packing |
| Software Testing & Verification | test generation, test case, software |
| Classification & Detection | classification, detection, recognition |
| Regression & Prediction | regression, prediction, forecasting |
| Scheduling & Planning | scheduling, tardiness, timetable |
| Game Playing & RL Environments | game, reinforcement learning |
| Combinatorial Optimization | MAX-SAT, knapsack, spanning tree |
| Design & Engineering | design, structure, turbine, controller |
| ML Tuning & Feature Selection | hyperparameter, feature selection |
| Image & Computer Vision | image, vision, CNN, neural network |
| Pure Math / Theory | Evaluating mathematical landscapes |
