#!/usr/bin/env python3
"""Run USABench evaluation with baseline and improved prompts."""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now import USABench
from USABench.sdk.api import USABench
from USABench.sdk.config import BenchmarkConfig

def run_baseline_evaluation():
    """Run baseline evaluation before prompt improvements."""
    print("=" * 60)
    print("Running BASELINE evaluation (before prompt improvements)")
    print("=" * 60)
    
    config = BenchmarkConfig(
        model_name="gpt-4o-mini",
        evaluation_type="mixed",
        sql_samples=10,
        function_samples=10,
        save_results=True,
        output_file="baseline_results.json"
    )
    
    benchmark = USABench(config)
    results = benchmark.run()
    
    # Print summary
    print(f"\nBaseline Results:")
    print(f"Total Samples: {results['total_samples']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['success_rate']:.2%}")
    print(f"Average Score: {results['average_score']:.3f}")
    
    return results

def run_improved_evaluation():
    """Run evaluation after prompt improvements."""
    print("\n" + "=" * 60)
    print("Running IMPROVED evaluation (after prompt improvements)")
    print("=" * 60)
    
    config = BenchmarkConfig(
        model_name="gpt-4o-mini",
        evaluation_type="mixed",
        sql_samples=10,
        function_samples=10,
        save_results=True,
        output_file="improved_results.json"
    )
    
    benchmark = USABench(config)
    results = benchmark.run()
    
    # Print summary
    print(f"\nImproved Results:")
    print(f"Total Samples: {results['total_samples']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['success_rate']:.2%}")
    print(f"Average Score: {results['average_score']:.3f}")
    
    return results

def compare_results(baseline, improved):
    """Compare baseline and improved results."""
    print("\n" + "=" * 60)
    print("COMPARISON: Baseline vs Improved")
    print("=" * 60)
    
    print(f"\nSuccess Rate:")
    print(f"  Baseline: {baseline['success_rate']:.2%}")
    print(f"  Improved: {improved['success_rate']:.2%}")
    print(f"  Change: {(improved['success_rate'] - baseline['success_rate']):.2%}")
    
    print(f"\nAverage Score:")
    print(f"  Baseline: {baseline['average_score']:.3f}")
    print(f"  Improved: {improved['average_score']:.3f}")
    print(f"  Change: {(improved['average_score'] - baseline['average_score']):.3f}")
    
    print(f"\nPassed Samples:")
    print(f"  Baseline: {baseline['passed']}/{baseline['total_samples']}")
    print(f"  Improved: {improved['passed']}/{improved['total_samples']}")
    print(f"  Improvement: {improved['passed'] - baseline['passed']} more passed")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run USABench evaluation")
    parser.add_argument("--baseline-only", action="store_true", help="Run only baseline evaluation")
    parser.add_argument("--improved-only", action="store_true", help="Run only improved evaluation")
    parser.add_argument("--compare", action="store_true", help="Compare existing results")
    
    args = parser.parse_args()
    
    if args.compare:
        # Load and compare existing results
        with open("baseline_results.json", "r") as f:
            baseline = json.load(f)
        with open("improved_results.json", "r") as f:
            improved = json.load(f)
        compare_results(baseline, improved)
    elif args.improved_only:
        run_improved_evaluation()
    else:
        # Default: run baseline first
        baseline = run_baseline_evaluation()
        
        if not args.baseline_only:
            input("\nPress Enter to apply prompt improvements and run again...")
            # After applying improvements
            improved = run_improved_evaluation()
            compare_results(baseline, improved)