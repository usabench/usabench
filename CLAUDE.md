# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

USABench is a comprehensive benchmark framework for evaluating language models on government economic data analysis tasks, featuring Text2SQL and Function Calling evaluations with real API integration. The codebase implements a clean architecture with modular evaluators, SDK interface, and CLI.

## Development Commands

### Environment Setup
```bash
# Option 1: Using .env file (recommended)
# Create a .env file in the project root with your API keys
cat > .env << EOF
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
BLS_API_KEY=your-bls-key
BEA_API_KEY=your-bea-key
EOF

# Option 2: Export environment variables
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"  # Optional
export GEMINI_API_KEY="your-gemini-key"        # Optional
export GROQ_API_KEY="your-groq-key"            # Optional
export BLS_API_KEY="your-bls-key"              # Optional for function calling
export BEA_API_KEY="your-bea-key"              # Optional for function calling

# Install Python dependencies (preferred method)
pip install -e .

# Alternative: Install dependencies directly
pip install litellm sqlparse pydantic numpy pandas python-dotenv

# Install Node.js dependencies (for landing page development)
npm install
```

**Note**: The .env file is automatically loaded by python-dotenv when running evaluations or benchmarks. This is the preferred method for local development.

### Running Evaluations

The main interface is the CLI module accessible via `python3 -m USABench`:

#### Single Model Evaluation
```bash
# Quick mixed evaluation
python3 -m USABench --model gpt-4o --sql-samples 10 --function-samples 5

# Text2SQL only evaluation
python3 -m USABench --evaluation-type sql --model gpt-4o --sql-samples 50

# Function calling evaluation
python3 -m USABench --evaluation-type function --model gpt-4o --function-samples 10

# Full evaluation with reports
python3 -m USABench --evaluation-type full --model gpt-4o --save-results --generate-report
```

#### Multi-Model Benchmark Runner
```bash
# Quick test with 5 samples per model (recommended for validation)
python3 -m USABench --benchmark --test-mode

# Full benchmark with all 459 samples per model
python3 -m USABench --benchmark

# Custom model selection
python3 -m USABench --benchmark --test-mode --benchmark-models gpt-4o claude-3-5-sonnet-20241022

# Environment variable override
BENCHMARK_MODELS="gpt-4o,gpt-4o-mini" python3 -m USABench --benchmark --test-mode

# Verbose output for detailed progress
python3 -m USABench --benchmark --test-mode --verbose

# Legacy shell script (still available)
./run_baseline.sh --test  # Test mode (5 samples)
./run_baseline.sh         # Full mode (all samples)
```

### Development Scripts
```bash
# Website development server
npm run dev

# Website linting
npm run lint

# Run tests (validation through running evaluations)
python3 -m USABench --model gpt-4o --sql-samples 5 --function-samples 5
```

## Architecture

### Main Components

```
USABench/
├── core/                     # Core framework components
│   ├── base.py              # Base classes and data models
│   ├── loader.py            # Data loading and management
│   ├── production_client.py # LiteLLM integration with auto param handling
│   └── client.py            # Legacy LLM client
├── evaluators/              # Evaluation implementations
│   ├── production_sql.py    # Production Text2SQL evaluator
│   ├── berkeley_function.py # Function calling evaluator
│   ├── sql.py              # Basic SQL evaluator
│   └── function.py         # Basic function evaluator
├── sdk/                     # High-level SDK interface
│   ├── api.py              # Main USABench class
│   ├── config.py           # Configuration management
│   ├── results.py          # Results analysis
│   └── benchmark.py        # Multi-model benchmark runner
├── metrics/                 # Evaluation metrics
├── data/                    # Dataset and database
│   ├── usafacts.db         # SQLite database (459 samples total)
│   ├── text2sql_ground_truth.json           # 293 SQL questions
│   └── enhanced_function_calling_ground_truth.json # 166 function questions
├── cli.py                   # Command-line interface with benchmark mode
├── run_baseline.sh          # Shell script for multi-model benchmarks
└── __main__.py             # Module entry point
```

### Key Design Patterns

- **Modular Evaluators**: Separate evaluators for SQL and function calling with pluggable architecture
- **Production Client**: Direct LiteLLM integration with automatic parameter dropping for model-specific constraints
- **SDK Interface**: High-level `USABench` class for programmatic access
- **CLI Integration**: Full-featured command-line interface via `python3 -m USABench`
- **Multi-Model Orchestration**: BenchmarkRunner class for iterative evaluation across multiple models
- **Model Registry Pattern**: Centralized MODEL_REGISTRY with metadata, API key requirements, and display names
- **Graceful Degradation**: API key validation with early warnings, continues with available models
- **Real API Integration**: Function calling evaluation uses actual BLS/BEA government APIs
- **Environment-based Configuration**: Automatic .env file loading via python-dotenv for local development

### Data Flow

**Single Model Evaluation:**
1. CLI/SDK → Configuration → Data Loader → Evaluator
2. Evaluator → LLM Client → Model Response → Metrics
3. Results → Analysis → Reports (JSON/CSV/Markdown)

