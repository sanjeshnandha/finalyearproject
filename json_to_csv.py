"""Convert all JSON extraction outputs to a single CSV file.

Reads every JSON file in data/outputs/ (recursively), flattens each
extraction into one row, and writes a combined CSV to data/reports/.

Usage:
    python json_to_csv.py
    python json_to_csv.py --output-dir data/outputs --report-path data/reports/gecco_dataset.csv
"""

import argparse
import csv
import json
from pathlib import Path


# CSV column headers — your requested columns first, then additional ones
CSV_COLUMNS = [
    # --- Your requested columns ---
    "Paper_ID",
    "Category",
    "Evaluation_Dataset",
    "Environment",
    "Target_Landscape",
    "Winning_Strategy",
    # --- Additional columns from the JSON schema ---
    "Paper_Title",
    "Authors",
    "Year",
    "Source_File",
    "GECCO_Track",
    "Industry",
    "Problem_Context",
    "Dataset_Name",
    "Source_Platform",
    "Benchmark_Name",
    "Dimensionality",
    "Modality",
    "Separability",
    "Landscape_Characteristics",
    "Algorithm_Name",
    "Population_Size",
    "Max_Evaluations_or_Generations",
    "Mutation_Rate",
    "Crossover_Rate",
    "Performance_Metric",
    "Is_Optimal_Found",
]


def flatten_extraction(paper_data: dict, extraction: dict, paper_idx: int, ext_idx: int) -> dict:
    """Flatten a single extraction + metadata into a CSV row dict."""
    meta = paper_data.get("metadata", {})
    domain = extraction.get("the_domain", {})
    database = extraction.get("the_database", {})
    benchmark = extraction.get("the_benchmark_problem", {})
    landscape = extraction.get("the_landscape", {})
    strategy = extraction.get("the_evolutionary_strategy", {})
    params = extraction.get("parameters", {})
    outcome = extraction.get("performance_outcome", {})

    context_type = extraction.get("context_type", "")
    # Map context_type to user-friendly category
    if context_type == "Synthetic Benchmark":
        category = "Pure Math"
    elif context_type == "Real-World Applied":
        category = "Applied"
    else:
        category = context_type

    # Build "Environment" like "10D / 100,000"
    dim = benchmark.get("dimensionality") or ""
    max_evals = params.get("max_evaluations_or_generations")
    pop_size = params.get("population_size")
    env_parts = []
    if dim:
        env_parts.append(str(dim))
    if max_evals is not None:
        env_parts.append(f"{max_evals:,} MaxFEs")
    elif pop_size is not None:
        env_parts.append(f"{pop_size} Pop")
    environment = " / ".join(env_parts) if env_parts else ""

    # Build "Target_Landscape" — combine modality info with benchmark name
    modality = landscape.get("modality", "")
    target_landscape = f"{benchmark.get('name', '')} ({modality})" if modality and modality != "Unknown" else benchmark.get("name", "")

    # Authors as semicolon-separated string
    authors = "; ".join(meta.get("authors", []) or [])

    # Landscape characteristics as semicolon-separated string
    characteristics = "; ".join(landscape.get("characteristics", []))

    # Evaluation dataset — use dataset_name if available, else benchmark name
    eval_dataset = database.get("dataset_name") or benchmark.get("name", "")

    return {
        "Paper_ID": f"Paper_{paper_idx:03d}_Ext_{ext_idx:02d}",
        "Category": category,
        "Evaluation_Dataset": eval_dataset,
        "Environment": environment,
        "Target_Landscape": target_landscape,
        "Winning_Strategy": strategy.get("algorithm_name", ""),
        # Additional columns
        "Paper_Title": meta.get("title", ""),
        "Authors": authors,
        "Year": meta.get("year", ""),
        "Source_File": meta.get("source_file", ""),
        "GECCO_Track": meta.get("gecco_track") or "",
        "Industry": domain.get("industry", ""),
        "Problem_Context": domain.get("problem_context", ""),
        "Dataset_Name": database.get("dataset_name") or "",
        "Source_Platform": database.get("source_platform") or "",
        "Benchmark_Name": benchmark.get("name", ""),
        "Dimensionality": dim,
        "Modality": modality,
        "Separability": landscape.get("separability", ""),
        "Landscape_Characteristics": characteristics,
        "Algorithm_Name": strategy.get("algorithm_name", ""),
        "Population_Size": pop_size if pop_size is not None else "",
        "Max_Evaluations_or_Generations": max_evals if max_evals is not None else "",
        "Mutation_Rate": params.get("mutation_rate") if params.get("mutation_rate") is not None else "",
        "Crossover_Rate": params.get("crossover_rate") if params.get("crossover_rate") is not None else "",
        "Performance_Metric": outcome.get("metric", ""),
        "Is_Optimal_Found": outcome.get("is_optimal_found") if outcome.get("is_optimal_found") is not None else "",
    }


def convert_jsons_to_csv(output_dir: Path, report_path: Path, split_by_year: bool = False) -> int:
    """Read all JSON files and write a single CSV or multiple CSVs split by year.

    Returns:
        Total number of rows written.
    """
    json_files = sorted(output_dir.rglob("*.json"))
    if not json_files:
        print(f"⚠ No JSON files found in {output_dir}")
        return 0

    report_path.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    paper_idx_by_year = {}
    
    rows_by_year = {}
    all_rows = []

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ✗ Skipping {json_file.name}: {e}")
            continue

        folder_year = json_file.parent.name
        year_key = folder_year if folder_year.isdigit() else "Unknown"

        paper_idx_by_year[year_key] = paper_idx_by_year.get(year_key, 0) + 1
        current_paper_idx = paper_idx_by_year[year_key]

        extractions = data.get("extractions", [])

        if not extractions:
            print(f"  ⚠ No extractions in {json_file.name}, skipping")
            continue

        for ext_idx, extraction in enumerate(extractions, start=1):
            row = flatten_extraction(data, extraction, current_paper_idx, ext_idx)
            
            # Use folder name as authoritative year (metadata.year can be wrong)
            if folder_year.isdigit():
                row["Year"] = folder_year
            
            if split_by_year:
                year = row.get("Year") or "Unknown"
                rows_by_year.setdefault(str(year), []).append(row)
            else:
                all_rows.append(row)
                
            total_rows += 1

    if split_by_year:
        for year, rows in sorted(rows_by_year.items()):
            # dataset_analysis.py expects YYYY_dataset.csv
            year_path = report_path.with_name(f"{year}_dataset.csv")
            with open(year_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  Wrote {len(rows)} rows to {year_path}")
    else:
        with open(report_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(all_rows)

    return total_rows


def main():
    parser = argparse.ArgumentParser(description="Convert JSON extractions to CSV")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/outputs"),
        help="Directory containing JSON output files (default: data/outputs)",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("data/reports/gecco_dataset.csv"),
        help="Path for the output CSV file (default: data/reports/gecco_dataset.csv)",
    )
    parser.add_argument(
        "--split-by-year",
        action="store_true",
        help="Split the output into multiple CSV files based on the year",
    )
    args = parser.parse_args()

    print(f"\n📊 Converting JSONs from {args.output_dir} → CSV")
    total = convert_jsons_to_csv(args.output_dir, args.report_path, args.split_by_year)
    print(f"\n✓ Done! Processed {total} total rows.\n")


if __name__ == "__main__":
    main()
