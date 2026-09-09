"""Generate year-wise markdown reports categorizing all papers with
their Tier 3 (dataset sub-category) and Tier 4 (problem domain) classifications.

Usage:
    python3 generate_paper_reports.py --year 2020
    python3 generate_paper_reports.py --all-years
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

# ── Tier 2 Benchmark Families ────────────────────────────────────────────────
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

# ── Tier 3 Sub-Categories (for "Other" datasets) ────────────────────────────
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
    """For datasets in 'Other / Domain-Specific', further classify into Tier 3."""
    for family, patterns in TIER3_FAMILIES:
        for pat in patterns:
            if re.search(pat, name, re.IGNORECASE):
                return family
    return "Genuine Real-World Datasets"

def get_dataset_classification(name):
    """Get full classification: Tier 2 family or Tier 3 sub-category."""
    tier2 = classify_tier2(name)
    if tier2 != "Other / Domain-Specific":
        return tier2
    return classify_tier3(name)

# ── Tier 4: Problem Domain Classification ────────────────────────────────────
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

def classify_domain(problem_context, category):
    """Classify into Tier 4 domain."""
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


def process_year(csv_path, year, out_dir):
    """Process one year CSV and generate a comprehensive markdown report."""
    
    # Collect per-paper data
    # paper_key -> { title, category, problem, datasets: [{name, tier2, tier3_or_family}] }
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
                    "datasets": {},  # dataset_name -> classification
                }
            
            if dataset and dataset not in papers[paper_key]["datasets"]:
                papers[paper_key]["datasets"][dataset] = get_dataset_classification(dataset)
    
    # Group papers by Tier 4 domain
    domain_groups = defaultdict(list)
    for paper_key, pdata in papers.items():
        domain_groups[pdata["domain"]].append(pdata)
    
    # Sort domains: Pure Math last, rest alphabetical
    sorted_domains = sorted(
        domain_groups.keys(),
        key=lambda d: ("ZZZ" if d == "Pure Math / Theory" else d)
    )
    
    # Count stats
    total_papers = len(papers)
    applied_count = sum(1 for p in papers.values() if p["category"] == "Applied")
    theory_count = total_papers - applied_count
    
    # Write markdown
    out_path = out_dir / f"paper_classification_{year}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# GECCO {year} — Full Paper Classification Report\n\n")
        f.write(f"**Total Papers:** {total_papers} "
                f"({applied_count} Applied, {theory_count} Theory)\n\n")
        f.write("Each paper is classified on two axes:\n")
        f.write("- **Tier 3 (Dataset Classification):** What kind of datasets/benchmarks the paper uses\n")
        f.write("- **Tier 4 (Problem Domain):** What real-world problem the paper is trying to solve\n\n")
        f.write("---\n\n")
        
        # Summary table
        f.write("## Domain Summary\n\n")
        f.write("| Domain | Papers | Applied | Theory |\n")
        f.write("|---|---|---|---|\n")
        for domain in sorted_domains:
            plist = domain_groups[domain]
            app = sum(1 for p in plist if p["category"] == "Applied")
            thy = len(plist) - app
            f.write(f"| {domain} | {len(plist)} | {app} | {thy} |\n")
        f.write(f"| **Total** | **{total_papers}** | **{applied_count}** | **{theory_count}** |\n")
        f.write("\n---\n\n")
        
        # Detailed sections per domain
        for domain in sorted_domains:
            plist = domain_groups[domain]
            # Sort papers by title
            plist.sort(key=lambda p: p["title"].lower())
            
            f.write(f"## {domain} ({len(plist)} papers)\n\n")
            
            for i, pdata in enumerate(plist, 1):
                title = pdata["title"]
                category = pdata["category"]
                problem = pdata["problem"] if pdata["problem"] else "—"
                
                f.write(f"### {i}. {title}\n\n")
                f.write(f"- **Type:** {category}\n")
                f.write(f"- **Problem:** {problem}\n")
                
                if pdata["datasets"]:
                    # Group datasets by their classification
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
    
    print(f"  ✓ Report saved to {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate paper classification reports")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--all-years", action="store_true")
    args = parser.parse_args()
    
    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if args.all_years:
        csv_files = sorted(Path("data/reports").glob("[0-9][0-9][0-9][0-9]_dataset.csv"))
        if not csv_files:
            print("⚠ No year CSV files found.")
            return
        for csv_file in csv_files:
            year = csv_file.stem.split("_")[0]
            print(f"\n📄 Generating report for {year}...")
            process_year(csv_file, year, out_dir)
    elif args.year:
        csv_file = Path(f"data/reports/{args.year}_dataset.csv")
        if not csv_file.exists():
            print(f"⚠ Could not find {csv_file}")
            return
        print(f"📄 Generating report for {args.year}...")
        process_year(csv_file, str(args.year), out_dir)
    else:
        csv_files = sorted(Path("data/reports").glob("[0-9][0-9][0-9][0-9]_dataset.csv"))
        if not csv_files:
            print("⚠ No CSV files found.")
            return
        for csv_file in csv_files:
            year = csv_file.stem.split("_")[0]
            print(f"\n📄 Generating report for {year}...")
            process_year(csv_file, year, out_dir)


if __name__ == "__main__":
    main()
