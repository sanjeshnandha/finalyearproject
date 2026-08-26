"""Statistical analysis: Stacked bar chart of datasets used across GECCO papers.

Reads CSV files from data/reports/, counts the number of **unique papers**
using each dataset (Evaluation_Dataset column), and produces a stacked
horizontal bar chart with:
    - Y-axis:  Dataset names (top N most-used)
    - X-axis:  Number of papers (unique)
    - Colours: Applied (sky-blue) vs Theory/Pure Math (orange)

For "Custom Simulated Data", an inset text box lists the actual problem
contexts covered by that umbrella label.

Output is saved to data/reports/dataset_usage_chart.png (or _YYYY.png)

Usage:
    python dataset_analysis.py
    python dataset_analysis.py --top 30
    python dataset_analysis.py --year 2021
"""

import argparse
import csv
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


# ── Colour palette ───────────────────────────────────────────────────────────
COLOUR_APPLIED = "#0EA5E9"   # Sky-blue for Applied
COLOUR_THEORY  = "#F97316"   # Orange for Theory / Pure Math

MAX_CUSTOM_ITEMS = 15        # Max number of Custom Simulated Data contexts to show


def load_dataset_counts(csv_files: list[Path]):
    """Count unique papers per dataset, split by Applied vs Theory.

    Returns:
        counts: {dataset_name: {"Applied": n, "Theory": m}}
        custom_benchmarks: set of Benchmark_Name values for "Custom Simulated Data"
    """
    # Track (paper_id, dataset, category) to deduplicate
    seen: set[tuple[str, str, str]] = set()
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"Applied": 0, "Theory": 0})
    custom_benchmarks: set[str] = set()
    # Track per-paper custom benchmark names to avoid duplicates from multiple extractions
    custom_seen: set[tuple[str, str]] = set()

    for csv_path in csv_files:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dataset = row.get("Evaluation_Dataset", "").strip()
                category = row.get("Category", "").strip()
                paper_id = row.get("Paper_ID", "").strip()
                if not dataset:
                    continue

                # Derive unique paper key (strip _Ext_NN suffix)
                paper_key = paper_id.rsplit("_Ext_", 1)[0] if "_Ext_" in paper_id else paper_id
                # Also include the source CSV name to avoid cross-year collisions
                source_key = csv_path.name

                cat_key = "Applied" if category == "Applied" else "Theory"
                dedup_key = (source_key, paper_key, dataset, cat_key)

                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                counts[dataset][cat_key] += 1

                # Collect benchmark names behind "Custom Simulated Data"
                if dataset == "Custom Simulated Data":
                    bench = row.get("Benchmark_Name", "").strip()
                    if bench:
                        bench_dedup = (source_key, paper_key, bench)
                        if bench_dedup not in custom_seen:
                            custom_seen.add(bench_dedup)
                            custom_benchmarks.add(bench)

    return counts, custom_benchmarks


