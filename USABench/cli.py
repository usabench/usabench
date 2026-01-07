#!/usr/bin/env python3
"""
USABench Command Line Interface

A professional CLI for running government economic data analysis benchmarks.
"""

import argparse
from pathlib import Path
import sys
from typing import List, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

# Add USABench to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from USABench.core.base import Difficulty
from USABench.sdk import BenchmarkConfig, USABench


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for USABench CLI."""
    parser = argparse.ArgumentParser(
        prog='usabench',
        description='USABench: Government Economic Data Analysis Benchmark',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick mixed evaluation with 10 samples each
  usabench --model gpt-4o --sql-samples 10 --function-samples 10

  # SQL-only evaluation with 50 samples
  usabench --evaluation-type sql --sql-samples 50 --model claude-3-5-sonnet-20241022

  # Full evaluation with all available samples
  usabench --evaluation-type full --model gpt-4o --save-results

  # Evaluation with difficulty filtering
  usabench --model gpt-4o --difficulty easy medium --sql-samples 20

  # Custom output directory and report generation
  usabench --model gpt-4o --output-dir ./my_results --generate-report
        """
    )

    # Model configuration
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='gpt-4o',
        help='Model to evaluate (default: gpt-4o)'
    )

    parser.add_argument(
        '--temperature',
        type=float,
        default=0.0,
        help='Model temperature (default: 0.0)'
    )

    parser.add_argument(
        '--max-tokens',
        type=int,
        default=2000,
        help='Maximum tokens per response (default: 2000)'
    )

    # Evaluation configuration
    parser.add_argument(
        '--evaluation-type', '-t',
        type=str,
        choices=['sql', 'function', 'mixed', 'full'],
        default='mixed',
        help='Type of evaluation to run (default: mixed)'
    )

    parser.add_argument(
        '--sql-samples',
        type=int,
        help='Number of SQL samples to evaluate'
    )

    parser.add_argument(
        '--function-samples',
        type=int,
        help='Number of function calling samples to evaluate'
    )

    parser.add_argument(
        '--difficulty',
        type=str,
        nargs='+',
        choices=['easy', 'medium', 'hard'],
        help='Filter by difficulty levels (can specify multiple)'
    )

    # Data configuration
    parser.add_argument(
        '--data-dir',
        type=str,
        default=str(Path(__file__).parent / 'data'),
        help='Path to data directory (default: USABench/data)'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default=str(Path(__file__).parent / 'data' / 'usafacts.db'),
        help='Path to database file (default: USABench/data/usafacts.db)'
    )

    # Output configuration
    parser.add_argument(
        '--output-dir',
        type=str,
        default='results',
        help='Output directory for results (default: results)'
    )

    parser.add_argument(
        '--save-results',
        action='store_true',
        help='Save detailed results to files'
    )

    parser.add_argument(
        '--generate-report',
        action='store_true',
        help='Generate evaluation report'
    )

    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save any results (overrides --save-results)'
    )

    # Utility options
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List supported models and exit'
    )

    parser.add_argument(
        '--dataset-info',
        action='store_true',
        help='Show dataset information and exit'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='USABench 1.0.0'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    # Benchmark mode options
    benchmark_group = parser.add_argument_group('Benchmark Mode')
    benchmark_group.add_argument(
        '--benchmark',
        action='store_true',
        help='Run multi-model benchmark mode'
    )
    benchmark_group.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode with 5 samples each (default: all available samples)'
    )
    benchmark_group.add_argument(
        '--benchmark-models',
        type=str,
        nargs='+',
        help='Models to benchmark (default: all models in registry or BENCHMARK_MODELS env var)'
    )

    return parser


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    import logging

    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def list_supported_models():
    """List supported models."""
    models = [
        "OpenAI Models:",
        "  - gpt-5-chat",
        "  - gpt-5-mini",
        "  - gpt-4o (Recommended)",
        "  - gpt-4o-mini",
        "",
        "Anthropic Models:",
        "  - claude-3-5-sonnet-20240620",
        "  - claude-3-haiku-20240307",
        "  - claude-sonnet-4-5-20250929",
        "  - claude-opus-4-5-20251101",
        "",
        "Google Models:",
        "  - gemini/gemini-2.0-flash (requires GEMINI_API_KEY)",
        "  - gemini/gemini-flash-latest (requires GEMINI_API_KEY)",
        "",
        "Groq Models:",
        "  - groq/llama-3.3-70b-versatile (requires GROQ_API_KEY)",
        "",
        "xAI Models:",
        "  - xai/grok-4-1-fast-non-reasoning (requires XAI_API_KEY)",
        "",
        "Other Models:",
        "  - Any model supported by LiteLLM",
        "  - See: https://docs.litellm.ai/docs/providers"
    ]

    print("\nSupported Models:")
    print("=" * 50)
    for model in models:
        print(model)


