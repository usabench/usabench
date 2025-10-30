#!/usr/bin/env python3
"""
Simple wrapper to run USABench evaluation with the improved prompts.
This avoids the import issues in the CLI.
"""

import sys
import os
import json
from pathlib import Path

# Set up the path
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)  # Ensure we're in USABench directory

def run_evaluation():
    """Run a simple evaluation to test the prompt improvements."""
    
    # Import here after path is set
    from core.base import EvaluationConfig, UnifiedSample, EvaluationType
    from core.loader import DataLoader
    from evaluators.production_sql import ProductionSQLEvaluator
    from evaluators.function import FunctionEvaluator
    
    print("=" * 60)
    print("Running USABench Evaluation with Improved Prompts")
    print("=" * 60)
    
    # Configuration
    config = EvaluationConfig(
        model_name="gpt-4o-mini",
        temperature=0.0,
        max_tokens=2000,
        timeout=30
    )
    
    # Load samples
    loader = DataLoader(data_dir="data")
    
    print("\n📊 Loading samples...")
    sql_samples = loader.load_sql_samples(max_samples=5)
    function_samples = loader.load_function_samples(max_samples=5)
    
    print(f"  - Loaded {len(sql_samples)} SQL samples")
    print(f"  - Loaded {len(function_samples)} function samples")
    
    # Initialize evaluators with improved prompts
    sql_evaluator = ProductionSQLEvaluator(config)
    function_evaluator = FunctionEvaluator(config)
    
    results = {
        "sql_results": [],
        "function_results": [],
        "summary": {}
    }
    
    # Run SQL evaluation
    print("\n🔍 Running SQL Evaluation...")
    sql_passed = 0
    for i, sample in enumerate(sql_samples, 1):
        print(f"  Sample {i}/{len(sql_samples)}: {sample.question[:50]}...")
        try:
            result = sql_evaluator.evaluate(sample)
            results["sql_results"].append({
                "question": sample.question,
                "passed": result.is_correct,
                "score": result.score
            })
            if result.is_correct:
                sql_passed += 1
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results["sql_results"].append({
                "question": sample.question,
                "passed": False,
                "score": 0.0,
                "error": str(e)
            })
    
    # Run Function evaluation
    print("\n🔧 Running Function Evaluation...")
    func_passed = 0
    for i, sample in enumerate(function_samples, 1):
        print(f"  Sample {i}/{len(function_samples)}: {sample.question[:50]}...")
        try:
            result = function_evaluator.evaluate(sample)
            results["function_results"].append({
                "question": sample.question,
                "passed": result.is_correct,
                "score": result.score
            })
            if result.is_correct:
                func_passed += 1
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results["function_results"].append({
                "question": sample.question,
                "passed": False,
                "score": 0.0,
                "error": str(e)
            })
    
    # Calculate summary
    total_samples = len(sql_samples) + len(function_samples)
    total_passed = sql_passed + func_passed
    
    results["summary"] = {
        "total_samples": total_samples,
        "passed": total_passed,
        "failed": total_samples - total_passed,
        "success_rate": total_passed / total_samples if total_samples > 0 else 0,
        "sql_success_rate": sql_passed / len(sql_samples) if sql_samples else 0,
        "function_success_rate": func_passed / len(function_samples) if function_samples else 0
    }
    
    # Print summary
    print("\n" + "=" * 60)
    print("📈 EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total Samples: {total_samples}")
    print(f"Passed: {total_passed} ({results['summary']['success_rate']:.1%})")
    print(f"Failed: {total_samples - total_passed}")
    print(f"\nSQL Success Rate: {results['summary']['sql_success_rate']:.1%}")
    print(f"Function Success Rate: {results['summary']['function_success_rate']:.1%}")
    
    # Save results
    output_file = "evaluation_results_with_prompts.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {output_file}")
    
    # Test year constraint handling
    print("\n" + "=" * 60)
    print("🧪 TESTING YEAR CONSTRAINT HANDLING")
    print("=" * 60)
    
    test_sample = UnifiedSample(
        id="test_2025",
        question="What will the GDP be in 2025?",
        evaluation_type=EvaluationType.SQL,
        context="Testing year constraint"
    )
    
    print(f"Test Question: {test_sample.question}")
    print("Expected: Model should explain data limitation\n")
    
    try:
        result = sql_evaluator.evaluate(test_sample)
        print(f"Model Response: {result.model_response[:200]}...")
        if "2024" in str(result.model_response) or "not available" in str(result.model_response).lower():
            print("✅ Year constraint properly handled!")
        else:
            print("⚠️ Model may not be handling year constraint properly")
    except Exception as e:
        print(f"Error during test: {e}")
    
    return results

if __name__ == "__main__":
    # Set API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ Setting OPENAI_API_KEY from script...")
        os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
    
    run_evaluation()