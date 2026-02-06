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

# Export golden records to CSV
python3 -m USABench.scripts.export_golden_records
```

## Architecture

### Main Components

```
USABench/
├── core/                     # Core framework components
│   ├── base.py              # Base classes, data models, parallel batch evaluation
│   ├── loader.py            # Data loading with caching
│   ├── production_client.py # Thread-safe LiteLLM integration
│   ├── rate_limiter.py      # Thread-safe rate limiting for API calls
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
├── scripts/                 # Utility scripts
│   ├── __init__.py         # Package marker
│   └── export_golden_records.py # Export all 459 questions to CSV
├── data/                    # Dataset and database
│   ├── usafacts.db         # SQLite database (459 samples total)
│   ├── text2sql_ground_truth.json           # 293 SQL questions
│   ├── fcl_ground_truth.json                # 167 function questions (BLS/BEA APIs)
│   ├── mock_fcl_ground_truth.json           # 166 mock functions (abstract APIs)
│   └── golden_records_consolidated.csv      # All questions in single CSV (generated)
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
- **Parallel Batch Evaluation**: ThreadPoolExecutor-based parallel sample processing (configurable workers)
- **Thread-Safe Components**: Lock-protected usage tracking, thread-local database connections
- **Connection Pooling**: HTTP session pooling for API calls, SQLite connection reuse per thread
- **Rate Limiting**: Thread-safe sliding window rate limiter for API throttling

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
- **OpenAI GPT-5**: gpt-5-pro, gpt-5.2, gpt-5-mini
- **OpenAI Reasoning**: o4-mini, o3-mini, o3
- **OpenAI GPT-4**: gpt-4o, gpt-4o-mini
- **Anthropic**: claude-sonnet-4-5-20250929, claude-opus-4-5-20251101, claude-3-haiku-20240307
- **Google Gemini 3.0**: gemini/gemini-3-pro-preview
- **Google Gemini 2.5**: gemini/gemini-2.5-flash
- **Google Gemini 2.0**: gemini/gemini-2.0-flash-thinking-exp-01-21, gemini/gemini-2.0-flash
- **Google Gemini 1.5**: gemini/gemini-1.5-pro-latest
- **Groq**: groq/llama-3.3-70b-versatile
- **xAI Grok**: xai/grok-4-1-fast-non-reasoning, xai/grok-4-1-fast-reasoning
- **Custom**: Any model supported by LiteLLM can be used with `--model` flag

**Parameter Handling**: The production client automatically handles model-specific parameter constraints via `litellm.drop_params = True` (e.g., temperature requirements for different models)

### Paths and Configuration
- **Data Location**: `USABench/data/usafacts.db` (SQLite database)
- **Results Directory**: Configurable via `--output-dir` (default: `results/`)
- **Output Formats**: JSON, CSV, and Markdown reports
- **Leaderboard Output**: Website-ready JSON at `results/benchmark-{timestamp}/leaderboard.json`

## Performance Optimizations

The framework includes several performance optimizations for faster benchmark execution:

### Parallel Batch Evaluation
- **ThreadPoolExecutor**: Parallel sample processing with configurable worker count
- **Model-Specific Concurrency**: Automatic worker count adjustment based on provider rate limits
  - OpenAI models: 10 workers (generous concurrency limits)
  - Claude models: 1 worker (strict concurrent connection limits)
  - Grok models: 1 worker (very strict concurrent connection limits)
  - Gemini models: 5 workers (moderate limits)
  - Groq models: 5 workers (moderate limits)
- **Automatic Retry Logic**: 3 retries with exponential backoff for rate limit errors
- **Thread Safety**: All shared resources protected with locks
- **Expected Speedup**: 4-10x for OpenAI/Gemini/Groq, sequential for Claude/Grok (prevents rate limit errors)

```python
from USABench.core.base import EvaluationConfig

# Configure parallel workers (overrides model-specific defaults)
config = EvaluationConfig(
    model_name="gpt-4o",
    max_workers=10  # Increase for higher throughput
)
```

