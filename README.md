# GECCO Evolutionary Strategy & Landscape Mapping Pipeline

A Python pipeline that extracts structured data from GECCO conference papers (2020–2026) using Google Gemini, mapping evolutionary strategies to optimization problem landscapes.

## Features

- **Automated PDF Processing**: Sends full PDFs to Gemini 2.5 Flash for native parsing
- **Structured Output**: Pydantic-validated JSON matching a strict data dictionary
- **Anti-Hallucination**: Schema enforcement + low-temperature extraction + explicit null handling
- **Batch Processing**: Progress tracking, resume support, rate limiting
- **Multi-Algorithm Support**: Captures all algorithm–benchmark pairs from each paper

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 3. Add PDFs

Place GECCO paper PDFs in the `data/pdfs/` directory, organized by year:

```
data/pdfs/
├── 2020/
│   ├── paper1.pdf
│   └── paper2.pdf
├── 2021/
│   └── ...
└── 2026/
```

### 4. Run Extraction

```bash
# Process a single PDF (for testing)
python main.py --single data/pdfs/2024/paper.pdf

# Process all PDFs
python main.py --input-dir data/pdfs --output-dir data/outputs

# Process a specific year
python main.py --input-dir data/pdfs --year 2024

# Dry run (see what would be processed)
python main.py --dry-run --input-dir data/pdfs

# Aggregate results into a single dataset
python main.py --aggregate

# To convert the new json data into csv
venv/bin/python json_to_csv.py

# To generate dataset usage statistical charts (All years)
venv/bin/python dataset_analysis.py --top 25

# To generate dataset usage charts for a specific year
venv/bin/python dataset_analysis.py --year 2021


# To convert json data to csv data year wise
venv/bin/python json_to_csv.py --split-by-year

```


## Output Schema

Each paper produces a JSON document with:

- **`metadata`**: Paper title, authors, year, GECCO track
- **`extractions`**: List of algorithm–landscape mappings, each containing:
  - `context_type`: "Real-World Applied" or "Synthetic Benchmark"
  - `the_domain`: Industry and problem context
  - `the_database`: Dataset name and source platform
  - `the_benchmark_problem`: Benchmark name and dimensionality
  - `the_landscape`: Modality, separability, and characteristics
  - `the_evolutionary_strategy`: Algorithm name
  - `parameters`: Population size, evaluations, mutation/crossover rates
  - `performance_outcome`: Metric and optimality

## Configuration

All settings can be configured via environment variables or `.env` file:

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | (required) | Google AI API key |
| `MODEL_NAME` | `gemini-2.5-flash` | Gemini model to use |
| `BATCH_SIZE` | `5` | Concurrent extractions |
| `RATE_LIMIT_RPM` | `60` | Max requests per minute |
| `MAX_RETRIES` | `3` | Retries per failed extraction |
| `TEMPERATURE` | `0.1` | LLM temperature |

## Project Structure

```
├── gecco_pipeline/
│   ├── schemas.py          # Pydantic data models
│   ├── config.py           # Settings & configuration
│   ├── prompt_template.py  # LLM extraction prompts
│   ├── extractor.py        # Gemini API interaction
│   ├── processor.py        # Batch orchestration
│   └── utils.py            # Logging, file I/O, helpers
├── data/
│   ├── pdfs/               # Source PDFs by year
│   ├── outputs/            # Extracted JSON per paper
│   └── reports/            # Aggregated datasets
├── tests/
│   └── test_schemas.py     # Schema validation tests
├── main.py                 # CLI entry point
├── requirements.txt
└── .env.example
```

## Tech Stack

- **Python 3.10+**
- **google-genai** — Gemini API SDK
- **Pydantic v2** — Schema validation
- **loguru** — Structured logging
- **tqdm** — Progress bars

## License

MIT
