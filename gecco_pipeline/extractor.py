"""Core extraction engine using Google Gemini API."""

import time
import random
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from loguru import logger

from gecco_pipeline.config import Settings
from gecco_pipeline.schemas import PaperResult, PaperExtraction, PaperMetadata
from gecco_pipeline.prompt_template import SYSTEM_PROMPT, EXTRACTION_PROMPT


class GeccoExtractor:
    """Extracts structured data from GECCO papers using Gemini."""

    def __init__(self, settings: Settings):
        """Initialize the extractor with API client and settings.
        
        Args:
            settings: Pipeline configuration settings.
        """
        self.settings = settings
        self.client = genai.Client(
            api_key=settings.GOOGLE_API_KEY,
            http_options=types.HttpOptions(
                api_version="v1beta",
            ),
        )
        self._request_count = 0
        self._window_start = time.time()
        logger.info(f"Initialized GeccoExtractor with model: {settings.MODEL_NAME}")

    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting based on RPM configuration."""
        self._request_count += 1
        elapsed = time.time() - self._window_start
        
        if elapsed < 60:
            if self._request_count >= self.settings.RATE_LIMIT_RPM:
                wait_time = 60 - elapsed + random.uniform(0.5, 2.0)
                logger.info(f"Rate limit reached ({self._request_count} requests in {elapsed:.1f}s). Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self._request_count = 0
                self._window_start = time.time()
        else:
            # Reset window
            self._request_count = 0
            self._window_start = time.time()

    def extract_from_pdf(self, pdf_path: Path, year: Optional[int] = None) -> PaperResult:
        """Extract structured data from a single GECCO paper PDF.
        
        Args:
            pdf_path: Path to the PDF file.
            year: Publication year (used for metadata if not extractable).
        
        Returns:
            PaperResult with metadata and all algorithm-landscape extractions.
        
        Raises:
            Exception: If extraction fails after all retries.
        """
        logger.info(f"Processing: {pdf_path.name}")
        
        # Determine year from directory name if not provided
        if year is None:
            try:
                parent_name = pdf_path.parent.name
                if parent_name.isdigit() and 2000 <= int(parent_name) <= 2030:
                    year = int(parent_name)
            except (ValueError, AttributeError):
                pass
        
        if year is None:
            year = 2024  # Fallback default
            logger.warning(f"Could not determine year for {pdf_path.name}, using {year}")
        
        # Upload PDF to Gemini File API
        uploaded_file = self._upload_pdf(pdf_path)
        
        # Build the prompt with source file placeholder replaced
        prompt = EXTRACTION_PROMPT.replace("__SOURCE_FILE__", pdf_path.name)
        
        # Call Gemini with retry logic
        result = self._call_with_retry(uploaded_file, prompt, pdf_path.name, year)
        
        # Replace source_file placeholder in metadata
        result.metadata.source_file = pdf_path.name
        if result.metadata.year == 0:
            result.metadata.year = year
        
        logger.success(f"Extracted {len(result.extractions)} entries from {pdf_path.name}")
        return result

    def _upload_pdf(self, pdf_path: Path):
        """Upload a PDF file to the Gemini File API.
        
        Args:
            pdf_path: Path to the PDF file.
        
        Returns:
            Uploaded file object from the Gemini API.
        """
        logger.debug(f"Uploading {pdf_path.name} to Gemini File API...")
        try:
            uploaded_file = self.client.files.upload(file=pdf_path)
            logger.debug(f"Upload complete: {uploaded_file.name}")
            return uploaded_file
        except Exception as e:
            logger.error(f"Failed to upload {pdf_path.name}: {e}")
            raise

    def _call_with_retry(self, uploaded_file, prompt: str, filename: str, year: int) -> PaperResult:
        """Call Gemini API with exponential backoff retry.
        
        Args:
            uploaded_file: The uploaded PDF file object.
            prompt: The extraction prompt.
            filename: Original filename for logging.
            year: Publication year.
        
        Returns:
            Validated PaperResult.
        
        Raises:
            Exception: If all retries are exhausted.
        """
        last_exception = None
        
        for attempt in range(1, self.settings.MAX_RETRIES + 1):
            try:
                self._rate_limit_wait()
                
                response = self.client.models.generate_content(
                    model=self.settings.MODEL_NAME,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_uri(
                                    file_uri=uploaded_file.uri,
                                    mime_type="application/pdf",
                                ),
                                types.Part.from_text(text=prompt),
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=PaperResult,
                        temperature=self.settings.TEMPERATURE,
                    ),
                )
                
                # Use the SDK's built-in parsed response
                if response.parsed:
                    return response.parsed
                
                # Fallback: manually parse if .parsed is None
                if response.text:
                    result = PaperResult.model_validate_json(response.text)
                    return result
                
                raise ValueError(f"Empty response from Gemini for {filename}")
                
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # Don't retry on non-transient errors
                if "400" in error_str or "403" in error_str or "404" in error_str:
                    logger.error(f"Non-retryable error for {filename}: {e}")
                    raise
                
                if attempt < self.settings.MAX_RETRIES:
                    wait_time = (self.settings.RETRY_BASE_DELAY ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"Attempt {attempt}/{self.settings.MAX_RETRIES} failed for {filename}: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.settings.MAX_RETRIES} attempts failed for {filename}: {e}")
        
        raise last_exception

    def cleanup_uploaded_file(self, file_name: str) -> None:
        """Delete an uploaded file from the Gemini File API.
        
        Args:
            file_name: The name of the uploaded file to delete.
        """
        try:
            self.client.files.delete(name=file_name)
            logger.debug(f"Deleted uploaded file: {file_name}")
        except Exception as e:
            logger.warning(f"Failed to delete uploaded file {file_name}: {e}")
