#!/bin/bash

echo "============================================================"
echo "Running BASELINE evaluation (before prompt improvements)"
echo "============================================================"

cd USABench

# Set your OpenAI API key before running this script:
# export OPENAI_API_KEY="your-api-key-here"
# or create a .env file with OPENAI_API_KEY=your-api-key-here

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set"
    echo "Please set it with: export OPENAI_API_KEY='your-api-key-here'"
    echo "Or create a .env file in the project root"
    exit 1
fi

# Run evaluation using Python module syntax
python3 -c "
import sys
sys.path.insert(0, '.')

from sdk.api import USABench
from sdk.config import BenchmarkConfig

config = BenchmarkConfig(
    model_name='gpt-4o-mini',
    sql_samples=10,
    function_samples=10,
    save_results=True
)

benchmark = USABench(config)
results = benchmark.run()

print(f'\\nBaseline Results:')
print(f'Total Samples: {results[\"total_samples\"]}')
print(f'Passed: {results[\"passed\"]}')
print(f'Failed: {results[\"failed\"]}')
print(f'Success Rate: {results[\"success_rate\"]:.2%}')
print(f'Average Score: {results[\"average_score\"]:.3f}')

# Save results
import json
with open('baseline_results.json', 'w') as f:
    json.dump(results, f, indent=2)
"

echo "Baseline results saved to baseline_results.json"