"""GECCO Extraction Pipeline — CLI Entry Point.

Extracts structured evolutionary strategy ↔ landscape mappings from
GECCO conference papers using Google Gemini.

Usage:
    # Process all PDFs
    python main.py --input-dir data/pdfs --output-dir data/outputs

    # Process a single year
    python main.py --input-dir data/pdfs --output-dir data/outputs --year 2024

    # Process a single PDF
    python main.py --single data/pdfs/2024/some_paper.pdf

    # Dry run (discover files without processing)
    python main.py --input-dir data/pdfs --dry-run

    # Aggregate all outputs into a single dataset
    python main.py --aggregate
"""

import argparse
import sys
from pathlib import Path

from gecco_pipeline.config import get_settings
from gecco_pipeline.utils import setup_logging, aggregate_results, print_stats


def main():
    parser = argparse.ArgumentParser(
        description="GECCO Paper Extraction Pipeline — Extract ES ↔ Landscape mappings using Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input-dir data/pdfs --output-dir data/outputs
  python main.py --single data/pdfs/2024/paper.pdf
  python main.py --input-dir data/pdfs --year 2024
  python main.py --dry-run --input-dir data/pdfs
  python main.py --aggregate
        """,
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--single",
        type=Path,
        help="Process a single PDF file.",
    )
    mode_group.add_argument(
        "--aggregate",
        action="store_true",
        help="Aggregate all output JSONs into a single dataset.",
    )

    # Input/Output
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing PDF files (default: from config).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for output JSON files (default: from config).",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="Directory for aggregate reports (default: from config).",
    )

    # Filtering
    parser.add_argument(
        "--year",
        type=int,
        choices=range(2020, 2027),
        help="Only process papers from a specific year.",
    )

    # Processing options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover files and show what would be processed, without making API calls.",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Re-process papers even if output JSON already exists.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(log_dir=Path("logs"), verbose=args.verbose)

    # Load settings
    try:
        settings = get_settings()
    except Exception as e:
        if not args.dry_run and not args.aggregate:
            print(f"\n✗ Configuration error: {e}")
            print("  Make sure GOOGLE_API_KEY is set in your .env file or environment.")
            print("  See .env.example for reference.\n")
            sys.exit(1)
        # For dry-run and aggregate, we don't need the API key
        # Create a minimal settings object
        from gecco_pipeline.config import Settings
        settings = None

    # Override paths from CLI args
    if args.input_dir and settings:
        settings.PDF_BASE_DIR = args.input_dir
    if args.output_dir and settings:
        settings.OUTPUT_DIR = args.output_dir
    if args.report_dir and settings:
        settings.REPORTS_DIR = args.report_dir

    # --- Mode: Aggregate ---
    if args.aggregate:
        output_dir = args.output_dir or (settings.OUTPUT_DIR if settings else Path("data/outputs"))
        report_dir = args.report_dir or (settings.REPORTS_DIR if settings else Path("data/reports"))
        report_path = report_dir / "gecco_full_dataset.json"
        
        print(f"\n📊 Aggregating results from {output_dir}...")
        stats = aggregate_results(output_dir, report_path)
        print_stats(stats)
        return

    # --- Mode: Single PDF ---
    if args.single:
        if settings is None:
            print("\n✗ API key required for extraction. Set GOOGLE_API_KEY.\n")
            sys.exit(1)
        
        from gecco_pipeline.processor import BatchProcessor
        processor = BatchProcessor(settings)
        
        output_dir = args.output_dir or settings.OUTPUT_DIR
        print(f"\n📄 Processing single PDF: {args.single}")
        result = processor.process_single(args.single, output_dir)
        
        if result:
            import json
            print("\n✓ Extraction result:")
            print(json.dumps(result, indent=2))
        else:
            print("\n✗ Extraction failed. Check logs for details.")
            sys.exit(1)
        return

    # --- Mode: Batch Processing ---
    input_dir = args.input_dir or (settings.PDF_BASE_DIR if settings else Path("data/pdfs"))
    output_dir = args.output_dir or (settings.OUTPUT_DIR if settings else Path("data/outputs"))

    if args.dry_run:
        # Dry run doesn't need settings/API key
        from gecco_pipeline.utils import discover_pdfs, is_already_processed
        
        pdfs = discover_pdfs(input_dir, args.year)
        pending = [p for p in pdfs if not is_already_processed(p, output_dir)]
        cached = len(pdfs) - len(pending)
        
        print(f"\n🔍 [DRY RUN] PDF Discovery Report")
        print(f"   Directory: {input_dir}")
        if args.year:
            print(f"   Year filter: {args.year}")
        print(f"   Total PDFs found: {len(pdfs)}")
        print(f"   Already processed: {cached}")
        print(f"   Pending: {len(pending)}")
        if pending:
            print(f"\n   Files to process:")
            for p in pending[:20]:
                print(f"     → {p.name}")
            if len(pending) > 20:
                print(f"     ... and {len(pending) - 20} more")
        print()
        return

    if settings is None:
        print("\n✗ API key required for extraction. Set GOOGLE_API_KEY.\n")
        sys.exit(1)

    from gecco_pipeline.processor import BatchProcessor
    processor = BatchProcessor(settings)
    
    stats = processor.process_batch(
        input_dir=input_dir,
        output_dir=output_dir,
        year=args.year,
        skip_existing=not args.no_skip,
        dry_run=False,
    )
    
    if stats.total_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
