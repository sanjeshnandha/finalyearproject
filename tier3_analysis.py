"""Tier 3 analysis: Break down the "Other / Domain-Specific" datasets.

This script categorizes the datasets that fall into the generic "Other / Domain-Specific"
category from the Tier 2 analysis into more specific sub-categories and generates a
stacked bar chart visualizing their usage (Applied vs. Theory).

It also includes Domain Analysis: categorizing papers by the real-world problem
domains they are solving, and generating paper-to-domain mapping markdown files.

Usage:
    python tier3_analysis.py
    python tier3_analysis.py --year 2020
    python tier3_analysis.py --all-years
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Colour palette ───────────────────────────────────────────────────────────
COLOUR_APPLIED = "#0EA5E9"   # Sky-blue for Applied
COLOUR_THEORY  = "#F97316"   # Orange for Theory / Pure Math

# ── Tier 2 Classification Rules (to filter out non-Other datasets) ────────────
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

def classify_tier2(name):
    """Classify a dataset name into a Tier 2 benchmark family."""
    for family, patterns in BENCHMARK_FAMILIES:
        for pat in patterns:
            if re.search(pat, name, re.IGNORECASE):
                return family
    return "Other / Domain-Specific"

# ── Tier 3 Classification Rules (for the "Other" datasets) ────────────────────
TIER3_FAMILIES = [
    ("Program Synthesis Benchmarks", [
        r"\bCmp[0-9]\b", r"\bDsc[0-9]\b", r"\bMaj[0-9]\b", r"\bMal[0-9]\b",
        r"\bMux[0-9]\b", r"\bPar[0-9]\b", r"\bpar3\b", r"\badder1\b"
    ]),
    ("Bit-String / Boolean Problems", [
        r"Adder", r"Carry", r"Parity", r"Multiplexer", r"\bMUX\b",
        r"Majority-on", r"Chain", r"Multiplier"
    ]),
    ("RL / Game Environments", [
        r"\bCartPole\b", r"\bCarRacing\b", r"\bDoom\b", r"\bMountainCar\b",
        r"\bFlappy Bird\b", r"\bMaze\b", r"\bMinecraft\b", r"\bSabberStone\b",
        r"\bCT-graph\b"
    ]),
    ("Problem Instance Libraries", [
        r"Covering Array", r"MKP benchmark", r"MIPLIB", r"OR-library",
        r"OPTSICOM", r"OCSTP instances", r"benchmark dataset",
        r"benchmark instances", r"Irrigation Network", r"Modena network", r"ACLib"
    ]),
    ("Opaque / Generic Labels", [
        r"^339$", r"^DS[0-9]$", r"Toy Problem", r"^BIO$"
    ]),
    ("Pure Math / Test Functions", [
        r"\bBall\b", r"\bCube\b", r"\bSimplex\b", r"\bBranin\b", r"\bCamelback\b",
        r"\bGoldstein-Price\b", r"\bSalomon\b", r"\bQuadric\b", r"\bSpherical\b",
        r"\bStep\b", r"\bRidge\b", r"\bSchaffer", r"\bJump\b", r"\bNeedHighMut\b",
        r"\bDeJong\b", r"\bUF1\b", r"\bBimodal\b", r"\btrap\b", r"\bDec\.3\b",
        r"\bDeceptiveLeadingBlocks\b", r"\bEqualBlocksOneMax\b", r"\bSQLO\b",
        r"\bNK-landscape\b", r"\bREB5", r"\bREBChain", r"\bREBGrid", r"\bSMD",
        r"\bSMTQ", r"\bMTQ", r"\buMTR\b", r"\bMultimodal\b", r"\bWangFreitas\b",
        r"\bMOPTA\b", r"\bGriewangk\b", r"\bYABBOB\b", r"\bYAHDBBOB\b",
        r"\bYANOISYBBOB\b", r"2D Spin Glass", r"MAX-SAT", r"Linear Ordering",
        r"\bDTLZ2orig\b", r"\bDTLZ2void\b"
    ]),
]

def classify_tier3(name):
    """Classify a Tier 2 'Other' dataset into a Tier 3 sub-category."""
    for family, patterns in TIER3_FAMILIES:
        for pat in patterns:
            if re.search(pat, name, re.IGNORECASE):
                return family
    return "Genuine Real-World Datasets"

def load_tier3_dataset_counts(csv_files):
    """Count unique papers per Tier 3 category for datasets in the 'Other' Tier 2 category."""
    seen = set()
    counts = defaultdict(lambda: {"Applied": 0, "Theory": 0})
    dataset_lists = defaultdict(set)

    for csv_path in csv_files:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dataset = row.get("Evaluation_Dataset", "").strip()
                category = row.get("Category", "").strip()
                paper_id = row.get("Paper_ID", "").strip()
                if not dataset:
                    continue

                if classify_tier2(dataset) != "Other / Domain-Specific":
                    continue

                paper_key = paper_id.rsplit("_Ext_", 1)[0] if "_Ext_" in paper_id else paper_id
                source_key = csv_path.name
                cat_key = "Applied" if category == "Applied" else "Theory"
                dedup_key = (source_key, paper_key, dataset, cat_key)

                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                tier3_cat = classify_tier3(dataset)
                counts[tier3_cat][cat_key] += 1
                dataset_lists[tier3_cat].add(dataset)

    return counts, dataset_lists

def plot_tier3_chart(counts, dataset_lists, year_label, out_path):
    """Create and save the stacked horizontal bar chart for Tier 3 categories."""
    if not counts:
        return

    sorted_categories = sorted(
        counts.items(),
        key=lambda x: x[1]["Applied"] + x[1]["Theory"],
        reverse=True,
    )
    sorted_categories = list(reversed(sorted_categories))

    labels = [name for name, _ in sorted_categories]
    applied_vals = [c["Applied"] for _, c in sorted_categories]
    theory_vals  = [c["Theory"]  for _, c in sorted_categories]
    totals = [a + t for a, t in zip(applied_vals, theory_vals)]

    display_labels = []
    for label in labels:
        n_datasets = len(dataset_lists[label])
        display_labels.append(f"{label} ({n_datasets} datasets)")

    fig_height = max(6, len(labels) * 0.8)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    y_pos = range(len(labels))

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
    ax.set_yticklabels(display_labels, fontsize=10, fontfamily="sans-serif")
    ax.set_xlabel("Number of Papers (unique)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(
        f"Tier 3 Analysis: Breakdown of 'Other / Domain-Specific' Datasets ({year_label})\n"
        f"Shows composition of datasets missed by standard benchmark families",
        fontsize=14, fontweight="bold", pad=20
    )

    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#555555")
    ax.tick_params(axis="y", colors="#333333")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    for bar_a, bar_t, a_val, t_val in zip(bars_applied, bars_theory, applied_vals, theory_vals):
        total = a_val + t_val
        if total > 0:
            ax.text(
                total + (max(totals) * 0.01), bar_a.get_y() + bar_a.get_height() / 2,
                str(total), va="center", ha="left", fontsize=9, color="#555555",
                fontweight="bold",
            )

    ax.legend(loc="lower right", fontsize=11, framealpha=0.9, edgecolor="#CCCCCC")

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✓ Tier 3 chart saved to {out_path}")


# ── Domain Analysis ──────────────────────────────────────────────────────────
DOMAIN_CATEGORIES = {
    "Navigation & Pathfinding": [r"navigat", r"maze", r"path", r"autonomous driving"],
    "Routing & Logistics": [r"routing", r"tsp", r"vehicle", r"bin-packing", r"packing", r"facility layout"],
    "Software Testing & Verification": [r"test generation", r"test case", r"test data", r"software", r"bug", r"fault"],
    "Classification & Detection": [r"classifi", r"detection", r"recognition", r"diagnos"],
    "Regression & Prediction": [r"regression", r"predict", r"forecasting"],
    "Scheduling & Planning": [r"schedul", r"tardiness", r"planning", r"timetable"],
    "Game Playing & RL Environments": [r"game", r"reinforcement learning", r"rl", r"agent"],
    "Combinatorial Optimization": [r"max-sat", r"knapsack", r"spanning tree", r"combinatorial"],
    "Design & Engineering": [r"design", r"structure", r"turbine", r"controller", r"aerodynamic", r"engineering"],
    "ML Tuning & Feature Selection": [r"hyperparameter", r"parameter tuning", r"tuning", r"feature selection", r"dimensionality reduction"],
    "Image & Computer Vision": [r"image", r"vision", r"pixel", r"cnn", r"neural network"],
    "Pure Math / Synthetic Test": [r"evaluating mathematical landscapes", r"synthetic", r"test function", r"benchmark problem"],
}

def classify_problem_domain(problem_context):
    """Classify a problem context into a broad domain."""
    if not problem_context or problem_context.strip().lower() in ["none", "unknown"]:
        return "Unknown / Unspecified"
    for category, patterns in DOMAIN_CATEGORIES.items():
        for pat in patterns:
            if re.search(pat, problem_context, re.IGNORECASE):
                return category
    return "Other Applied Problems"

def load_domain_counts(csv_files):
    """Count unique papers per problem domain."""
    seen_papers = set()
    counts = defaultdict(int)
    problem_lists = defaultdict(set)

    for csv_path in csv_files:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                problem_context = row.get("Problem_Context", "").strip()
                paper_id = row.get("Paper_ID", "").strip()
                if not problem_context:
                    continue

                paper_key = paper_id.rsplit("_Ext_", 1)[0] if "_Ext_" in paper_id else paper_id
                dedup_key = f"{csv_path.name}_{paper_key}"

                if dedup_key in seen_papers:
                    continue
                seen_papers.add(dedup_key)

                domain = classify_problem_domain(problem_context)
                if domain == "Pure Math / Synthetic Test":
                    continue

                counts[domain] += 1
                problem_lists[domain].add(problem_context)

    return counts, problem_lists

def plot_domain_chart(counts, year_label, out_path):
    """Create and save the horizontal bar chart for Problem Domains."""
    if not counts:
        return

    sorted_categories = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    sorted_categories = list(reversed(sorted_categories))

    labels = [name for name, _ in sorted_categories]
    vals = [count for _, count in sorted_categories]

    fig_height = max(6, len(labels) * 0.7)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    y_pos = range(len(labels))

    bars = ax.barh(
        y_pos, vals, height=0.65, color="#8B5CF6",
        edgecolor="white", linewidth=0.5,
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=11, fontfamily="sans-serif")
    ax.set_xlabel("Number of Papers", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(
        f"Real-World Problem Domains Addressed by GECCO Papers ({year_label})\n"
        f"Excludes papers purely evaluating mathematical/synthetic test functions",
        fontsize=14, fontweight="bold", pad=20
    )

    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#555555")
    ax.tick_params(axis="y", colors="#333333")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    for bar, val in zip(bars, vals):
        if val > 0:
            ax.text(
                val + (max(vals) * 0.01), bar.get_y() + bar.get_height() / 2,
                str(val), va="center", ha="left", fontsize=10, color="#555555",
                fontweight="bold",
            )

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✓ Domain chart saved to {out_path}")


# ── Paper-to-Domain Mapping ─────────────────────────────────────────────────
def generate_paper_domain_mapping(csv_files, year_label, out_path):
    """Generate a markdown table mapping every paper to its domain."""
    paper_mappings = {}

    for csv_path in csv_files:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_title = row.get("Paper_Title", "").strip()
                problem_context = row.get("Problem_Context", "").strip()
                category = row.get("Category", "").strip()

                if not paper_title or paper_title in paper_mappings:
                    continue

                domain = classify_problem_domain(problem_context)
                if domain == "Pure Math / Synthetic Test" or category.lower() == "theory":
                    display_domain = "Pure Math / Theory"
                else:
                    display_domain = domain

                paper_mappings[paper_title] = {
                    "domain": display_domain,
                    "category": category,
                    "problem": problem_context,
                }

    sorted_papers = sorted(paper_mappings.items(), key=lambda x: x[0].lower())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"# Paper to Domain Mapping ({year_label})\n\n")
        out.write(f"Total Unique Papers: **{len(sorted_papers)}**\n\n")
        out.write("| Paper Title | Assigned Domain | Applied/Theory | Problem Context |\n")
        out.write("|---|---|---|---|\n")

        for title, data in sorted_papers:
            short_title = title if len(title) <= 60 else title[:57] + "..."
            short_prob = data["problem"] if len(data["problem"]) <= 50 else data["problem"][:47] + "..."
            short_title = short_title.replace("|", "\\|")
            short_prob = short_prob.replace("|", "\\|")
            out.write(f"| {short_title} | **{data['domain']}** | {data['category']} | {short_prob} |\n")

    print(f"  ✓ Paper-domain mapping saved to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Tier 3 & Domain analysis pipeline")
    parser.add_argument(
        "--year", type=int, default=None,
        help="Specific year to generate charts for (e.g. 2020).",
    )
    parser.add_argument(
        "--all-years", action="store_true",
        help="Generate charts for every year individually.",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output image path (for single year mode)",
    )
    args = parser.parse_args()

    def process_year(csv_file, year):
        """Process a single year: Tier 3 chart + Domain chart + Paper mapping."""
        print(f"\n{'='*60}")
        print(f"  Processing {year}")
        print(f"{'='*60}")

        # ── Tier 3: Breakdown of "Other / Domain-Specific" ───────────────
        print(f"  📊 Tier 3: Breakdown of 'Other' datasets...")
        counts_t3, dataset_lists = load_tier3_dataset_counts([csv_file])
        if counts_t3:
            t3_path = Path(f"data/reports/dataset_tier3_chart_{year}.png")
            plot_tier3_chart(counts_t3, dataset_lists, year, t3_path)
        else:
            print("     No 'Other' data found. Skipping Tier 3.")

        # ── Domain Analysis: Problem domains ─────────────────────────────
        print(f"  📊 Domain Analysis: Problem domains...")
        counts_domain, _ = load_domain_counts([csv_file])
        if counts_domain:
            domain_path = Path(f"data/reports/domain_analysis_chart_{year}.png")
            plot_domain_chart(counts_domain, year, domain_path)
        else:
            print("     No domain data found. Skipping.")

        # ── Paper-to-Domain Mapping ──────────────────────────────────────
        print(f"  📋 Paper-to-domain mapping...")
        mapping_path = Path(f"data/reports/paper_domains_{year}.md")
        generate_paper_domain_mapping([csv_file], year, mapping_path)

    if args.all_years:
        csv_files = sorted(Path("data/reports").glob("[0-9][0-9][0-9][0-9]_dataset.csv"))
        if not csv_files:
            print("⚠ No year CSV files found.")
            return
        for csv_file in csv_files:
            year = csv_file.stem.split("_")[0]
            process_year(csv_file, year)

    elif args.year:
        csv_file = Path(f"data/reports/{args.year}_dataset.csv")
        if not csv_file.exists():
            print(f"⚠ Could not find {csv_file}")
            return
        process_year(csv_file, str(args.year))

    else:
        csv_files = sorted(Path("data/reports").glob("[0-9][0-9][0-9][0-9]_dataset.csv"))
        if not csv_files:
            print("⚠ Could not find CSV file(s).")
            return
        for csv_file in csv_files:
            year = csv_file.stem.split("_")[0]
            process_year(csv_file, year)


if __name__ == "__main__":
    main()
