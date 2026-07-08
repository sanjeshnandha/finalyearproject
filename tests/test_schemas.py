"""Tests for GECCO extraction pipeline Pydantic schemas."""

import json
import pytest
from pydantic import ValidationError

from gecco_pipeline.schemas import (
    Domain,
    Database,
    BenchmarkProblem,
    Landscape,
    EvolutionaryStrategy,
    Parameters,
    PerformanceOutcome,
    PaperExtraction,
    PaperMetadata,
    PaperResult,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def synthetic_extraction_data():
    """Valid data for a synthetic benchmark extraction."""
    return {
        "context_type": "Synthetic Benchmark",
        "the_domain": {
            "industry": "None / Pure Synthetic",
            "problem_context": "Evaluating mathematical landscapes",
        },
        "the_database": {
            "dataset_name": None,
            "source_platform": None,
        },
        "the_benchmark_problem": {
            "name": "Rastrigin",
            "dimensionality": "30D",
        },
        "the_landscape": {
            "modality": "Multimodal",
            "separability": "Separable",
            "characteristics": ["highly multimodal", "regular structure"],
        },
        "the_evolutionary_strategy": {
            "algorithm_name": "CMA-ES",
        },
        "parameters": {
            "population_size": 100,
            "max_evaluations_or_generations": 10000,
            "mutation_rate": None,
            "crossover_rate": None,
        },
        "performance_outcome": {
            "metric": "Best fitness value achieved",
            "is_optimal_found": True,
        },
    }


@pytest.fixture
def applied_extraction_data():
    """Valid data for a real-world applied extraction."""
    return {
        "context_type": "Real-World Applied",
        "the_domain": {
            "industry": "Medical/Healthcare",
            "problem_context": "Feature selection for diabetes prediction",
        },
        "the_database": {
            "dataset_name": "Pima Indians Diabetes",
            "source_platform": "UCI Repository",
        },
        "the_benchmark_problem": {
            "name": "Feature Selection",
            "dimensionality": "8D",
        },
        "the_landscape": {
            "modality": "Unknown",
            "separability": "Unknown",
            "characteristics": [],
        },
        "the_evolutionary_strategy": {
            "algorithm_name": "Genetic Algorithm (GA)",
        },
        "parameters": {
            "population_size": 50,
            "max_evaluations_or_generations": 500,
            "mutation_rate": 0.01,
            "crossover_rate": 0.8,
        },
        "performance_outcome": {
            "metric": "Classification accuracy",
            "is_optimal_found": None,
        },
    }


@pytest.fixture
def paper_result_data(synthetic_extraction_data, applied_extraction_data):
    """Valid data for a complete PaperResult."""
    return {
        "metadata": {
            "title": "Comparing CMA-ES and GA on Benchmark and Applied Problems",
            "authors": ["Alice Smith", "Bob Jones"],
            "year": 2024,
            "source_file": "2024_Smith_CMAES_vs_GA.pdf",
            "gecco_track": "Genetic Algorithms",
        },
        "extractions": [synthetic_extraction_data, applied_extraction_data],
    }


# ──────────────────────────────────────────────
# Test: Valid data accepted
# ──────────────────────────────────────────────

class TestValidData:
    def test_domain(self):
        d = Domain(industry="Medical/Healthcare", problem_context="Tumor detection")
        assert d.industry == "Medical/Healthcare"

    def test_database_with_nulls(self):
        db = Database(dataset_name=None, source_platform=None)
        assert db.dataset_name is None
        assert db.source_platform is None

    def test_database_with_values(self):
        db = Database(dataset_name="MNIST", source_platform="Kaggle")
        assert db.dataset_name == "MNIST"

    def test_landscape_valid_literals(self):
        ls = Landscape(modality="Multimodal", separability="Non-separable", characteristics=["rugged"])
        assert ls.modality == "Multimodal"
        assert ls.separability == "Non-separable"

    def test_parameters_all_null(self):
        p = Parameters()
        assert p.population_size is None
        assert p.mutation_rate is None

    def test_parameters_with_values(self):
        p = Parameters(population_size=200, mutation_rate=0.05)
        assert p.population_size == 200
        assert p.mutation_rate == 0.05

    def test_performance_outcome(self):
        po = PerformanceOutcome(metric="Convergence speed", is_optimal_found=False)
        assert po.metric == "Convergence speed"
        assert po.is_optimal_found is False

    def test_paper_extraction_synthetic(self, synthetic_extraction_data):
        ext = PaperExtraction(**synthetic_extraction_data)
        assert ext.context_type == "Synthetic Benchmark"
        assert ext.the_benchmark_problem.name == "Rastrigin"
        assert ext.the_evolutionary_strategy.algorithm_name == "CMA-ES"

    def test_paper_extraction_applied(self, applied_extraction_data):
        ext = PaperExtraction(**applied_extraction_data)
        assert ext.context_type == "Real-World Applied"
        assert ext.the_domain.industry == "Medical/Healthcare"

    def test_paper_result(self, paper_result_data):
        result = PaperResult(**paper_result_data)
        assert result.metadata.title is not None
        assert len(result.extractions) == 2
        assert result.metadata.year == 2024

    def test_paper_metadata_minimal(self):
        meta = PaperMetadata(year=2023, source_file="paper.pdf")
        assert meta.title is None
        assert meta.authors is None
        assert meta.gecco_track is None


# ──────────────────────────────────────────────
# Test: Invalid data rejected
# ──────────────────────────────────────────────

class TestInvalidData:
    def test_invalid_modality_literal(self):
        with pytest.raises(ValidationError):
            Landscape(modality="Bimodal", separability="Separable", characteristics=[])

    def test_invalid_separability_literal(self):
        with pytest.raises(ValidationError):
            Landscape(modality="Unimodal", separability="Partially-separable", characteristics=[])

    def test_invalid_context_type(self):
        with pytest.raises(ValidationError):
            PaperExtraction(
                context_type="Hybrid",  # Invalid
                the_domain=Domain(industry="Test", problem_context="Test"),
                the_database=Database(),
                the_benchmark_problem=BenchmarkProblem(name="Test"),
                the_landscape=Landscape(modality="Unimodal", separability="Separable", characteristics=[]),
                the_evolutionary_strategy=EvolutionaryStrategy(algorithm_name="Test"),
                parameters=Parameters(),
                performance_outcome=PerformanceOutcome(metric="Test"),
            )

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            Domain(industry="Medical")  # Missing problem_context

    def test_missing_algorithm_name(self):
        with pytest.raises(ValidationError):
            EvolutionaryStrategy()  # Missing algorithm_name

    def test_missing_benchmark_name(self):
        with pytest.raises(ValidationError):
            BenchmarkProblem()  # Missing name


# ──────────────────────────────────────────────
# Test: JSON round-trip
# ──────────────────────────────────────────────

class TestJsonRoundTrip:
    def test_extraction_roundtrip(self, synthetic_extraction_data):
        ext = PaperExtraction(**synthetic_extraction_data)
        json_str = ext.model_dump_json()
        restored = PaperExtraction.model_validate_json(json_str)
        assert restored == ext

    def test_result_roundtrip(self, paper_result_data):
        result = PaperResult(**paper_result_data)
        json_str = result.model_dump_json()
        restored = PaperResult.model_validate_json(json_str)
        assert restored == result
        assert len(restored.extractions) == 2

    def test_json_nulls_preserved(self):
        db = Database(dataset_name=None, source_platform=None)
        data = json.loads(db.model_dump_json())
        assert data["dataset_name"] is None
        assert data["source_platform"] is None

    def test_empty_characteristics_list(self):
        ls = Landscape(modality="Unknown", separability="Unknown", characteristics=[])
        data = json.loads(ls.model_dump_json())
        assert data["characteristics"] == []