def show_dataset_info(data_dir: str):
    """Show dataset information."""
    from .core.loader import DataLoader

    try:
        loader = DataLoader(data_dir)
        info = loader.get_dataset_info()

        print("\nDataset Information:")
        print("=" * 50)

        if 'sql' in info:
            print("SQL Evaluation:")
            print(f"  - Questions: {info['sql']['total_questions']}")
            print(f"  - File: {info['sql']['file']}")

        if 'function' in info:
            print("\nFunction Calling Evaluation:")
            print(f"  - Questions: {info['function']['total_questions']}")
            print(f"  - File: {info['function']['file']}")

        total = info.get('sql', {}).get('total_questions', 0) + \
                info.get('function', {}).get('total_questions', 0)
        print(f"\nTotal Questions: {total}")

    except Exception as e:
        print(f"Error loading dataset info: {e}")
        return False

    return True


def validate_arguments(args) -> bool:
    """Validate command line arguments."""
    errors = []

    # Check data directory exists
    if not Path(args.data_dir).exists():
        errors.append(f"Data directory not found: {args.data_dir}")

    # Check database file exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        # Try relative to data directory
        alt_db_path = Path(args.data_dir) / "usafacts.db"
        if alt_db_path.exists():
            args.db_path = str(alt_db_path)
        else:
            errors.append(f"Database file not found: {args.db_path}")

    # Validate sample counts
    if args.sql_samples is not None and args.sql_samples < 1:
        errors.append("SQL samples must be positive")

    if args.function_samples is not None and args.function_samples < 1:
        errors.append("Function samples must be positive")

    # Validate temperature
    if not (0.0 <= args.temperature <= 2.0):
        errors.append("Temperature must be between 0.0 and 2.0")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return False

    return True


def parse_difficulty_filter(difficulty_list: Optional[List[str]]) -> Optional[List[Difficulty]]:
    """Parse difficulty filter from command line."""
    if not difficulty_list:
        return None

    difficulty_map = {
        'easy': Difficulty.EASY,
        'medium': Difficulty.MEDIUM,
        'hard': Difficulty.HARD
    }

    return [difficulty_map[d.lower()] for d in difficulty_list]


