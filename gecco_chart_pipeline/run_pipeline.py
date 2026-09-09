#!/usr/bin/env python3
"""
GECCO Chart Pipeline — Tier 3 & Tier 4 Graph Generator
=======================================================

Drop your year CSV files (e.g., 2020_dataset.csv) into the input_csvs/ folder,
then run:

    python3 run_pipeline.py

All charts and reports are saved to the output/ folder.

Charts generated (per year + combined):
  - dataset_tier3_chart_YYYY.png       — Tier 3 bar chart for that year
  - domain_analysis_chart_YYYY.png     — Tier 4 bar chart for that year
  - dataset_tier3_chart_combined.png   — Tier 3 bar chart across ALL years
  - domain_analysis_chart_combined.png — Tier 4 bar chart across ALL years
  - paper_classification_YYYY.md       — Per-year markdown report
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
    import numpy as np
except ImportError:
    print("❌ matplotlib and numpy are required. Install with:")
    print("   pip install matplotlib numpy")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
#  COLOUR PALETTE
# ═══════════════════════════════════════════════════════════════════════════════
COLOURS = {
    "applied":  "#0EA5E9",
    "theory":   "#F97316",
    "domain":   "#8B5CF6",
    "bg":       "#FAFAFA",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 2 — Benchmark Families (to identify "Other" datasets)
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
        r"\bMux[0-9]\b", r"\bPar[0-9]\b", r"\bpar3\b", r"\badder1\b"]),
    ("Bit-String / Boolean Problems", [
        r"Adder", r"Carry", r"Parity", r"Multiplexer", r"\bMUX\b",
        r"Majority-on", r"Chain", r"Multiplier"]),
    ("RL / Game Environments", [
        r"\bCartPole\b", r"\bCarRacing\b", r"\bDoom\b", r"\bMountainCar\b",
        r"\bFlappy Bird\b", r"\bMaze\b", r"\bMinecraft\b", r"\bSabberStone\b",
        r"\bCT-graph\b"]),
    ("Problem Instance Libraries", [
        r"Covering Array", r"MKP benchmark", r"MIPLIB", r"OR-library",
        r"OPTSICOM", r"OCSTP instances", r"benchmark dataset",
        r"benchmark instances", r"Irrigation Network", r"Modena network", r"ACLib"]),
    ("Opaque / Generic Labels", [
        r"^339$", r"^DS[0-9]$", r"Toy Problem", r"^BIO$"]),
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
        r"\bDTLZ2orig\b", r"\bDTLZ2void\b"]),
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
        return "Pure Math / Theory" if category.lower() == "theory" else "Unknown / Unspecified"
    for domain, patterns in DOMAIN_CATEGORIES.items():
        for pat in patterns:
            if re.search(pat, problem_context, re.IGNORECASE):
                return "Pure Math / Theory" if domain == "Pure Math / Synthetic Test" else domain
    return "Pure Math / Theory" if category.lower() == "theory" else "Other Applied Problems"


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════
def load_all_records(csv_files):
    """Load all CSVs and return a list of per-row records with all classifications."""
    records = []
    for csv_path in csv_files:
        year = csv_path.stem.split("_")[0]
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ds = row.get("Evaluation_Dataset", "").strip()
                cat = row.get("Category", "").strip()
                paper_id = row.get("Paper_ID", "").strip()
                problem = row.get("Problem_Context", "").strip()
                title = row.get("Paper_Title", "").strip()
                paper_key = paper_id.rsplit("_Ext_", 1)[0] if "_Ext_" in paper_id else paper_id

                records.append({
                    "year": year,
                    "paper_key": f"{year}_{paper_key}",
                    "paper_title": title,
                    "dataset": ds,
                    "category": cat,
                    "tier2_family": classify_tier2(ds) if ds else "",
                    "tier3_family": classify_tier3(ds) if ds and classify_tier2(ds) == "Other / Domain-Specific" else "",
                    "full_classification": get_dataset_classification(ds) if ds else "",
                    "problem_context": problem,
                    "domain": classify_domain(problem, cat),
                })
    return records


def detect_conference_name(csv_files):
    """Try to detect the conference name from the CSV directory or filenames."""
    parent = csv_files[0].parent.name.upper()
    for conf in ["GECCO", "FOGA", "PPSN", "CEC", "WCCI", "EMO"]:
        if conf in parent:
            return conf
    with open(csv_files[0], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        first_row = next(reader, None)
        if first_row:
            conf = first_row.get("Conference", "").strip()
            if conf:
                return conf
    return "Conference"


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 3 BAR CHART — Breakdown of "Other / Domain-Specific"
# ═══════════════════════════════════════════════════════════════════════════════
def generate_tier3_chart(records, year_label, conf_name, out_path):
    """Horizontal stacked bar chart for Tier 3 sub-categories."""
    seen = set()
    counts = defaultdict(lambda: {"Applied": 0, "Theory": 0})
    ds_lists = defaultdict(set)

    for r in records:
        if not r["tier3_family"]:
            continue
        dedup = (r["paper_key"], r["dataset"])
        if dedup in seen:
            continue
        seen.add(dedup)
        cat_key = "Applied" if r["category"] == "Applied" else "Theory"
        counts[r["tier3_family"]][cat_key] += 1
        ds_lists[r["tier3_family"]].add(r["dataset"])

    if not counts:
        print(f"     ⚠ No 'Other' datasets for {year_label}. Skipping Tier 3 chart.")
        return

    sorted_cats = sorted(counts.items(), key=lambda x: x[1]["Applied"] + x[1]["Theory"], reverse=True)
    sorted_cats = list(reversed(sorted_cats))
    labels = [n for n, _ in sorted_cats]
    app = [c["Applied"] for _, c in sorted_cats]
    thy = [c["Theory"]  for _, c in sorted_cats]
    tots = [a + t for a, t in zip(app, thy)]
    disp = [f"{l} ({len(ds_lists[l])} datasets)" for l in labels]

    fig_h = max(6, len(labels) * 0.8)
    fig, ax = plt.subplots(figsize=(14, fig_h))
    fig.patch.set_facecolor(COLOURS["bg"]); ax.set_facecolor(COLOURS["bg"])
    y = range(len(labels))
    ax.barh(y, app, height=0.65, color=COLOURS["applied"], label="Applied", edgecolor="white", linewidth=0.5)
    ax.barh(y, thy, height=0.65, left=app, color=COLOURS["theory"], label="Theory (Pure Math)", edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(disp, fontsize=10, fontfamily="sans-serif")
    ax.set_xlabel("Number of Papers (unique)", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(
        f"Tier 3: Breakdown of 'Other / Domain-Specific' Datasets — {conf_name} {year_label}\n"
        f"Sub-categories of datasets not matched by standard benchmark families",
        fontsize=14, fontweight="bold", pad=20)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC"); ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#555555"); ax.tick_params(axis="y", colors="#333333")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    for i, total in enumerate(tots):
        if total > 0:
            ax.text(total + max(tots) * 0.01, i, str(total), va="center", ha="left",
                    fontsize=9, color="#555555", fontweight="bold")
    ax.legend(loc="lower right", fontsize=11, framealpha=0.9, edgecolor="#CCCCCC")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"     ✅ Tier 3 chart  → {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════════
#  TIER 4 BAR CHART — Domain Analysis
# ═══════════════════════════════════════════════════════════════════════════════
def generate_domain_chart(records, year_label, conf_name, out_path):
    """Horizontal bar chart for Tier 4 problem domains."""
    seen = set()
    counts = defaultdict(int)

    for r in records:
        dedup = r["paper_key"]
        if dedup in seen:
            continue
        seen.add(dedup)
        domain = r["domain"]
        if domain == "Pure Math / Theory":
            continue
        counts[domain] += 1

    if not counts:
        print(f"     ⚠ No applied domain data for {year_label}. Skipping Tier 4 chart.")
        return

    sorted_cats = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    sorted_cats = list(reversed(sorted_cats))
    labels = [n for n, _ in sorted_cats]
    vals = [c for _, c in sorted_cats]

    fig_h = max(6, len(labels) * 0.7)
    fig, ax = plt.subplots(figsize=(14, fig_h))
    fig.patch.set_facecolor(COLOURS["bg"]); ax.set_facecolor(COLOURS["bg"])
    y = range(len(labels))
    ax.barh(y, vals, height=0.65, color=COLOURS["domain"], edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11, fontfamily="sans-serif")
    ax.set_xlabel("Number of Papers", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_title(
        f"Tier 4: Real-World Problem Domains — {conf_name} {year_label}\n"
        f"Excludes papers purely evaluating mathematical/synthetic test functions",
        fontsize=14, fontweight="bold", pad=20)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC"); ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(axis="x", colors="#555555"); ax.tick_params(axis="y", colors="#333333")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    for i, val in enumerate(vals):
        if val > 0:
            ax.text(val + max(vals) * 0.01, i, str(val), va="center", ha="left",
                    fontsize=10, color="#555555", fontweight="bold")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"     ✅ Tier 4 chart  → {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAPER CLASSIFICATION REPORT (Markdown)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_paper_report(records, year_label, conf_name, out_path):
    """Generate markdown classification report."""
    papers = {}
    for r in records:
        pk = r["paper_key"]
        if pk not in papers:
            papers[pk] = {"title": r["paper_title"], "year": r["year"],
                          "category": r["category"], "problem": r["problem_context"],
                          "domain": r["domain"], "datasets": {}}
        if r["dataset"] and r["dataset"] not in papers[pk]["datasets"]:
            papers[pk]["datasets"][r["dataset"]] = r["full_classification"]

    domain_groups = defaultdict(list)
    for p in papers.values():
        domain_groups[p["domain"]].append(p)
    sorted_domains = sorted(domain_groups.keys(),
                            key=lambda d: ("ZZZ" if d == "Pure Math / Theory" else d))

    total = len(papers)
    app_c = sum(1 for p in papers.values() if p["category"] == "Applied")
    thy_c = total - app_c

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# {conf_name} {year_label} — Paper Classification Report\n\n")
        f.write(f"**Total Papers:** {total} ({app_c} Applied, {thy_c} Theory)\n\n---\n\n")
        f.write("## Domain Summary\n\n| Domain | Papers | Applied | Theory |\n|---|---|---|---|\n")
        for d in sorted_domains:
            pl = domain_groups[d]
            a = sum(1 for p in pl if p["category"] == "Applied")
            f.write(f"| {d} | {len(pl)} | {a} | {len(pl)-a} |\n")
        f.write(f"| **Total** | **{total}** | **{app_c}** | **{thy_c}** |\n\n---\n\n")
        for d in sorted_domains:
            pl = domain_groups[d]
            pl.sort(key=lambda p: (p.get("year", ""), p["title"].lower()))
            f.write(f"## {d} ({len(pl)} papers)\n\n")
            for i, p in enumerate(pl, 1):
                yr_prefix = f"[{p['year']}] " if "combined" in year_label.lower() else ""
                f.write(f"### {i}. {yr_prefix}{p['title']}\n\n")
                f.write(f"- **Type:** {p['category']}\n- **Problem:** {p['problem'] or '—'}\n")
                if p["datasets"]:
                    cg = defaultdict(list)
                    for dn, dc in sorted(p["datasets"].items()):
                        cg[dc].append(dn)
                    f.write(f"- **Datasets** ({len(p['datasets'])} total):\n")
                    for cls in sorted(cg.keys()):
                        dl = cg[cls]
                        ds = ", ".join(f"`{d}`" for d in dl[:8])
                        if len(dl) > 8:
                            ds += f" ... (+{len(dl)-8} more)"
                        f.write(f"  - **{cls}:** {ds}\n")
                else:
                    f.write("- **Datasets:** None recorded\n")
                f.write("\n")
            f.write("---\n\n")
    print(f"     ✅ Report        → {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="GECCO Chart Pipeline — Tier 3 & Tier 4 Bar Charts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            How to use:
              1. Place your CSV files (e.g., 2020_dataset.csv) into input_csvs/
              2. Run: python3 run_pipeline.py
              3. Find all charts & reports in output/

            Generated per year:
              dataset_tier3_chart_YYYY.png       — Tier 3 bar chart
              domain_analysis_chart_YYYY.png     — Tier 4 bar chart
              paper_classification_YYYY.md       — Full paper report

            Generated combined (all years):
              dataset_tier3_chart_combined.png   — Tier 3 bar chart (all years)
              domain_analysis_chart_combined.png — Tier 4 bar chart (all years)
              paper_classification_combined.md   — Full report (all years)
        """))
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--year", type=int, default=None)
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    input_dir = args.input or (script_dir / "input_csvs")
    output_dir = args.output or (script_dir / "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.glob("[0-9][0-9][0-9][0-9]_dataset.csv"))
    if not csv_files:
        csv_files = sorted(input_dir.glob("[0-9][0-9][0-9][0-9]*.csv"))
    if not csv_files:
        print(f"❌ No CSV files found in {input_dir}/")
        sys.exit(1)

    conf_name = detect_conference_name(csv_files)
    years = sorted(set(f.stem.split("_")[0] for f in csv_files))

    if args.year:
        csv_files = [f for f in csv_files if f.stem.startswith(str(args.year))]
        years = [str(args.year)]

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     GECCO Chart Pipeline — Tier 3 & Tier 4 Graphs          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Conference: {conf_name}")
    print(f"  Input:      {input_dir}")
    print(f"  Output:     {output_dir}")
    print(f"  CSVs:       {len(csv_files)} file(s) — Years: {', '.join(years)}")
    print()

    # Load all data
    print("  📂 Loading data...")
    records = load_all_records(csv_files)
    print(f"     Loaded {len(records)} records from {len(csv_files)} CSVs")
    print()

    # ── Per-year charts ──
    for year in years:
        year_records = [r for r in records if r["year"] == year]
        print(f"  ┌─── {year} ───")
        generate_tier3_chart(year_records, year, conf_name,
                             output_dir / f"dataset_tier3_chart_{year}.png")
        generate_domain_chart(year_records, year, conf_name,
                              output_dir / f"domain_analysis_chart_{year}.png")
        generate_paper_report(year_records, year, conf_name,
                              output_dir / f"paper_classification_{year}.md")
        print(f"  └─── {year} done ✓")
        print()

    # ── Combined charts (all years merged) ──
    if len(years) >= 1:
        year_range = f"{years[0]}–{years[-1]}" if len(years) > 1 else years[0]
        combined_label = f"Combined ({year_range})"
        print(f"  ┌─── {combined_label} ───")
        generate_tier3_chart(records, combined_label, conf_name,
                             output_dir / "dataset_tier3_chart_combined.png")
        generate_domain_chart(records, combined_label, conf_name,
                              output_dir / "domain_analysis_chart_combined.png")
        generate_paper_report(records, combined_label, conf_name,
                              output_dir / "paper_classification_combined.md")
        print(f"  └─── Combined done ✓")
        print()

    # ── Summary ──
    generated = sorted(f for f in output_dir.iterdir() if f.name != ".gitkeep")
    print("═" * 60)
    print(f"  ✅ Done! Generated {len(generated)} files in {output_dir}/")
    print("═" * 60)
    for f in generated:
        size = f.stat().st_size
        print(f"     {f.name:50s} {size // 1024:>4d} KB")


if __name__ == "__main__":
    main()