**Important**: The MODEL_REGISTRY in `sdk/benchmark.py` specifies optimal `max_workers` for each model based on their API rate limits. During benchmarks, these values are used automatically to prevent concurrent connection errors.

### HTTP Connection Pooling
- **Session Reuse**: `requests.Session()` with connection pooling for government APIs
- **Retry Logic**: Automatic retries (3x) with exponential backoff for transient errors
- **Status Codes**: Handles 429, 500, 502, 503, 504 with automatic retry
- **Pool Size**: 10 connections, max 20 per pool

### Database Connection Pooling
- **Thread-Local Connections**: SQLite connections reused within same thread
- **Connection Parameters**: `check_same_thread=False`, 30s timeout
- **Eliminates Overhead**: No connect/close per query

### Rate Limiting
- **Thread-Safe Rate Limiter**: Sliding window algorithm in `core/rate_limiter.py`
- **Pre-configured Limits**: OpenAI (3500 RPM), BLS (100/min), BEA (80/min)

```python
from USABench.core.rate_limiter import RateLimiter, create_openai_limiter

# Create rate limiter
limiter = create_openai_limiter()  # 3500 requests/minute

# Use in API calls
if limiter.acquire():  # Blocks until slot available
    # Make API call
    pass
```

### Data Caching
- **DataLoader Caching**: JSON files loaded once and cached in memory
- **Cache Methods**: `_load_sql_data()`, `_load_function_data()`, `_load_function_eval_data()`
- **Cache Control**: `clear_cache()` method for invalidation

### Performance Estimates
| Scenario | Before | After | Speedup |
|----------|--------|-------|---------|
| Test mode (10 samples) | ~8 min | ~2 min | 4x |
| Single model (460 samples) | ~10 hours | ~1.5-2 hours | 5-6x |
| 3-model benchmark | ~30 hours | ~5 hours | 6x |

## Datasets

- **SQL Dataset**: 293 Text2SQL questions in `text2sql_ground_truth.json`
- **Function Calling Dataset**: 167 questions in `fcl_ground_truth.json` (concrete BLS/BEA API functions)
  - Used for benchmark evaluations with real API execution
  - Functions: `get_gdp_by_industry`, `get_cpi_data`, `get_employment_cost_index`, etc.
- **Mock Function Dataset**: 166 questions in `mock_fcl_ground_truth.json` (abstract functions)
  - Used for CSV exports and future mock testing
  - Functions: `query_economic_data`, `query_budget_data`, etc.
- **Total Questions**: 460 (293 SQL + 167 Function)
- **Test Mode**: 10 questions (5 SQL + 5 Function) for quick validation
- **Full Mode**: All 460 questions for comprehensive evaluation
- **Database Schema**: Government economic data from USAFacts, BLS, and BEA in SQLite format
- **Difficulty Levels**: Easy/Medium/Hard classifications for both evaluation types

### Golden Records Export

Export all 459 ground truth questions to a unified CSV:
```bash
python3 -m USABench.scripts.export_golden_records
```

**Output**: `USABench/data/golden_records_consolidated.csv`

**Structure** (13 columns):
- **Summary**: question_id, question_type, question_text, difficulty, primary_tables, expected_output_rows, workflow_complexity
- **Metadata**: generation_model, generation_timestamp
- **Technical Details**: reference_sql (SQL only), function_sequence (Function only), expected_result_summary, success_criteria

**Features**:
- All 459 questions in single spreadsheet
- SQL difficulty inferred via heuristics (easy: simple queries, medium: GROUP BY/JOINs, hard: subqueries/HAVING/multiple JOINs)
- Function difficulty from source data (easy: 11, medium: 48, hard: 107)
- Easy viewing in Excel, Google Sheets, or any CSV viewer
- Hybrid format: human-readable summary columns first, technical details at end