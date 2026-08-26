"""Additional dataset visualizations for the GECCO research project.

Generates two charts:
  1. Dataset Diversity Line Chart — unique datasets & papers per year
  2. Benchmark Composition Stacked Area Chart — how dataset categories evolve

Usage:
    python dataset_visualizations.py
    python dataset_visualizations.py --chart diversity
    python dataset_visualizations.py --chart composition
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


# ── Colour palette ───────────────────────────────────────────────────────────
COLOURS = {
    "primary":    "#6366F1",  # Indigo
    "secondary":  "#EC4899",  # Pink
    "accent":     "#14B8A6",  # Teal
    "applied":    "#0EA5E9",  # Sky-blue
    "theory":     "#F97316",  # Orange
    "bg":         "#FAFAFA",
}

# Benchmark family classification rules (order matters — first match wins)
BENCHMARK_FAMILIES = [
    ("CEC Benchmarks",     [r"\bCEC\b", r"\bCEC\s*20\d\d\b"]),
    ("BBOB / COCO",        [r"\bBBOB\b", r"\bCOCO\b", r"\bNoiseless\b"]),
    ("DTLZ Suite",         [r"\bDTLZ\d?\b"]),
    ("ZDT Suite",          [r"\bZDT\d?\b"]),
    ("WFG Suite",          [r"\bWFG\d?\b"]),
    ("TSP / Routing",      [r"\bTSP\b", r"\bCVRP\b", r"\bVRP\b", r"\brouting\b", r"\bTSPLIB\b"]),
    ("Program Synthesis",  [r"\bPSB\b", r"\bProgram Synthesis\b"]),
    ("Image Datasets",     [r"\bMNIST\b", r"\bCIFAR\b", r"\bImageNet\b", r"\bSVHN\b", r"\bFashion\b"]),
    ("OpenML / UCI",       [r"\bOpenML\b", r"\bUCI\b"]),
    ("Classic Functions",  [r"\bRastrigin\b", r"\bSphere\b", r"\bAckley\b", r"\bRosenbrock\b",
                            r"\bSchwefel\b", r"\bGriewank\b", r"\bOneMax\b", r"\bLeadingOnes\b",
                            r"\bBohachevsky\b", r"\bEggHolder\b", r"\bBooth\b", r"\bDamavandi\b"]),
    ("RL Environments",    [r"\bGym\b", r"\bMuJoCo\b", r"\bAtari\b", r"\bBrax\b",
                            r"\bMicroRTS\b", r"\bMiniGrid\b", r"\bPyGame\b"]),
    ("Custom / Simulated", [r"\bCustom\b", r"\bSimulated\b", r"\bSynthetic\b"]),
]


def classify_dataset(name: str) -> str:
    """Classify a dataset name into a benchmark family."""
    for family, patterns in BENCHMARK_FAMILIES:
        for pat in patterns:
            if re.search(pat, name, re.IGNORECASE):
                return family
    return "Other / Domain-Specific"


def load_data(csv_dir: Path):
    """Load all year CSVs and return per-row records."""
    records = []
    for csv_file in sorted(csv_dir.glob("[0-9][0-9][0-9][0-9]_dataset.csv")):
        year = csv_file.stem.split("_")[0]
        with open(csv_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ds = row.get("Evaluation_Dataset", "").strip()
                cat = row.get("Category", "").strip()
                paper_key = row.get("Paper_ID", "").rsplit("_Ext_", 1)[0]
                if ds:
                    records.append({
                        "year": year,
                        "paper_key": f"{year}_{paper_key}",
                        "dataset": ds,
                        "category": cat,
                        "family": classify_dataset(ds),
                    })
    return records


def plot_diversity_chart(records: list[dict], out_path: Path):
    """Chart 1: Dataset diversity over time — dual-axis line chart."""

    # Unique datasets and papers per year
    datasets_by_year = defaultdict(set)
    papers_by_year = defaultdict(set)
    applied_papers = defaultdict(set)
    theory_papers = defaultdict(set)

    for r in records:
        datasets_by_year[r["year"]].add(r["dataset"])
        papers_by_year[r["year"]].add(r["paper_key"])
        if r["category"] == "Applied":
            applied_papers[r["year"]].add(r["paper_key"])
        else:
            theory_papers[r["year"]].add(r["paper_key"])

    years = sorted(datasets_by_year.keys())
    n_datasets = [len(datasets_by_year[y]) for y in years]
    n_papers = [len(papers_by_year[y]) for y in years]
    ratio = [d / p if p > 0 else 0 for d, p in zip(n_datasets, n_papers)]
    n_applied = [len(applied_papers[y]) for y in years]
    n_theory = [len(theory_papers[y]) for y in years]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={"height_ratios": [3, 2]})
    fig.patch.set_facecolor(COLOURS["bg"])

    # ── Top panel: Datasets & Papers ─────────────────────────────────────
    ax1.set_facecolor(COLOURS["bg"])

    # Fill area under datasets line
    ax1.fill_between(years, n_datasets, alpha=0.12, color=COLOURS["primary"])
    line1, = ax1.plot(years, n_datasets, "o-", color=COLOURS["primary"],
                      linewidth=2.5, markersize=8, label="Unique Datasets", zorder=5)

    # Papers on secondary axis
    ax1_twin = ax1.twinx()
    line2, = ax1_twin.plot(years, n_papers, "s--", color=COLOURS["secondary"],
                           linewidth=2.5, markersize=8, label="Papers", zorder=5)

    # Applied vs Theory bars (subtle background)
    bar_width = 0.35
    x_pos = np.arange(len(years))
    ax1_twin.bar(x_pos - bar_width / 2, n_applied, bar_width,
                 color=COLOURS["applied"], alpha=0.25, label="Applied Papers")
    ax1_twin.bar(x_pos + bar_width / 2, n_theory, bar_width,
                 color=COLOURS["theory"], alpha=0.25, label="Theory Papers")
    ax1_twin.set_xticks(x_pos)
    ax1_twin.set_xticklabels(years)

    # Annotate data points
    for i, (d, p) in enumerate(zip(n_datasets, n_papers)):
        ax1.annotate(str(d), (years[i], d), textcoords="offset points",
                     xytext=(0, 12), ha="center", fontsize=9, fontweight="bold",
                     color=COLOURS["primary"])
        ax1_twin.annotate(str(p), (years[i], p), textcoords="offset points",
                          xytext=(0, -16), ha="center", fontsize=9, fontweight="bold",
                          color=COLOURS["secondary"])

    ax1.set_ylabel("Unique Datasets", fontsize=12, fontweight="bold", color=COLOURS["primary"])
    ax1_twin.set_ylabel("Number of Papers", fontsize=12, fontweight="bold", color=COLOURS["secondary"])
    ax1.set_title("Dataset Diversity in GECCO Papers Over Time",
                  fontsize=16, fontweight="bold", pad=15)

    # Combined legend
    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", fontsize=10, framealpha=0.9)

    for ax in [ax1, ax1_twin]:
        ax.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1_twin.spines["left"].set_visible(False)
    ax1.grid(axis="y", linestyle="--", alpha=0.3)

    # ── Bottom panel: Datasets-per-paper ratio ───────────────────────────
    ax2.set_facecolor(COLOURS["bg"])
    ax2.fill_between(years, ratio, alpha=0.15, color=COLOURS["accent"])
    ax2.plot(years, ratio, "D-", color=COLOURS["accent"], linewidth=2.5, markersize=8)

    for i, r in enumerate(ratio):
        ax2.annotate(f"{r:.1f}", (years[i], r), textcoords="offset points",
                     xytext=(0, 12), ha="center", fontsize=10, fontweight="bold",
                     color=COLOURS["accent"])

    ax2.set_xlabel("Year", fontsize=12, fontweight="bold", labelpad=10)
    ax2.set_ylabel("Datasets per Paper", fontsize=12, fontweight="bold", color=COLOURS["accent"])
    ax2.set_title("Average Number of Unique Datasets per Paper",
                  fontsize=13, fontweight="bold", pad=10)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(axis="y", linestyle="--", alpha=0.3)

    plt.tight_layout(h_pad=3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✓ Diversity chart saved to {out_path}")


def plot_composition_chart(records: list[dict], out_path: Path):
    """Chart 2: Stacked area chart of benchmark family composition over time."""

    # Count unique papers per (year, family)
    year_family_papers = defaultdict(lambda: defaultdict(set))
    for r in records:
        year_family_papers[r["year"]][r["family"]].add(r["paper_key"])

    years = sorted(year_family_papers.keys())

    # Get all families, sorted by total usage
    family_totals = defaultdict(int)
    for y in years:
        for fam, papers in year_family_papers[y].items():
            family_totals[fam] += len(papers)

    families = sorted(family_totals.keys(), key=lambda f: family_totals[f], reverse=True)

    # Build data matrix
    data = {}
    for fam in families:
        data[fam] = [len(year_family_papers[y].get(fam, set())) for y in years]

    # Colour palette for stacked area
    cmap = plt.colormaps["tab20"]
    colours = [cmap(i / len(families)) for i in range(len(families))]

    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor(COLOURS["bg"])
    ax.set_facecolor(COLOURS["bg"])

    # Stack the areas
    y_stack = np.zeros(len(years))
    for i, fam in enumerate(families):
        values = np.array(data[fam], dtype=float)
        ax.fill_between(years, y_stack, y_stack + values,
                        alpha=0.8, color=colours[i], label=fam, linewidth=0.5,
                        edgecolor="white")
        y_stack += values

    # ── Formatting ───────────────────────────────────────────────────────
    ax.set_xlabel("Year", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_ylabel("Number of Papers", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title("Benchmark Family Composition in GECCO Papers Over Time",
                 fontsize=16, fontweight="bold", pad=20)

    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    # Legend outside the plot
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=9,
              framealpha=0.9, edgecolor="#CCCCCC", title="Benchmark Family",
              title_fontsize=10)

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✓ Composition chart saved to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Additional dataset visualizations")
    parser.add_argument(
        "--chart", choices=["diversity", "composition", "all"], default="all",
        help="Which chart to generate (default: all)",
    )
    parser.add_argument(
        "--csv-dir", type=Path, default=Path("data/reports"),
        help="Directory containing year CSV files",
    )
    args = parser.parse_args()

    print(f"\n📊 Loading data from {args.csv_dir}...")
    records = load_data(args.csv_dir)
    print(f"   Loaded {len(records)} records")

    if not records:
        print("   No data found. Exiting.")
        return

    if args.chart in ("diversity", "all"):
        plot_diversity_chart(records, args.csv_dir / "dataset_diversity_chart.png")

    if args.chart in ("composition", "all"):
        plot_composition_chart(records, args.csv_dir / "benchmark_composition_chart.png")

    print()


if __name__ == "__main__":
    main()
