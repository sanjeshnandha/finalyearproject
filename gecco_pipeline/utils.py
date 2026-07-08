"""Utility functions for the GECCO extraction pipeline."""

import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from loguru import logger


def setup_logging(log_dir: Optional[Path] = None, verbose: bool = False) -> None:
    """Configure loguru logging for the pipeline.
    
    Args:
        log_dir: Directory for log files. If None, logs only to stderr.
        verbose: If True, set log level to DEBUG.
    """
    # Remove default handler
    logger.remove()
    
    # Console handler
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )
    
    # File handler
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.add(
            log_dir / f"pipeline_{timestamp}.log",
            level="DEBUG",
            rotation="50 MB",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        )


def discover_pdfs(base_dir: Path, year: Optional[int] = None) -> List[Path]:
    """Discover PDF files in the base directory.
    
    Args:
        base_dir: Root directory containing PDFs (organized by year subdirectories).
        year: If specified, only discover PDFs from this year's subdirectory.
    
    Returns:
        Sorted list of PDF file paths.
    """
    if year:
        search_dir = base_dir / str(year)
        if not search_dir.exists():
            logger.warning(f"Year directory not found: {search_dir}")
            return []
    else:
        search_dir = base_dir
    
    pdfs = sorted(search_dir.rglob("*.pdf"))
    logger.info(f"Discovered {len(pdfs)} PDF files in {search_dir}")
    return pdfs


def get_output_path(pdf_path: Path, output_dir: Path) -> Path:
    """Generate the output JSON path for a given PDF.
    
    Preserves the year subdirectory structure.
    
    Args:
        pdf_path: Path to the source PDF.
        output_dir: Base output directory.
    
    Returns:
        Path for the output JSON file.
    """
    # Try to preserve year directory structure
    try:
        # Check if parent directory name is a year
        year_dir = pdf_path.parent.name
        if year_dir.isdigit() and 2000 <= int(year_dir) <= 2030:
            return output_dir / year_dir / f"{pdf_path.stem}.json"
    except (ValueError, AttributeError):
        pass
    
    return output_dir / f"{pdf_path.stem}.json"


def is_already_processed(pdf_path: Path, output_dir: Path) -> bool:
    """Check if a PDF has already been processed (output JSON exists).
    
    Args:
        pdf_path: Path to the source PDF.
        output_dir: Base output directory.
    
    Returns:
        True if output JSON already exists.
    """
    output_path = get_output_path(pdf_path, output_dir)
    return output_path.exists()


def save_result(result_dict: Dict[str, Any], output_path: Path) -> None:
    """Save extraction result as a formatted JSON file.
    
    Args:
        result_dict: The extraction result dictionary.
        output_path: Path to write the JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False)
    logger.debug(f"Saved result to {output_path}")


def aggregate_results(output_dir: Path, report_path: Path) -> Dict[str, Any]:
    """Aggregate all individual JSON results into a single dataset file.
    
    Args:
        output_dir: Directory containing per-paper JSON files.
        report_path: Path to write the aggregated dataset.
    
    Returns:
        Summary statistics dictionary.
    """
    all_results = []
    json_files = sorted(output_dir.rglob("*.json"))
    
    stats = {
        "total_papers": 0,
        "total_extractions": 0,
        "papers_by_year": {},
        "context_types": {"Real-World Applied": 0, "Synthetic Benchmark": 0},
        "failed_files": [],
    }
    
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            all_results.append(data)
            stats["total_papers"] += 1
            
            # Count extractions
            extractions = data.get("extractions", [])
            stats["total_extractions"] += len(extractions)
            
            # Count by year
            year = str(data.get("metadata", {}).get("year", "unknown"))
            stats["papers_by_year"][year] = stats["papers_by_year"].get(year, 0) + 1
            
            # Count by context type
            for ext in extractions:
                ctx = ext.get("context_type", "")
                if ctx in stats["context_types"]:
                    stats["context_types"][ctx] += 1
                    
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to read {json_file}: {e}")
            stats["failed_files"].append(str(json_file))
    
    # Save aggregated dataset
    report_path.parent.mkdir(parents=True, exist_ok=True)
    dataset = {
        "generated_at": datetime.now().isoformat(),
        "statistics": stats,
        "papers": all_results,
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Aggregated {stats['total_papers']} papers with {stats['total_extractions']} total extractions")
    logger.info(f"Dataset saved to {report_path}")
    
    return stats


def print_stats(stats: Dict[str, Any]) -> None:
    """Print a formatted summary of extraction statistics."""
    print("\n" + "=" * 60)
    print("  GECCO Extraction Pipeline — Summary Report")
    print("=" * 60)
    print(f"  Total papers processed: {stats['total_papers']}")
    print(f"  Total extractions:      {stats['total_extractions']}")
    print(f"  Avg extractions/paper:  {stats['total_extractions'] / max(stats['total_papers'], 1):.1f}")
    print()
    print("  By Year:")
    for year in sorted(stats["papers_by_year"].keys()):
        print(f"    {year}: {stats['papers_by_year'][year]} papers")
    print()
    print("  By Context Type:")
    for ctx, count in stats["context_types"].items():
        print(f"    {ctx}: {count}")
    
    if stats["failed_files"]:
        print(f"\n  ⚠ Failed files: {len(stats['failed_files'])}")
        for f in stats["failed_files"][:5]:
            print(f"    - {f}")
        if len(stats["failed_files"]) > 5:
            print(f"    ... and {len(stats['failed_files']) - 5} more")
    
    print("=" * 60 + "\n")
