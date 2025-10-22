from typing import Any, Dict, List, Optional

from USABench.core.base import Difficulty, EvaluationResult, EvaluationType
from USABench.core.loader import DataLoader
from USABench.evaluators.berkeley_function import FunctionCallEvaluator
from USABench.evaluators.production_sql import ProductionSQLEvaluator
from .config import BenchmarkConfig
from .results import ResultsAnalyzer


class USABench:
    """High-level SDK interface for USABench evaluation framework."""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.data_loader = DataLoader(self.config.data_dir)

        # Initialize evaluators lazily
        self._sql_evaluator = None
        self._function_evaluator = None

    @property
    def sql_evaluator(self) -> ProductionSQLEvaluator:
        """Lazy initialization of SQL evaluator."""
        if self._sql_evaluator is None:
            eval_config = self.config.to_evaluation_config()
            self._sql_evaluator = ProductionSQLEvaluator(eval_config, self.config.db_path)
        return self._sql_evaluator

    @property
    def function_evaluator(self) -> FunctionCallEvaluator:
        """Lazy initialization of function evaluator."""
        if self._function_evaluator is None:
            eval_config = self.config.to_evaluation_config()
            self._function_evaluator = FunctionCallEvaluator(eval_config)
        return self._function_evaluator

    def run_sql_evaluation(
        self,
        max_samples: Optional[int] = None,
        difficulty_filter: Optional[List[Difficulty]] = None
    ) -> List[EvaluationResult]:
        """Run SQL evaluation only."""
        samples = self.data_loader.load_sql_samples(
            max_samples=max_samples or self.config.sql_samples,
            difficulty_filter=difficulty_filter or self.config.difficulty_filter
        )

        return self.sql_evaluator.evaluate_batch(samples)

    def run_function_evaluation(
        self,
        max_samples: Optional[int] = None,
        difficulty_filter: Optional[List[Difficulty]] = None
    ) -> List[EvaluationResult]:
        """Run function calling evaluation only."""
        samples = self.data_loader.load_function_samples(
            max_samples=max_samples or self.config.function_samples,
            difficulty_filter=difficulty_filter or self.config.difficulty_filter
        )

        return self.function_evaluator.evaluate_batch(samples)

    def run_mixed_evaluation(
        self,
        sql_samples: Optional[int] = None,
        function_samples: Optional[int] = None,
        difficulty_filter: Optional[List[Difficulty]] = None
    ) -> List[EvaluationResult]:
        """Run both SQL and function calling evaluations."""
        samples = self.data_loader.load_mixed_samples(
            sql_count=sql_samples or self.config.sql_samples,
            function_count=function_samples or self.config.function_samples,
            difficulty_filter=difficulty_filter or self.config.difficulty_filter
        )

        results = []

        # Separate samples by type
        sql_samples = [s for s in samples if s.evaluation_type == EvaluationType.SQL]
        function_samples = [s for s in samples if s.evaluation_type == EvaluationType.FUNCTION]

        # Run evaluations
        if sql_samples:
            sql_results = self.sql_evaluator.evaluate_batch(sql_samples)
            results.extend(sql_results)

        if function_samples:
            function_results = self.function_evaluator.evaluate_batch(function_samples)
            results.extend(function_results)

        return results

    def run_full_evaluation(self) -> List[EvaluationResult]:
        """Run comprehensive evaluation with all available samples."""
        return self.run_mixed_evaluation()

    def analyze_results(self, results: List[EvaluationResult]) -> ResultsAnalyzer:
        """Create results analyzer for detailed analysis."""
        return ResultsAnalyzer(results)

    def run_and_analyze(
        self,
        evaluation_type: str = "mixed",
        sql_samples: Optional[int] = None,
        function_samples: Optional[int] = None,
        difficulty_filter: Optional[List[Difficulty]] = None,
        save_results: Optional[bool] = None,
        generate_report: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Run evaluation and return comprehensive analysis."""
        # Run evaluation
        if evaluation_type == "sql":
            results = self.run_sql_evaluation(sql_samples, difficulty_filter)
        elif evaluation_type == "function":
            results = self.run_function_evaluation(function_samples, difficulty_filter)
        elif evaluation_type == "mixed":
            results = self.run_mixed_evaluation(sql_samples, function_samples, difficulty_filter)
        elif evaluation_type == "full":
            results = self.run_full_evaluation()
        else:
            raise ValueError(f"Unknown evaluation type: {evaluation_type}")

        # Analyze results
        analyzer = self.analyze_results(results)

        # Prepare output
        output = {
            'results': results,
            'analyzer': analyzer,
            'overall_metrics': analyzer.get_overall_metrics(),
            'metrics_by_type': analyzer.get_metrics_by_type(),
            'metrics_by_difficulty': analyzer.get_metrics_by_difficulty(),
            'detailed_breakdown': analyzer.get_detailed_breakdown(),
            'error_analysis': analyzer.get_error_analysis()
        }

        # Save results if requested
        save_results = save_results if save_results is not None else self.config.save_results
        if save_results:
            saved_files = analyzer.save_results(self.config.output_dir)
            output['saved_files'] = saved_files

        # Generate report if requested
        generate_report = generate_report if generate_report is not None else self.config.generate_report
        if generate_report:
            report = analyzer.generate_report()
            output['report'] = report

        return output

    def get_dataset_info(self) -> Dict[str, Any]:
        """Get information about available datasets."""
        return self.data_loader.get_dataset_info()

    # Fluent API methods for configuration
    def with_model(self, model_name: str) -> 'USABench':
        """Set model name."""
        self.config.model_name = model_name
        # Reset evaluators to use new model
        self._sql_evaluator = None
        self._function_evaluator = None
        return self

    def with_temperature(self, temperature: float) -> 'USABench':
        """Set temperature."""
        self.config.temperature = temperature
        # Reset evaluators
        self._sql_evaluator = None
        self._function_evaluator = None
        return self

    def with_data_dir(self, data_dir: str) -> 'USABench':
        """Set data directory."""
        self.config.data_dir = data_dir
        self.data_loader = DataLoader(data_dir)
        return self

    def with_db_path(self, db_path: str) -> 'USABench':
        """Set database path."""
        self.config.db_path = db_path
        # Reset SQL evaluator
        self._sql_evaluator = None
        return self

    def with_output_dir(self, output_dir: str) -> 'USABench':
        """Set output directory."""
        self.config.output_dir = output_dir
        return self


# Convenience function for quick evaluation
def quick_eval(
    model_name: str = "gpt-4o",
    evaluation_type: str = "mixed",
    sql_samples: int = 10,
    function_samples: int = 10,
    data_dir: str = "data",
    db_path: str = "data/usafacts.db"
) -> Dict[str, Any]:
    """Quick evaluation with minimal configuration."""
    config = BenchmarkConfig(
        model_name=model_name,
        sql_samples=sql_samples,
        function_samples=function_samples,
        data_dir=data_dir,
        db_path=db_path
    )

    benchmark = USABench(config)
    return benchmark.run_and_analyze(evaluation_type=evaluation_type)