**Multi-Model Benchmark:**
1. CLI → BenchmarkRunner → API Key Validation → Model Filtering
2. For each model: BenchmarkRunner → USABench → Evaluators → Results
3. Results → Score Transformation → Leaderboard JSON + Summary Reports

### Multi-Model Benchmark Runner

The benchmark runner (`sdk/benchmark.py`) orchestrates evaluations across multiple models:

**Key Components:**
- **MODEL_REGISTRY**: Centralized registry with model metadata, organizations, and API key requirements
  ```python
  MODEL_REGISTRY = {
      "gpt-4o": {
          "display_name": "GPT-4o",
          "organization": "OpenAI",
          "requires_api_keys": ["OPENAI_API_KEY"]
      },
      "gemini/gemini-2.0-flash": {
          "display_name": "Gemini 2.0 Flash",
          "organization": "Google",
          "requires_api_keys": ["GEMINI_API_KEY"]
      },
      # ... more models
  }
  ```

- **BenchmarkRunner**: Main orchestrator class
  - `validate_api_keys()`: Check available API keys, warn about missing ones
  - `filter_models_by_keys()`: Skip models with missing API keys, continue with available ones
  - `run_single_model()`: Run evaluation for one model with error handling
  - `run_all_models()`: Iterate through models, gracefully handle per-model failures
  - `generate_leaderboard_json()`: Transform results to website-ready format with rankings
  - `save_results()`: Output leaderboard.json, benchmark_summary.json, and SUMMARY.md

**Score Transformation:**
- Internal accuracy metrics (0-1 scale) → Leaderboard percentages (0-100 scale)
- `easy_success`, `medium_success`, `hard_success` from metrics_by_difficulty
- `sql_success`, `function_success` from metrics_by_type
- Handles missing data with `null` values (not 0)
- Ranks models by average of available success rates

**Output Structure:**
```
results/benchmark-{timestamp}/
├── gpt-4o/                    # Per-model detailed results
│   ├── evaluation_results.json
│   ├── evaluation_results.csv
│   └── evaluation_report.md
├── claude-3-5-sonnet-20241022/
│   └── (same structure)
├── leaderboard.json          # Website-ready JSON with rankings
├── benchmark_summary.json    # Full metadata and results
└── SUMMARY.md               # Human-readable summary
```

**Usage:**
```python
from USABench.sdk.benchmark import BenchmarkRunner, BenchmarkRunnerConfig

config = BenchmarkRunnerConfig(
    models=["gpt-4o", "claude-3-5-sonnet-20241022"],
    sql_samples=None,  # None means all samples
    function_samples=None,
    output_dir="results"
)

runner = BenchmarkRunner(config)
results = runner.run_all_models()
runner.save_results()
```

## Testing and Validation

No formal test framework is configured. Validation approaches:
- Run small evaluations to verify functionality: `python3 -m USABench --model gpt-4o --sql-samples 5 --function-samples 5`
- Use baseline script: `./run_baseline.sh`
- Check results consistency and API connectivity
- Manual review of evaluation outputs

## Configuration

### API Keys
Can be set via .env file (recommended) or environment variables:
- **OPENAI_API_KEY**: Required for OpenAI models (GPT-4o, GPT-5, etc.)
- **ANTHROPIC_API_KEY**: Required for Anthropic models (Claude 3.5 Sonnet, Claude 4.5, etc.)
- **GEMINI_API_KEY**: Required for Google Gemini models (Gemini 2.0 Flash)
- **GROQ_API_KEY**: Required for Groq models (Llama 3.3 70B)
- **BLS_API_KEY**: Required for function calling evaluation (Bureau of Labor Statistics API)
- **BEA_API_KEY**: Required for function calling evaluation (Bureau of Economic Analysis API)

### Model Selection
**Pre-configured Models** (in MODEL_REGISTRY):
- **OpenAI**: gpt-5-chat, gpt-5-mini, gpt-4o, gpt-3.5-turbo
- **Anthropic**: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022, claude-sonnet-4-5-20250929, claude-opus-4-5-20251101
- **Google**: gemini/gemini-2.0-flash
- **Groq**: groq/llama-3.3-70b-versatile
- **Custom**: Any model supported by LiteLLM can be used with `--model` flag

**Parameter Handling**: The production client automatically handles model-specific parameter constraints via `litellm.drop_params = True` (e.g., temperature requirements for different models)

### Paths and Configuration
- **Data Location**: `USABench/data/usafacts.db` (SQLite database)
- **Results Directory**: Configurable via `--output-dir` (default: `results/`)
- **Output Formats**: JSON, CSV, and Markdown reports
- **Leaderboard Output**: Website-ready JSON at `results/benchmark-{timestamp}/leaderboard.json`

## Datasets

- **SQL Dataset**: 293 Text2SQL questions in `text2sql_ground_truth.json`
- **Function Calling Dataset**: 166 questions in `enhanced_function_calling_ground_truth.json`
- **Total Questions**: 459 (293 SQL + 166 Function)
- **Test Mode**: 10 questions (5 SQL + 5 Function) for quick validation
- **Full Mode**: All 459 questions for comprehensive evaluation
- **Database Schema**: Government economic data from USAFacts, BLS, and BEA in SQLite format
- **Difficulty Levels**: Easy/Medium/Hard classifications for both evaluation types