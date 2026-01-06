#!/bin/bash

##############################################################################
# USABench Baseline Benchmark Script
#
# Runs benchmark evaluations across multiple models and generates reports.
#
# Usage:
#   ./run_baseline.sh           # Run full benchmark (10 samples each)
#   ./run_baseline.sh --test    # Run test benchmark (5 samples each)
#
# Output:
#   - Results saved to results/baseline-{model}-{timestamp}/
#   - Reports generated in JSON, CSV, and Markdown formats
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
TEST_MODE=false
if [ "$1" == "--test" ]; then
    TEST_MODE=true
fi

# Configuration
if [ "$TEST_MODE" = true ]; then
    SQL_SAMPLES=5
    FUNCTION_SAMPLES=5
    echo -e "${YELLOW}===========================================================${NC}"
    echo -e "${YELLOW}Running BASELINE BENCHMARK - TEST MODE${NC}"
    echo -e "${YELLOW}===========================================================${NC}"
else
    SQL_SAMPLES=10
    FUNCTION_SAMPLES=10
    echo -e "${BLUE}===========================================================${NC}"
    echo -e "${BLUE}Running BASELINE BENCHMARK - FULL MODE${NC}"
    echo -e "${BLUE}===========================================================${NC}"
fi

echo "Configuration:"
echo "  SQL Samples: $SQL_SAMPLES"
echo "  Function Samples: $FUNCTION_SAMPLES"
echo ""

# Define models to benchmark
# You can customize this list or make it configurable via environment variable
if [ -z "$BENCHMARK_MODELS" ]; then
    MODELS=(
        "gpt-4o"
        "gpt-4o-mini"
        "claude-3-5-sonnet-20241022"
    )
else
    # Allow override via environment variable
    # Usage: BENCHMARK_MODELS="model1,model2,model3" ./run_baseline.sh
    IFS=',' read -ra MODELS <<< "$BENCHMARK_MODELS"
fi

echo "Models to benchmark:"
for model in "${MODELS[@]}"; do
    echo "  - $model"
done
echo ""

# Check for required API keys
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY environment variable is not set${NC}"
    echo "Please set it with: export OPENAI_API_KEY='your-api-key-here'"
    exit 1
fi

# Warning for optional API keys
if [ -z "$BLS_API_KEY" ] || [ -z "$BEA_API_KEY" ]; then
    echo -e "${YELLOW}Warning: BLS_API_KEY and/or BEA_API_KEY not set${NC}"
    echo -e "${YELLOW}Function calling evaluation may have limited functionality${NC}"
    echo ""
fi

# Create timestamp for this benchmark run
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BASELINE_DIR="results/baseline-${TIMESTAMP}"
mkdir -p "$BASELINE_DIR"

echo -e "${GREEN}Results will be saved to: $BASELINE_DIR${NC}"
echo ""

# Track results
SUCCESSFUL_RUNS=0
FAILED_RUNS=0
declare -a FAILED_MODELS

# Function to run benchmark for a single model
run_benchmark() {
    local model=$1
    local model_safe=$(echo "$model" | tr ':/' '-')
    local output_dir="${BASELINE_DIR}/${model_safe}"

    echo -e "${BLUE}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│ Running benchmark for: ${model}${NC}"
    echo -e "${BLUE}└─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Run the benchmark
    if python3 -m USABench \
        --model "$model" \
        --evaluation-type mixed \
        --sql-samples "$SQL_SAMPLES" \
        --function-samples "$FUNCTION_SAMPLES" \
        --output-dir "$output_dir" \
        --save-results \
        --generate-report \
        --verbose; then

        echo -e "${GREEN}✓ Successfully completed benchmark for $model${NC}"
        echo -e "${GREEN}  Results: $output_dir${NC}"
        echo ""
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
        return 0
    else
        echo -e "${RED}✗ Failed to complete benchmark for $model${NC}"
        echo ""
        FAILED_RUNS=$((FAILED_RUNS + 1))
        FAILED_MODELS+=("$model")
        return 1
    fi
}

# Run benchmarks for all models
echo -e "${BLUE}Starting benchmark runs...${NC}"
echo ""

for model in "${MODELS[@]}"; do
    run_benchmark "$model"

    # Add a small delay between runs to avoid rate limiting
    if [ $model != "${MODELS[-1]}" ]; then
        echo "Waiting 5 seconds before next run..."
        echo ""
        sleep 5
    fi
done

# Print summary
echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}BASELINE BENCHMARK SUMMARY${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""
echo "Total Models: ${#MODELS[@]}"
echo -e "${GREEN}Successful Runs: $SUCCESSFUL_RUNS${NC}"
if [ $FAILED_RUNS -gt 0 ]; then
    echo -e "${RED}Failed Runs: $FAILED_RUNS${NC}"
    echo ""
    echo "Failed models:"
    for failed_model in "${FAILED_MODELS[@]}"; do
        echo -e "  ${RED}- $failed_model${NC}"
    done
else
    echo -e "${GREEN}Failed Runs: 0${NC}"
fi
echo ""
echo "Results directory: $BASELINE_DIR"
echo ""

# Create a summary index file
SUMMARY_FILE="$BASELINE_DIR/SUMMARY.md"
cat > "$SUMMARY_FILE" << EOF
# Baseline Benchmark Summary

**Date:** $(date +"%Y-%m-%d %H:%M:%S")
**Mode:** $([ "$TEST_MODE" = true ] && echo "TEST MODE" || echo "FULL MODE")
**Samples:** SQL=$SQL_SAMPLES, Function=$FUNCTION_SAMPLES

## Models Evaluated

Total: ${#MODELS[@]} | Successful: $SUCCESSFUL_RUNS | Failed: $FAILED_RUNS

EOF

for model in "${MODELS[@]}"; do
    model_safe=$(echo "$model" | tr ':/' '-')
    if [[ " ${FAILED_MODELS[@]} " =~ " ${model} " ]]; then
        echo "- ❌ **$model** - Failed" >> "$SUMMARY_FILE"
    else
        echo "- ✅ **$model** - [Results](./${model_safe}/)" >> "$SUMMARY_FILE"
    fi
done

cat >> "$SUMMARY_FILE" << EOF

## Results Structure

Each model's results are in a separate directory:
- \`evaluation_results.json\` - Complete evaluation data
- \`evaluation_summary.csv\` - Summary statistics
- \`evaluation_report.md\` - Detailed report

## Commands to View Results

\`\`\`bash
# View summary report for a model
cat $BASELINE_DIR/{model-name}/evaluation_report.md

# Compare results across models
for dir in $BASELINE_DIR/*/; do
    echo "=== \$(basename \$dir) ==="
    grep "Overall Accuracy" "\$dir/evaluation_report.md" 2>/dev/null || echo "No report found"
done
\`\`\`
EOF

echo -e "${GREEN}Summary saved to: $SUMMARY_FILE${NC}"
echo ""

if [ $FAILED_RUNS -eq 0 ]; then
    echo -e "${GREEN}✓ All benchmarks completed successfully!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some benchmarks failed. Check the summary above for details.${NC}"
    exit 1
fi
