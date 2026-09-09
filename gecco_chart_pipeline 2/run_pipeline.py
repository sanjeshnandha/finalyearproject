#!/usr/bin/env python3
"""
GECCO Chart Pipeline — One-Click Graph Generator
=================================================

Drop your year CSV files (e.g., 2020_dataset.csv) into the input_csvs/ folder,
then run:

    python3 run_pipeline.py

All charts and reports are saved to the output/ folder.

Options:
    python3 run_pipeline.py                     # Process all CSVs in input_csvs/
    python3 run_pipeline.py --input /path/to/csvs  # Use a custom input folder
    python3 run_pipeline.py --year 2020         # Process only one year
"""

import argparse
import csv
import re
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
except ImportError:
    print("❌ matplotlib is required. Install it with:")
    print("   pip install matplotlib")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
#  COLOUR PALETTE
# ═══════════════════════════════════════════════════════════════════════════════
COLOUR_APPLIED = "#0EA5E9"
COLOUR_THEORY  = "#F97316"
COLOUR_DOMAIN  = "#8B5CF6"


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 2 — Benchmark Families (used to identify "Other" datasets)
# ═══════════════════════════════════════════════════════════════════════════════
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
    for family, patterns in BENCHMARK_FAMILIES:
        for pat in patterns:
            if re.search(pat, name, re.IGNORECASE):
                return family
    return "Other / Domain-Specific"


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 3 — Sub-categories for "Other / Domain-Specific"
# ═══════════════════════════════════════════════════════════════════════════════
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
    for family, patterns in TIER3_FAMILIES:
        for pat in patterns:
            if re.search(pat, name, re.IGNORECASE):
                return family
    return "Genuine Real-World Datasets"

def get_dataset_classification(name):
    tier2 = classify_tier2(name)
    if tier2 != "Other / Domain-Specific":
        return tier2
    return classify_tier3(name)


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 4 — Problem Domain Classification
# ═══════════════════════════════════════════════════════════════════════════════
DOMAIN_CATEGORIES = {
    "Navigation & Pathfinding":       [r"navigat", r"maze", r"path", r"autonomous driving"],
    "Routing & Logistics":            [r"routing", r"tsp", r"vehicle", r"bin-packing", r"packing", r"facility layout"],
    "Software Testing & Verification":[r"test generation", r"test case", r"test data", r"software", r"bug", r"fault"],
    "Classification & Detection":     [r"classifi", r"detection", r"recognition", r"diagnos"],
    "Regression & Prediction":        [r"regression", r"predict", r"forecasting"],
    "Scheduling & Planning":          [r"schedul", r"tardiness", r"planning", r"timetable"],
    "Game Playing & RL Environments": [r"game", r"reinforcement learning", r"rl", r"agent"],
    "Combinatorial Optimization":     [r"max-sat", r"knapsack", r"spanning tree", r"combinatorial"],
    "Design & Engineering":           [r"design", r"structure", r"turbine", r"controller", r"aerodynamic", r"engineering"],
    "ML Tuning & Feature Selection":  [r"hyperparameter", r"parameter tuning", r"tuning", r"feature selection", r"dimensionality reduction"],
    "Image & Computer Vision":        [r"image", r"vision", r"pixel", r"cnn", r"neural network"],
    "Pure Math / Synthetic Test":     [r"evaluating mathematical landscapes", r"synthetic", r"test function", r"benchmark problem"],
}

