"""
USABench: A comprehensive evaluation framework for government economic data analysis.

This package provides tools for evaluating language models on:
- Text-to-SQL tasks using government economic databases
- Function calling tasks for economic data retrieval and analysis

Key Components:
- Core evaluation framework with unified abstractions
- SQL and function calling evaluators with validation strategies
- High-level SDK for easy integration and usage
- Comprehensive results analysis and reporting

Quick Start:
    from USABench import USABench, quick_eval
    
    # Quick evaluation
    results = quick_eval(model_name="gpt-4o", evaluation_type="mixed")
    
    # Advanced usage
    benchmark = USABench()
    results = benchmark.run_and_analyze(evaluation_type="sql", sql_samples=50)
"""

from .core import (
    BaseEvaluator,
    DataLoader,
    Difficulty,
    EvaluationConfig,
    EvaluationResult,
    EvaluationType,
    LLMClient,
    UnifiedSample,
)
from .evaluators import FunctionEvaluator, SQLEvaluator
from .sdk import BenchmarkConfig, ResultsAnalyzer, USABench, quick_eval

__version__ = "1.0.0"
__author__ = "USABench Team"

__all__ = [
    # SDK
    'USABench',
    'BenchmarkConfig',
    'ResultsAnalyzer',
    'quick_eval',

    # Core
    'BaseEvaluator',
    'UnifiedSample',
    'EvaluationResult',
    'EvaluationType',
    'Difficulty',
    'EvaluationConfig',
    'LLMClient',
    'DataLoader',

    # Evaluators
    'SQLEvaluator',
    'FunctionEvaluator'
]