def plot_stacked_chart(
    counts: dict[str, dict[str, int]],
    custom_contexts: set[str],
    top_n: int,
    title: str,
    out_path: Path,
):
    """Create and save the stacked horizontal bar chart."""

    # Sort by total count descending, take top N
    sorted_datasets = sorted(
        counts.items(),
        key=lambda x: x[1]["Applied"] + x[1]["Theory"],
        reverse=True,
    )[:top_n]
    # Reverse so the largest bar is at the top of the chart
    sorted_datasets = list(reversed(sorted_datasets))

    labels = [name for name, _ in sorted_datasets]
    applied_vals = [c["Applied"] for _, c in sorted_datasets]
    theory_vals  = [c["Theory"]  for _, c in sorted_datasets]

    # Truncate long dataset names for display
    display_labels = []
    for label in labels:
        if len(label) > 55:
            display_labels.append(label[:52] + "…")
        else:
            display_labels.append(label)

    # ── Figure setup ─────────────────────────────────────────────────────
    fig_height = max(8, len(labels) * 0.45)
    # Add extra width for the custom-simulated-data annotation
    has_custom = "Custom Simulated Data" in [name for name, _ in sorted_datasets]
    fig_width = 18 if has_custom else 14

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    y_pos = range(len(labels))

    # Stacked bars
    bars_applied = ax.barh(
        y_pos, applied_vals, height=0.65, color=COLOUR_APPLIED,
        label="Applied", edgecolor="white", linewidth=0.5,
    )
    bars_theory = ax.barh(
        y_pos, theory_vals, height=0.65, left=applied_vals,
        color=COLOUR_THEORY, label="Theory (Pure Math)",
        edgecolor="white", linewidth=0.5,
    )

    # ── Axis labels & formatting ─────────────────────────────────────────
    ax.set_yticks(y_pos)
    ax.set_yticklabels(display_labels, fontsize=9, fontfamily="sans-serif")
    ax.set_xlabel("Number of Papers", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)

    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#555555")
    ax.tick_params(axis="y", colors="#333333")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    # Value labels on bars
    for bar_a, bar_t, a_val, t_val in zip(bars_applied, bars_theory, applied_vals, theory_vals):
        total = a_val + t_val
        if total > 0:
            ax.text(
                total + 0.5, bar_a.get_y() + bar_a.get_height() / 2,
                str(total), va="center", ha="left", fontsize=8, color="#555555",
                fontweight="bold",
            )

    # Legend
    ax.legend(loc="lower right", fontsize=11, framealpha=0.9, edgecolor="#CCCCCC")

    # ── Annotation box for "Custom Simulated Data" benchmarks ─────────────
    if has_custom and custom_contexts:
        sorted_benchmarks = sorted(custom_contexts)
        shown = sorted_benchmarks[:MAX_CUSTOM_ITEMS]
        remaining = len(sorted_benchmarks) - len(shown)

        lines = ['"Custom Simulated Data" includes:']
        for bench in shown:
            lines.append(f"  • {bench}")
        if remaining > 0:
            lines.append(f"  … and {remaining} more benchmarks")

        annotation_text = "\n".join(lines)

        # Place the text box to the right of the plot area
        fig.subplots_adjust(right=0.68)
        fig.text(
            0.70, 0.5, annotation_text,
            fontsize=8, fontfamily="sans-serif",
            verticalalignment="center",
            bbox=dict(
                boxstyle="round,pad=0.8",
                facecolor="#FFF7ED",
                edgecolor="#F97316",
                alpha=0.95,
            ),
        )

    plt.tight_layout(rect=[0, 0, 0.68 if (has_custom and custom_contexts) else 1, 1])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✓ Chart saved to {out_path}")


# ── Benchmark family classification (for long-tail grouping) ─────────────────
import re

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


