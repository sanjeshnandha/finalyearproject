"""Batch processor for orchestrating the GECCO extraction pipeline."""

import json
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from tqdm import tqdm
from loguru import logger

from gecco_pipeline.config import Settings
from gecco_pipeline.extractor import GeccoExtractor
from gecco_pipeline.utils import (
    discover_pdfs,
    get_output_path,
    is_already_processed,
    save_result,
)


@dataclass
class ProcessingStats:
    """Tracks processing statistics across the batch run."""
    total_discovered: int = 0
    total_skipped: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_extractions: int = 0
    failed_files: List[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0

    def summary(self) -> Dict[str, Any]:
        """Return a summary dictionary."""
        return {
            "total_discovered": self.total_discovered,
            "total_skipped": self.total_skipped,
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "total_extractions": self.total_extractions,
            "failed_files": self.failed_files,
            "processing_time_seconds": round(self.processing_time_seconds, 2),
        }


class BatchProcessor:
    """Orchestrates batch processing of GECCO paper PDFs."""

    def __init__(self, settings: Settings):
        """Initialize the batch processor.
        
        Args:
            settings: Pipeline configuration.
        """
        self.settings = settings
        self.extractor = GeccoExtractor(settings)
        logger.info("BatchProcessor initialized")

    def process_single(self, pdf_path: Path, output_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """Process a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file.
            output_dir: Output directory (defaults to settings.OUTPUT_DIR).
        
        Returns:
            Extraction result dictionary, or None if processing failed.
        """
        output_dir = output_dir or self.settings.OUTPUT_DIR
        
        if not pdf_path.exists():
            logger.error(f"PDF not found: {pdf_path}")
            return None
        
        try:
            result = self.extractor.extract_from_pdf(pdf_path)
            result_dict = result.model_dump(mode="json")
            
            # Save output
            output_path = get_output_path(pdf_path, output_dir)
            save_result(result_dict, output_path)
            
            logger.success(f"Successfully processed: {pdf_path.name} → {output_path}")
            return result_dict
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            return None

    def process_batch(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        year: Optional[int] = None,
        skip_existing: bool = True,
        dry_run: bool = False,
    ) -> ProcessingStats:
        """Process a batch of PDF files.
        
        Args:
            input_dir: Directory containing PDF files.
            output_dir: Output directory (defaults to settings.OUTPUT_DIR).
            year: If specified, only process PDFs from this year.
            skip_existing: Skip PDFs that already have output files.
            dry_run: If True, discover files but don't process them.
        
        Returns:
            ProcessingStats with batch statistics.
        """
        output_dir = output_dir or self.settings.OUTPUT_DIR
        stats = ProcessingStats()
        start_time = time.time()
        
        # Discover PDFs
        pdfs = discover_pdfs(input_dir, year)
        stats.total_discovered = len(pdfs)
        
        if not pdfs:
            logger.warning("No PDF files found to process.")
            return stats
        
        # Filter already processed
        if skip_existing:
            pending_pdfs = [
                p for p in pdfs if not is_already_processed(p, output_dir)
            ]
            stats.total_skipped = len(pdfs) - len(pending_pdfs)
            if stats.total_skipped > 0:
                logger.info(f"Skipping {stats.total_skipped} already-processed PDFs")
        else:
            pending_pdfs = pdfs
        
        if dry_run:
            logger.info(f"[DRY RUN] Would process {len(pending_pdfs)} PDFs")
            for pdf in pending_pdfs:
                logger.info(f"  → {pdf.name}")
            stats.processing_time_seconds = time.time() - start_time
            return stats
        
        if not pending_pdfs:
            logger.info("All PDFs already processed. Nothing to do.")
            stats.processing_time_seconds = time.time() - start_time
            return stats
        
        logger.info(f"Processing {len(pending_pdfs)} PDFs...")
        
        # Process sequentially with progress bar
        with tqdm(total=len(pending_pdfs), desc="Extracting papers", unit="paper") as pbar:
            for pdf_path in pending_pdfs:
                try:
                    result = self.extractor.extract_from_pdf(pdf_path)
                    result_dict = result.model_dump(mode="json")
                    
                    # Save output
                    output_path = get_output_path(pdf_path, output_dir)
                    save_result(result_dict, output_path)
                    
                    stats.total_processed += 1
                    stats.total_extractions += len(result.extractions)
                    
                    pbar.set_postfix(
                        ok=stats.total_processed,
                        fail=stats.total_failed,
                        entries=stats.total_extractions,
                    )
                    
                except Exception as e:
                    stats.total_failed += 1
                    stats.failed_files.append(str(pdf_path))
                    logger.error(f"Failed: {pdf_path.name} — {e}")
                
                pbar.update(1)
        
        stats.processing_time_seconds = time.time() - start_time
        
        # Print summary
        self._print_batch_summary(stats)
        
        # Save processing report
        self._save_processing_report(stats, output_dir)
        
        return stats

    def _print_batch_summary(self, stats: ProcessingStats) -> None:
        """Print a formatted summary of batch processing results."""
        print("\n" + "=" * 60)
        print("  GECCO Extraction Pipeline — Batch Summary")
        print("=" * 60)
        print(f"  PDFs discovered:   {stats.total_discovered}")
        print(f"  Skipped (cached):  {stats.total_skipped}")
        print(f"  Processed:         {stats.total_processed}")
        print(f"  Failed:            {stats.total_failed}")
        print(f"  Total extractions: {stats.total_extractions}")
        print(f"  Time elapsed:      {stats.processing_time_seconds:.1f}s")
        
        if stats.total_processed > 0:
            avg_time = stats.processing_time_seconds / stats.total_processed
            print(f"  Avg time/paper:    {avg_time:.1f}s")
        
        if stats.failed_files:
            print(f"\n  ⚠ Failed files:")
            for f in stats.failed_files[:10]:
                print(f"    - {Path(f).name}")
            if len(stats.failed_files) > 10:
                print(f"    ... and {len(stats.failed_files) - 10} more")
        
        print("=" * 60 + "\n")

    def _save_processing_report(self, stats: ProcessingStats, output_dir: Path) -> None:
        """Save processing stats as a JSON report."""
        report_dir = self.settings.REPORTS_DIR
        report_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        report_path = report_dir / f"processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, "w") as f:
            json.dump(stats.summary(), f, indent=2)
        
        logger.info(f"Processing report saved to {report_path}")
