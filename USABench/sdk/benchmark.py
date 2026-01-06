#!/usr/bin/env python3
"""
Multi-model benchmark runner for USABench.

Runs evaluations across multiple models and generates leaderboard JSON.
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv not installed, will use system environment variables

from USABench.sdk.api import USABench
from USABench.sdk.config import BenchmarkConfig
from USABench.core.base import Difficulty

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Model Registry - Core Configuration
MODEL_REGISTRY = {
    # OpenAI Models
    "gpt-5-chat": {
        "display_name": "GPT-5 Chat",
        "organization": "OpenAI",
        "requires_api_keys": ["OPENAI_API_KEY"]
    },
    "gpt-5-mini": {
        "display_name": "GPT-5 Mini",
        "organization": "OpenAI",
        "requires_api_keys": ["OPENAI_API_KEY"]
    },
    "gpt-4o": {
        "display_name": "GPT-4o",
        "organization": "OpenAI",
        "requires_api_keys": ["OPENAI_API_KEY"]
    },
    "gpt-3.5-turbo": {
        "display_name": "GPT-3.5 Turbo",
        "organization": "OpenAI",
        "requires_api_keys": ["OPENAI_API_KEY"]
    },
    # Anthropic Models
    "claude-3-5-sonnet-20241022": {
        "display_name": "Claude 3.5 Sonnet",
        "organization": "Anthropic",
        "requires_api_keys": ["ANTHROPIC_API_KEY"]
    },
    "claude-3-5-haiku-20241022": {
        "display_name": "Claude 3.5 Haiku",
        "organization": "Anthropic",
        "requires_api_keys": ["ANTHROPIC_API_KEY"]
    },
    "claude-sonnet-4-5-20250929": {
        "display_name": "Claude 4.5 Sonnet",
        "organization": "Anthropic",
        "requires_api_keys": ["ANTHROPIC_API_KEY"]
    },
    "claude-opus-4-5-20251101": {
        "display_name": "Claude 4.5 Opus",
        "organization": "Anthropic",
        "requires_api_keys": ["ANTHROPIC_API_KEY"]
    },
    # Gemini Models
    "gemini/gemini-2.0-flash": {
        "display_name": "Gemini 2.0 Flash",
        "organization": "Google",
        "requires_api_keys": ["GEMINI_API_KEY"]
    },
    # Groq
    "groq/llama-3.3-70b-versatile": {
        "display_name": "Froq Llama 3.3 70B Versatile",
        "organization": "Groq",
        "requires_api_keys": ["GROQ_API_KEY"]
    }
}


@dataclass
class BenchmarkRunnerConfig:
    """Configuration for benchmark runner."""
    models: List[str]
    sql_samples: Optional[int] = None  # None means all samples
    function_samples: Optional[int] = None  # None means all samples
    output_dir: str = "results"
    temperature: float = 0.0
    max_tokens: int = 2000
    timeout: int = 30
    difficulty_filter: Optional[List[Difficulty]] = None
    skip_on_missing_keys: bool = True
    delay_between_runs: int = 5
    data_dir: str = "USABench/data"
    db_path: str = "USABench/data/usafacts.db"


@dataclass
class ModelRunResult:
    """Result of a single model's benchmark run."""
    model_id: str
    display_name: str
    organization: str
    success: bool
    easy_success: Optional[float] = None
    medium_success: Optional[float] = None
    hard_success: Optional[float] = None
    sql_success: Optional[float] = None
    function_success: Optional[float] = None
    total_samples: int = 0
    execution_time: float = 0.0
    temperature: float = 0.0
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class BenchmarkRunner:
    """Multi-model benchmark runner."""

    def __init__(self, config: BenchmarkRunnerConfig):
        """Initialize benchmark runner.

        Args:
            config: BenchmarkRunnerConfig object with settings
        """
        self.config = config
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(config.output_dir) / f"benchmark-{self.timestamp}"
        self.results: List[ModelRunResult] = []

    def validate_api_keys(self) -> Dict[str, List[str]]:
        """Validate API keys and return available/missing keys.

        Returns:
            Dict with 'available' and 'missing' lists of API key names
        """
        # Collect all unique API keys required by models in registry
        all_keys = set()
        for model_info in MODEL_REGISTRY.values():
            all_keys.update(model_info["requires_api_keys"])

        # Add optional API keys for function calling
        all_keys.update(["BLS_API_KEY", "BEA_API_KEY"])

        all_keys = sorted(list(all_keys))

        available = []
        missing = []

        for key in all_keys:
            if os.getenv(key):
                available.append(key)
            else:
                missing.append(key)

        # Log warnings for missing keys
        if missing:
            logger.warning("=" * 60)
            logger.warning("MISSING API KEYS:")
            for key in missing:
                logger.warning(f"  - {key}")
            logger.warning("Some models may be skipped.")
            logger.warning("=" * 60)

        return {"available": available, "missing": missing}

    def filter_models_by_keys(self, available_keys: List[str]) -> List[str]:
        """Filter models based on available API keys.

        Args:
            available_keys: List of available API key names

        Returns:
            List of model IDs that can be run
        """
        runnable_models = []
        skipped_models = []

        for model_id in self.config.models:
            if model_id not in MODEL_REGISTRY:
                logger.warning(f"Unknown model '{model_id}' - skipping")
                skipped_models.append((model_id, "Unknown model"))
                continue

            required_keys = MODEL_REGISTRY[model_id]["requires_api_keys"]
            has_all_keys = all(key in available_keys for key in required_keys)

            if has_all_keys:
                runnable_models.append(model_id)
            else:
                missing = [key for key in required_keys if key not in available_keys]
                logger.warning(f"Skipping model '{model_id}' - missing keys: {missing}")
                skipped_models.append((model_id, f"Missing: {', '.join(missing)}"))

        if skipped_models:
            logger.info(f"\nRunnable models: {len(runnable_models)}/{len(self.config.models)}")
            logger.info(f"Skipped models: {len(skipped_models)}")

        return runnable_models

    def _run_evaluation_with_fallback(self, model_id: str, model_output_dir: Path,
                                       initial_temperature: float) -> tuple[Dict[str, Any], float]:
        """Run evaluation with temperature fallback if needed.

        Args:
            model_id: Model identifier
            model_output_dir: Output directory for results
            initial_temperature: Starting temperature to try

        Returns:
            Tuple of (analysis dict, actual temperature used)
        """
        temperature = initial_temperature

        for attempt in range(2):  # Try up to 2 times
            try:
                config = BenchmarkConfig(
                    model_name=model_id,
                    temperature=temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.timeout,
                    data_dir=self.config.data_dir,
                    db_path=self.config.db_path,
                    sql_samples=self.config.sql_samples,
                    function_samples=self.config.function_samples,
                    difficulty_filter=self.config.difficulty_filter,
                    output_dir=str(model_output_dir),
                    save_results=True,
                    generate_report=True
                )

                benchmark = USABench(config)
                analysis = benchmark.run_and_analyze(
                    evaluation_type="mixed",
                    sql_samples=self.config.sql_samples,
                    function_samples=self.config.function_samples,
                    difficulty_filter=self.config.difficulty_filter,
                    save_results=True,
                    generate_report=True
                )

                # Evaluation completed successfully
                return analysis, temperature

            except Exception as e:
                error_str = str(e).lower()
                # Check if error is related to temperature constraints
                if attempt == 0 and ('temperature' in error_str or 'temp' in error_str or
                                    'unsupportedparams' in error_str):
                    logger.warning(f"⚠️  Temperature {temperature} not supported, retrying with temperature=1.0")
                    temperature = 1.0
                    continue
                else:
                    # Not a temperature error or already retried, re-raise
                    raise

    def run_single_model(self, model_id: str) -> ModelRunResult:
        """Run benchmark for a single model.

        Args:
            model_id: Model identifier from MODEL_REGISTRY

        Returns:
            ModelRunResult with scores and metrics
        """
        model_info = MODEL_REGISTRY[model_id]
        display_name = model_info["display_name"]
        organization = model_info["organization"]

        logger.info("=" * 60)
        logger.info(f"Running benchmark for: {display_name}")
        logger.info("=" * 60)

        start_time = time.time()
        actual_temperature = self.config.temperature

        try:
            # Create per-model output directory
            model_safe = model_id.replace(':', '-').replace('/', '-')
            model_output_dir = self.output_dir / model_safe

            # Run evaluation with temperature fallback
            analysis, actual_temperature = self._run_evaluation_with_fallback(
                model_id, model_output_dir, self.config.temperature
            )

            # Log if temperature was adjusted
            if actual_temperature != self.config.temperature:
                logger.info(f"ℹ️  Used temperature={actual_temperature} for {display_name}")

            execution_time = time.time() - start_time

            # Transform metrics to leaderboard scores
            scores = self._transform_metrics_to_scores(analysis)

            # Create result
            result = ModelRunResult(
                model_id=model_id,
                display_name=display_name,
                organization=organization,
                success=True,
                easy_success=scores["easy_success"],
                medium_success=scores["medium_success"],
                hard_success=scores["hard_success"],
                sql_success=scores["sql_success"],
                function_success=scores["function_success"],
                total_samples=analysis['overall_metrics']['total_samples'],
                execution_time=execution_time,
                temperature=actual_temperature,
                metrics=analysis
            )

            logger.info(f"✓ Successfully completed: {display_name}")
            logger.info(f"  Total Samples: {result.total_samples}")
            logger.info(f"  SQL Success: {result.sql_success:.1f}%" if result.sql_success else "  SQL Success: N/A")
            logger.info(f"  Function Success: {result.function_success:.1f}%" if result.function_success else "  Function Success: N/A")
            logger.info(f"  Execution Time: {execution_time:.1f}s")
            if actual_temperature != self.config.temperature:
                logger.info(f"  Temperature Used: {actual_temperature} (fallback from {self.config.temperature})")
            logger.info("")

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"✗ Failed to run {display_name}: {error_msg}")
            logger.error("")

            return ModelRunResult(
                model_id=model_id,
                display_name=display_name,
                organization=organization,
                success=False,
                error_message=error_msg,
                execution_time=execution_time,
                temperature=actual_temperature
            )

    def _transform_metrics_to_scores(self, analysis: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Transform SDK metrics to leaderboard scores.

        Args:
            analysis: Analysis dict from USABench.run_and_analyze()

        Returns:
            Dict with easy_success, medium_success, hard_success, sql_success, function_success
        """
        scores = {
            "easy_success": None,
            "medium_success": None,
            "hard_success": None,
            "sql_success": None,
            "function_success": None
        }

        # Extract metrics by difficulty
        by_difficulty = analysis.get('metrics_by_difficulty', {})
        if 'easy' in by_difficulty:
            scores["easy_success"] = by_difficulty['easy']['accuracy'] * 100
        if 'medium' in by_difficulty:
            scores["medium_success"] = by_difficulty['medium']['accuracy'] * 100
        if 'hard' in by_difficulty:
            scores["hard_success"] = by_difficulty['hard']['accuracy'] * 100

        # Extract metrics by type
        by_type = analysis.get('metrics_by_type', {})
        if 'sql' in by_type:
            scores["sql_success"] = by_type['sql']['accuracy'] * 100
        if 'function' in by_type:
            scores["function_success"] = by_type['function']['accuracy'] * 100

        return scores

    def run_all_models(self) -> List[ModelRunResult]:
        """Run benchmark for all configured models.

        Returns:
            List of ModelRunResult objects
        """
        logger.info("=" * 60)
        logger.info("USABench Multi-Model Benchmark Runner")
        logger.info("=" * 60)
        logger.info(f"Models to benchmark: {len(self.config.models)}")
        sql_info = "All available" if self.config.sql_samples is None else str(self.config.sql_samples)
        function_info = "All available" if self.config.function_samples is None else str(self.config.function_samples)
        logger.info(f"SQL samples per model: {sql_info}")
        logger.info(f"Function samples per model: {function_info}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info("")

        # Validate API keys
        key_status = self.validate_api_keys()
        available_keys = key_status["available"]

        # Filter models based on available keys
        runnable_models = self.filter_models_by_keys(available_keys)

        if not runnable_models:
            logger.error("No models can be run with available API keys!")
            return []

        logger.info(f"\nStarting benchmark for {len(runnable_models)} models...")
        logger.info("")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Run benchmarks
        for i, model_id in enumerate(runnable_models):
            result = self.run_single_model(model_id)
            self.results.append(result)

            # Delay between runs (except after last model)
            if i < len(runnable_models) - 1:
                logger.info(f"Waiting {self.config.delay_between_runs} seconds before next run...")
                logger.info("")
                time.sleep(self.config.delay_between_runs)

        return self.results

    def generate_leaderboard_json(self) -> List[Dict[str, Any]]:
        """Generate leaderboard JSON for website.

        Returns:
            List of leaderboard entries sorted by average success rate
        """
        leaderboard = []

        # Only include successful runs
        successful_results = [r for r in self.results if r.success]

        # Calculate average success rate for each model (for ranking)
        for result in successful_results:
            scores = [
                result.easy_success,
                result.medium_success,
                result.hard_success,
                result.sql_success,
                result.function_success
            ]
            # Filter out None values
            valid_scores = [s for s in scores if s is not None]
            avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

            entry = {
                "model_id": result.model_id,  # For sorting
                "avg_score": avg_score,  # For sorting
                "model": result.display_name,
                "organization": result.organization,
                "easy_success": result.easy_success,
                "medium_success": result.medium_success,
                "hard_success": result.hard_success,
                "sql_success": result.sql_success,
                "function_success": result.function_success,
                "lastUpdated": datetime.now().strftime("%Y-%m-%d")
            }
            leaderboard.append(entry)

        # Sort by average score (descending)
        leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)

        # Assign ranks and remove temporary fields
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1
            del entry["model_id"]
            del entry["avg_score"]

        return leaderboard

    def generate_summary_report(self) -> str:
        """Generate human-readable summary report.

        Returns:
            Markdown-formatted summary string
        """
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        report = ["# USABench Benchmark Summary\n"]
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Configuration:**\n")
        report.append(f"- SQL Samples: {self.config.sql_samples}\n")
        report.append(f"- Function Samples: {self.config.function_samples}\n")
        report.append(f"- Total Models Attempted: {len(self.results)}\n")
        report.append(f"- Successful: {len(successful)}\n")
        report.append(f"- Failed: {len(failed)}\n")
        report.append("\n")

        if successful:
            report.append("## Successful Runs\n\n")
            for result in successful:
                report.append(f"### {result.display_name} ({result.organization})\n")
                report.append(f"- **Total Samples:** {result.total_samples}\n")
                report.append(f"- **Execution Time:** {result.execution_time:.1f}s\n")
                report.append(f"- **Temperature:** {result.temperature}\n")
                report.append("\n**Success Rates:**\n")
                if result.sql_success is not None:
                    report.append(f"- SQL: {result.sql_success:.1f}%\n")
                if result.function_success is not None:
                    report.append(f"- Function: {result.function_success:.1f}%\n")
                if result.easy_success is not None:
                    report.append(f"- Easy: {result.easy_success:.1f}%\n")
                if result.medium_success is not None:
                    report.append(f"- Medium: {result.medium_success:.1f}%\n")
                if result.hard_success is not None:
                    report.append(f"- Hard: {result.hard_success:.1f}%\n")
                report.append("\n")

        if failed:
            report.append("## Failed Runs\n\n")
            for result in failed:
                report.append(f"### {result.display_name} ({result.organization})\n")
                report.append(f"- **Error:** {result.error_message}\n")
                report.append("\n")

        report.append("## Output Files\n\n")
        report.append(f"- **Leaderboard:** `{self.output_dir}/leaderboard.json`\n")
        report.append(f"- **Summary:** `{self.output_dir}/benchmark_summary.json`\n")
        report.append(f"- **Per-model results:** `{self.output_dir}/{{model-name}}/`\n")

        return "".join(report)

    def save_results(self):
        """Save all results to disk."""
        logger.info("=" * 60)
        logger.info("Saving Results")
        logger.info("=" * 60)

        # Generate leaderboard
        leaderboard = self.generate_leaderboard_json()

        # Save leaderboard.json
        leaderboard_path = self.output_dir / "leaderboard.json"
        with open(leaderboard_path, 'w') as f:
            json.dump(leaderboard, f, indent=2)
        logger.info(f"✓ Leaderboard: {leaderboard_path}")

        # Save benchmark_summary.json
        summary_data = {
            "generated_at": datetime.now().isoformat(),
            "configuration": {
                "models": self.config.models,
                "sql_samples": self.config.sql_samples,
                "function_samples": self.config.function_samples,
                "temperature": self.config.temperature
            },
            "results": [
                {
                    "model_id": r.model_id,
                    "display_name": r.display_name,
                    "organization": r.organization,
                    "success": r.success,
                    "easy_success": r.easy_success,
                    "medium_success": r.medium_success,
                    "hard_success": r.hard_success,
                    "sql_success": r.sql_success,
                    "function_success": r.function_success,
                    "total_samples": r.total_samples,
                    "execution_time": r.execution_time,
                    "temperature": r.temperature,
                    "error_message": r.error_message
                }
                for r in self.results
            ],
            "summary": {
                "total_models": len(self.results),
                "successful": len([r for r in self.results if r.success]),
                "failed": len([r for r in self.results if not r.success])
            }
        }

        summary_path = self.output_dir / "benchmark_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary_data, f, indent=2)
        logger.info(f"✓ Summary: {summary_path}")

        # Save SUMMARY.md
        summary_md = self.generate_summary_report()
        summary_md_path = self.output_dir / "SUMMARY.md"
        with open(summary_md_path, 'w') as f:
            f.write(summary_md)
        logger.info(f"✓ Report: {summary_md_path}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("Benchmark Complete!")
        logger.info("=" * 60)
        logger.info(f"Results directory: {self.output_dir}")
        logger.info(f"Leaderboard JSON: {leaderboard_path}")
        logger.info("")


def get_default_models() -> List[str]:
    """Get default model list from environment or registry.

    Returns:
        List of model IDs to benchmark
    """
    env_models = os.getenv('BENCHMARK_MODELS')
    if env_models:
        return [m.strip() for m in env_models.split(',')]

    # Return all registered models
    return list(MODEL_REGISTRY.keys())