def print_results_summary(analysis: dict, verbose: bool = False):
    """Print a summary of evaluation results."""
    overall = analysis['overall_metrics']
    by_type = analysis['metrics_by_type']
    by_difficulty = analysis['metrics_by_difficulty']

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 60)

    # Overall metrics
    print("\n📊 Overall Performance:")
    print(f"   Total Samples: {overall['total_samples']}")
    print(f"   Accuracy: {overall['accuracy']:.1%}")
    print(f"   Average Score: {overall['average_score']:.3f}")
    print(f"   Avg Execution Time: {overall['average_execution_time']:.2f}s")
    print(f"   Error Rate: {overall['error_rate']:.1%}")

    # By evaluation type
    if by_type:
        print("\n📋 Performance by Type:")
        for eval_type, metrics in by_type.items():
            print(f"   {eval_type.upper()}:")
            print(f"     - Samples: {metrics['total_samples']}")
            print(f"     - Accuracy: {metrics['accuracy']:.1%}")
            print(f"     - Avg Score: {metrics['average_score']:.3f}")

    # By difficulty
    if by_difficulty and verbose:
        print("\n🎯 Performance by Difficulty:")
        for difficulty, metrics in by_difficulty.items():
            print(f"   {difficulty.upper()}:")
            print(f"     - Samples: {metrics['total_samples']}")
            print(f"     - Accuracy: {metrics['accuracy']:.1%}")
            print(f"     - Avg Score: {metrics['average_score']:.3f}")

    # Error analysis
    error_analysis = analysis.get('error_analysis', {})
    if error_analysis.get('total_errors', 0) > 0:
        print(f"\n⚠️  Errors: {error_analysis['total_errors']} total")


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Handle utility commands
    if args.list_models:
        list_supported_models()
        return 0

    if args.dataset_info:
        success = show_dataset_info(args.data_dir)
        return 0 if success else 1

    # Handle benchmark mode
    if args.benchmark:
        from USABench.sdk.benchmark import BenchmarkRunner, BenchmarkRunnerConfig, get_default_models

        # Determine sample counts
        if args.test_mode:
            sql_samples = 5
            function_samples = 5
        else:
            # In full mode, use all samples (None means no limit)
            sql_samples = args.sql_samples  # None if not specified
            function_samples = args.function_samples  # None if not specified

        # Get models to benchmark
        if args.benchmark_models:
            models = args.benchmark_models
        else:
            models = get_default_models()

        # Parse difficulty filter if specified
        difficulty_filter = parse_difficulty_filter(args.difficulty)

        # Create benchmark config
        config = BenchmarkRunnerConfig(
            models=models,
            sql_samples=sql_samples,
            function_samples=function_samples,
            output_dir=args.output_dir,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            difficulty_filter=difficulty_filter,
            data_dir=args.data_dir,
            db_path=args.db_path
        )

        # Run benchmark
        runner = BenchmarkRunner(config)
        runner.run_all_models()
        runner.save_results()

        return 0

    # Validate arguments
    if not validate_arguments(args):
        return 1

    # Parse difficulty filter
    difficulty_filter = parse_difficulty_filter(args.difficulty)

    # Create configuration
    config = BenchmarkConfig(
        model_name=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        data_dir=args.data_dir,
        db_path=args.db_path,
        sql_samples=args.sql_samples,
        function_samples=args.function_samples,
        difficulty_filter=difficulty_filter,
        output_dir=args.output_dir,
        save_results=args.save_results and not args.no_save,
        generate_report=args.generate_report and not args.no_save
    )

    try:
        # Initialize benchmark
        print("🚀 Initializing USABench...")
        print(f"   Model: {args.model}")
        print(f"   Evaluation Type: {args.evaluation_type}")
        if difficulty_filter:
            diff_names = [d.value for d in difficulty_filter]
            print(f"   Difficulty Filter: {', '.join(diff_names)}")

        benchmark = USABench(config)

        # Show dataset info
        info = benchmark.get_dataset_info()
        total_sql = info.get('sql', {}).get('total_questions', 0)
        total_func = info.get('function', {}).get('total_questions', 0)
        print(f"   Available: {total_sql} SQL, {total_func} Function questions")

        # Run evaluation
        print(f"\n⏳ Running {args.evaluation_type} evaluation...")

        analysis = benchmark.run_and_analyze(
            evaluation_type=args.evaluation_type,
            sql_samples=args.sql_samples,
            function_samples=args.function_samples,
            difficulty_filter=difficulty_filter,
            save_results=config.save_results,
            generate_report=config.generate_report
        )

        # Print results
        print_results_summary(analysis, args.verbose)

        # Show saved files
        if 'saved_files' in analysis:
            files = analysis['saved_files']
            print("\n💾 Results saved:")
            for file_type, file_path in files.items():
                print(f"   {file_type}: {file_path}")

        print("\n✅ Evaluation completed successfully!")
        return 0

    except KeyboardInterrupt:
        print("\n❌ Evaluation interrupted by user")
        return 130

    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