def classify_domain(problem_context, category=""):
    if not problem_context or problem_context.strip().lower() in ["none", "unknown"]:
        if category.lower() == "theory":
            return "Pure Math / Theory"
        return "Unknown / Unspecified"
    for domain, patterns in DOMAIN_CATEGORIES.items():
        for pat in patterns:
            if re.search(pat, problem_context, re.IGNORECASE):
                if domain == "Pure Math / Synthetic Test":
                    return "Pure Math / Theory"
                return domain
    if category.lower() == "theory":
        return "Pure Math / Theory"
    return "Other Applied Problems"


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 3 CHART — Breakdown of "Other / Domain-Specific"
# ═══════════════════════════════════════════════════════════════════════════════
def generate_tier3_chart(csv_path, year, out_dir):
    seen = set()
    counts = defaultdict(lambda: {"Applied": 0, "Theory": 0})
    dataset_lists = defaultdict(set)

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
            cat_key = "Applied" if category == "Applied" else "Theory"
            dedup_key = (csv_path.name, paper_key, dataset, cat_key)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            tier3_cat = classify_tier3(dataset)
            counts[tier3_cat][cat_key] += 1
            dataset_lists[tier3_cat].add(dataset)

    if not counts:
        print(f"     ⚠ No 'Other' datasets found for {year}. Skipping Tier 3 chart.")
        return

    sorted_cats = sorted(counts.items(), key=lambda x: x[1]["Applied"] + x[1]["Theory"], reverse=True)
    sorted_cats = list(reversed(sorted_cats))

    labels = [n for n, _ in sorted_cats]
    applied_vals = [c["Applied"] for _, c in sorted_cats]
    theory_vals  = [c["Theory"]  for _, c in sorted_cats]
    totals = [a + t for a, t in zip(applied_vals, theory_vals)]
    display_labels = [f"{l} ({len(dataset_lists[l])} datasets)" for l in labels]

    fig_height = max(6, len(labels) * 0.8)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")
    y = range(len(labels))

    ax.barh(y, applied_vals, height=0.65, color=COLOUR_APPLIED, label="Applied", edgecolor="white", linewidth=0.5)
    ax.barh(y, theory_vals, height=0.65, left=applied_vals, color=COLOUR_THEORY, label="Theory (Pure Math)", edgecolor="white", linewidth=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels(display_labels, fontsize=10, fontfamily="sans-serif")
    ax.set_xlabel("Number of Papers (unique)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(
        f"Tier 3: Breakdown of 'Other / Domain-Specific' Datasets ({year})\n"
        f"Sub-categories of datasets not matched by standard benchmark families",
        fontsize=14, fontweight="bold", pad=20)

    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#555555")
    ax.tick_params(axis="y", colors="#333333")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    for i, total in enumerate(totals):
        if total > 0:
            ax.text(total + max(totals) * 0.01, i, str(total), va="center", ha="left",
                    fontsize=9, color="#555555", fontweight="bold")

    ax.legend(loc="lower right", fontsize=11, framealpha=0.9, edgecolor="#CCCCCC")
    plt.tight_layout()
    out_path = out_dir / f"dataset_tier3_chart_{year}.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"     ✅ Tier 3 chart  → {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 4 CHART — Domain Analysis
# ═══════════════════════════════════════════════════════════════════════════════
def generate_domain_chart(csv_path, year, out_dir):
    seen_papers = set()
    counts = defaultdict(int)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            problem_context = row.get("Problem_Context", "").strip()
            paper_id = row.get("Paper_ID", "").strip()
            category = row.get("Category", "").strip()
            if not problem_context:
                continue

            paper_key = paper_id.rsplit("_Ext_", 1)[0] if "_Ext_" in paper_id else paper_id
            dedup_key = f"{csv_path.name}_{paper_key}"
            if dedup_key in seen_papers:
                continue
            seen_papers.add(dedup_key)

            domain = classify_domain(problem_context, category)
            if domain == "Pure Math / Theory":
                continue
            counts[domain] += 1

    if not counts:
        print(f"     ⚠ No applied domain data found for {year}. Skipping domain chart.")
        return

    sorted_cats = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    sorted_cats = list(reversed(sorted_cats))
    labels = [n for n, _ in sorted_cats]
    vals = [c for _, c in sorted_cats]

    fig_height = max(6, len(labels) * 0.7)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")
    y = range(len(labels))

    ax.barh(y, vals, height=0.65, color=COLOUR_DOMAIN, edgecolor="white", linewidth=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11, fontfamily="sans-serif")
    ax.set_xlabel("Number of Papers", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(
        f"Real-World Problem Domains in GECCO Papers ({year})\n"
        f"Excludes papers purely evaluating mathematical/synthetic test functions",
        fontsize=14, fontweight="bold", pad=20)

    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#555555")
    ax.tick_params(axis="y", colors="#333333")
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    for i, val in enumerate(vals):
        if val > 0:
            ax.text(val + max(vals) * 0.01, i, str(val), va="center", ha="left",
                    fontsize=10, color="#555555", fontweight="bold")

    plt.tight_layout()
    out_path = out_dir / f"domain_analysis_chart_{year}.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"     ✅ Domain chart  → {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAPER CLASSIFICATION REPORT (Markdown)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_paper_report(csv_path, year, out_dir):
    papers = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_id = row.get("Paper_ID", "").strip()
            paper_title = row.get("Paper_Title", "").strip()
            category = row.get("Category", "").strip()
            problem_context = row.get("Problem_Context", "").strip()
            dataset = row.get("Evaluation_Dataset", "").strip()
            if not paper_title:
                continue

            paper_key = paper_id.rsplit("_Ext_", 1)[0] if "_Ext_" in paper_id else paper_id
            if paper_key not in papers:
                papers[paper_key] = {
                    "title": paper_title,
                    "category": category,
                    "problem": problem_context,
                    "domain": classify_domain(problem_context, category),
                    "datasets": {},
                }
            if dataset and dataset not in papers[paper_key]["datasets"]:
                papers[paper_key]["datasets"][dataset] = get_dataset_classification(dataset)

    domain_groups = defaultdict(list)
    for pdata in papers.values():
        domain_groups[pdata["domain"]].append(pdata)

    sorted_domains = sorted(domain_groups.keys(),
                            key=lambda d: ("ZZZ" if d == "Pure Math / Theory" else d))

    total = len(papers)
    applied_count = sum(1 for p in papers.values() if p["category"] == "Applied")
    theory_count = total - applied_count

    out_path = out_dir / f"paper_classification_{year}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# GECCO {year} — Full Paper Classification Report\n\n")
        f.write(f"**Total Papers:** {total} ({applied_count} Applied, {theory_count} Theory)\n\n")
        f.write("Each paper is classified on two axes:\n")
        f.write("- **Tier 3 (Dataset Classification):** What kind of datasets/benchmarks the paper uses\n")
        f.write("- **Tier 4 (Problem Domain):** What real-world problem the paper is trying to solve\n\n---\n\n")

        f.write("## Domain Summary\n\n")
        f.write("| Domain | Papers | Applied | Theory |\n|---|---|---|---|\n")
        for domain in sorted_domains:
            plist = domain_groups[domain]
            app = sum(1 for p in plist if p["category"] == "Applied")
            thy = len(plist) - app
            f.write(f"| {domain} | {len(plist)} | {app} | {thy} |\n")
        f.write(f"| **Total** | **{total}** | **{applied_count}** | **{theory_count}** |\n\n---\n\n")

        for domain in sorted_domains:
            plist = domain_groups[domain]
            plist.sort(key=lambda p: p["title"].lower())
            f.write(f"## {domain} ({len(plist)} papers)\n\n")

            for i, pdata in enumerate(plist, 1):
                problem = pdata["problem"] if pdata["problem"] else "—"
                f.write(f"### {i}. {pdata['title']}\n\n")
                f.write(f"- **Type:** {pdata['category']}\n")
                f.write(f"- **Problem:** {problem}\n")

                if pdata["datasets"]:
                    class_groups = defaultdict(list)
                    for ds_name, ds_class in sorted(pdata["datasets"].items()):
                        class_groups[ds_class].append(ds_name)
                    f.write(f"- **Datasets Used** ({len(pdata['datasets'])} total):\n")
                    for cls in sorted(class_groups.keys()):
                        ds_list = class_groups[cls]
                        ds_str = ", ".join(f"`{d}`" for d in ds_list[:8])
                        if len(ds_list) > 8:
                            ds_str += f" ... (+{len(ds_list) - 8} more)"
                        f.write(f"  - **{cls}:** {ds_str}\n")
                else:
                    f.write("- **Datasets Used:** None recorded\n")
                f.write("\n")
            f.write("---\n\n")

    print(f"     ✅ Report        → {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN — Process all CSVs
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="GECCO Chart Pipeline — Generate Tier 3 & Tier 4 graphs from CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            How to use:
              1. Place your CSV files (e.g., 2020_dataset.csv) into input_csvs/
              2. Run: python3 run_pipeline.py
              3. Find all charts & reports in output/
        """))
    parser.add_argument("--input", type=Path, default=None,
                        help="Input folder containing CSV files (default: input_csvs/)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output folder for charts & reports (default: output/)")
    parser.add_argument("--year", type=int, default=None,
                        help="Process only this year (e.g., 2020)")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    input_dir = args.input or (script_dir / "input_csvs")
    output_dir = args.output or (script_dir / "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.year:
        csv_files = list(input_dir.glob(f"{args.year}_dataset.csv"))
        if not csv_files:
            csv_files = list(input_dir.glob(f"{args.year}*.csv"))
    else:
        csv_files = sorted(input_dir.glob("[0-9][0-9][0-9][0-9]_dataset.csv"))
        if not csv_files:
            csv_files = sorted(input_dir.glob("[0-9][0-9][0-9][0-9]*.csv"))

    if not csv_files:
        print(f"❌ No CSV files found in {input_dir}/")
        print(f"   Place your year CSVs (e.g., 2020_dataset.csv) in that folder and try again.")
        sys.exit(1)

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        GECCO Chart Pipeline — Tier 3 & Tier 4 Graphs       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Input:  {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  CSVs:   {len(csv_files)} file(s) found")
    print()

    for csv_file in csv_files:
        year = csv_file.stem.split("_")[0]
        print(f"  ┌─── {year} ({csv_file.name}) ───")

        # Tier 3: Dataset breakdown
        generate_tier3_chart(csv_file, year, output_dir)

        # Tier 4: Domain analysis
        generate_domain_chart(csv_file, year, output_dir)

        # Full paper classification report
        generate_paper_report(csv_file, year, output_dir)

        print(f"  └─── {year} done ✓")
        print()

    # List generated files
    generated = sorted(output_dir.iterdir())
    print("═" * 60)
    print(f"  ✅ Done! Generated {len(generated)} files in {output_dir}/")
    print("═" * 60)
    for f in generated:
        size = f.stat().st_size
        if size > 1024:
            print(f"     {f.name:50s} {size // 1024:>4d} KB")
        else:
            print(f"     {f.name:50s} {size:>4d} B")


if __name__ == "__main__":
    main()