def plot_longtail_chart(
    counts: dict[str, dict[str, int]],
    year: str,
    out_path: Path,
):
    """Create a chart showing single-use datasets grouped by benchmark family.

    This is "Tier 2" — the long tail of datasets used by only 1 paper,
    grouped into benchmark families so every dataset is accounted for.
    """
    # Separate single-use datasets
    single_use = {ds: c for ds, c in counts.items()
                  if (c["Applied"] + c["Theory"]) == 1}
    multi_use = {ds: c for ds, c in counts.items()
                 if (c["Applied"] + c["Theory"]) >= 2}

    if not single_use:
        return

    # Group single-use datasets by benchmark family
    family_applied: dict[str, int] = defaultdict(int)
    family_theory: dict[str, int] = defaultdict(int)
    family_datasets: dict[str, list[str]] = defaultdict(list)

    for ds, c in single_use.items():
        fam = classify_dataset(ds)
        family_applied[fam] += c["Applied"]
        family_theory[fam] += c["Theory"]
        family_datasets[fam].append(ds)

    # Sort families by total count
    families = sorted(
        family_applied.keys(),
        key=lambda f: family_applied[f] + family_theory[f],
        reverse=True,
    )

    applied_vals = [family_applied[f] for f in families]
    theory_vals = [family_theory[f] for f in families]
    totals = [a + t for a, t in zip(applied_vals, theory_vals)]

    # Build display labels with dataset count
    display_labels = [f"{f} ({len(family_datasets[f])} datasets)" for f in families]

    # Reverse for top-to-bottom display
    display_labels = list(reversed(display_labels))
    applied_vals = list(reversed(applied_vals))
    theory_vals = list(reversed(theory_vals))
    totals = list(reversed(totals))
    families_rev = list(reversed(families))

    # ── Figure ───────────────────────────────────────────────────────────
    fig_height = max(6, len(families) * 0.5 + 2)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    y_pos = range(len(families))

    bars_applied = ax.barh(
        y_pos, applied_vals, height=0.65, color=COLOUR_APPLIED,
        label="Applied", edgecolor="white", linewidth=0.5,
    )
    bars_theory = ax.barh(
        y_pos, theory_vals, height=0.65, left=applied_vals,
        color=COLOUR_THEORY, label="Theory (Pure Math)",
        edgecolor="white", linewidth=0.5,
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(display_labels, fontsize=9, fontfamily="sans-serif")
    ax.set_xlabel("Number of Papers (unique)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(
        f"Long-Tail Datasets in GECCO Papers ({year})\n"
        f"Datasets Used by Only 1 Paper — Grouped by Benchmark Family\n"
        f"({len(single_use)} of {len(counts)} total datasets)",
        fontsize=14, fontweight="bold", pad=15,
    )

    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#555555")
    ax.tick_params(axis="y", colors="#333333")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    # Value labels
    for bar_a, bar_t, a_val, t_val in zip(bars_applied, bars_theory, applied_vals, theory_vals):
        total = a_val + t_val
        if total > 0:
            ax.text(
                total + 0.3, bar_a.get_y() + bar_a.get_height() / 2,
                str(total), va="center", ha="left", fontsize=9, color="#555555",
                fontweight="bold",
            )

    ax.legend(loc="lower right", fontsize=11, framealpha=0.9, edgecolor="#CCCCCC")

    # Summary annotation box
    summary_lines = [
        f"Total datasets in {year}: {len(counts)}",
        f"Used by 2+ papers: {len(multi_use)}",
        f"Used by 1 paper (shown here): {len(single_use)}",
    ]
    fig.text(
        0.98, 0.02, "\n".join(summary_lines),
        fontsize=9, fontfamily="sans-serif",
        ha="right", va="bottom",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#E0F2FE",
                  edgecolor="#0EA5E9", alpha=0.9),
    )

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✓ Long-tail chart saved to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Dataset usage stacked bar chart")
    parser.add_argument(
        "--top", type=int, default=25,
        help="Number of top datasets to show (default: 25)",
    )
    parser.add_argument(
        "--year", type=int, default=None,
        help="Specific year to generate chart for (e.g. 2021). "
             "If not provided, generates for all years.",
    )
    parser.add_argument(
        "--all-years", action="store_true",
        help="Generate charts for every year individually.",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output image path",
    )
    args = parser.parse_args()

    if args.all_years:
        # Generate tiered charts for every year
        csv_files = sorted(Path("data/reports").glob("[0-9][0-9][0-9][0-9]_dataset.csv"))
        if not csv_files:
            print("⚠ No year CSV files found.")
            return
        for csv_file in csv_files:
            year = csv_file.stem.split("_")[0]
            print(f"\n📊 Generating charts for {year}...")
            counts, custom_contexts = load_dataset_counts([csv_file])
            print(f"   Found {len(counts)} unique datasets")

            if not counts:
                continue

            # Tier 1: Top datasets stacked bar
            title = f"Top Datasets Used in GECCO Papers ({year})\nApplied vs Theory"
            out_path = Path(f"data/reports/dataset_usage_chart_{year}.png")
            plot_stacked_chart(counts, custom_contexts, args.top, title, out_path)

            # Tier 2: Long-tail grouped by benchmark family
            longtail_path = Path(f"data/reports/dataset_longtail_chart_{year}.png")
            plot_longtail_chart(counts, year, longtail_path)

    elif args.year:
        csv_files = [Path(f"data/reports/{args.year}_dataset.csv")]
        title = f"Top Datasets Used in GECCO Papers ({args.year})\nApplied vs Theory"
        out_path = args.output or Path(f"data/reports/dataset_usage_chart_{args.year}.png")

        if not csv_files[0].exists():
            print(f"⚠ Could not find {csv_files[0]}")
            return

        print(f"📊 Loading data from {csv_files[0].name}...")
        counts, custom_contexts = load_dataset_counts(csv_files)
        print(f"   Found {len(counts)} unique datasets")

        if not counts:
            print("   No data found. Skipping.")
            return

        # Tier 1: Top datasets
        plot_stacked_chart(counts, custom_contexts, args.top, title, out_path)
        # Tier 2: Long-tail
        longtail_path = args.output.with_name(
            f"dataset_longtail_chart_{args.year}.png"
        ) if args.output else Path(f"data/reports/dataset_longtail_chart_{args.year}.png")
        plot_longtail_chart(counts, str(args.year), longtail_path)

    else:
        csv_files = sorted(Path("data/reports").glob("[0-9][0-9][0-9][0-9]_dataset.csv"))
        title = "Top Datasets Used in GECCO Papers (All Years)\nApplied vs Theory"
        out_path = args.output or Path("data/reports/dataset_usage_chart.png")

        if not csv_files or not all(f.exists() for f in csv_files):
            print("⚠ Could not find CSV file(s).")
            return

        print(f"📊 Loading data from {len(csv_files)} CSV files...")
        for f in csv_files:
            print(f"   • {f.name}")

        counts, custom_contexts = load_dataset_counts(csv_files)
        print(f"   Found {len(counts)} unique datasets (counting unique papers)")

        if not counts:
            print("   No data found. Skipping chart generation.")
            return

        plot_stacked_chart(counts, custom_contexts, args.top, title, out_path)


if __name__ == "__main__":
    main()
