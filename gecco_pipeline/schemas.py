from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Domain(BaseModel):
    """Domain classification for the paper."""
    industry: str = Field(description="e.g., Medical/Healthcare, Engineering/Manufacturing, Energy/Power, Logistics/Supply Chain, or 'None / Pure Synthetic'")
    problem_context: str = Field(description="e.g., Pressure Vessel Design, Vehicle routing, or 'Evaluating mathematical landscapes'")


class Database(BaseModel):
    """Database/dataset used in the paper."""
    dataset_name: Optional[str] = Field(default=None, description="e.g., Pima Indians Diabetes, MNIST, Custom Simulated Data, or null if pure mathematical function")
    source_platform: Optional[str] = Field(default=None, description="e.g., UCI Repository, Kaggle, or null")


class BenchmarkProblem(BaseModel):
    """Benchmark problem evaluated in the paper."""
    name: str = Field(description="e.g., Rastrigin, Rosenbrock, CEC 2020 Suite, Traveling Salesman Problem")
    dimensionality: Optional[str] = Field(default=None, description="e.g., 10D, 30D, Variable, or null")


class Landscape(BaseModel):
    """Mathematical landscape characteristics."""
    modality: Literal['Unimodal', 'Multimodal', 'Unknown'] = Field(description="Landscape modality classification")
    separability: Literal['Separable', 'Non-separable', 'Unknown'] = Field(description="Landscape separability classification")
    characteristics: List[str] = Field(default_factory=list, description="e.g., 'conditioned', 'noisy', 'rugged', 'flat regions'")


class EvolutionaryStrategy(BaseModel):
    """The evolutionary algorithm/strategy used."""
    algorithm_name: str = Field(description="e.g., CMA-ES, Differential Evolution (DE), Genetic Algorithm (GA)")


class Parameters(BaseModel):
    """Algorithm parameters."""
    population_size: Optional[int] = Field(default=None)
    max_evaluations_or_generations: Optional[int] = Field(default=None)
    mutation_rate: Optional[float] = Field(default=None)
    crossover_rate: Optional[float] = Field(default=None)


class PerformanceOutcome(BaseModel):
    """Performance results of the algorithm."""
    metric: str = Field(description="e.g., Best fitness value achieved, Convergence speed")
    is_optimal_found: Optional[bool] = Field(default=None)


class PaperExtraction(BaseModel):
    """A single algorithm-to-landscape mapping extracted from a paper."""
    context_type: Literal['Real-World Applied', 'Synthetic Benchmark']
    the_domain: Domain
    the_database: Database
    the_benchmark_problem: BenchmarkProblem
    the_landscape: Landscape
    the_evolutionary_strategy: EvolutionaryStrategy
    parameters: Parameters
    performance_outcome: PerformanceOutcome


class PaperMetadata(BaseModel):
    """Metadata about the source paper."""
    title: Optional[str] = Field(default=None)
    authors: Optional[List[str]] = Field(default=None)
    year: int
    source_file: str
    gecco_track: Optional[str] = Field(default=None)


class PaperResult(BaseModel):
    """Top-level document containing all extractions from a single paper."""
    metadata: PaperMetadata
    extractions: List[PaperExtraction]
