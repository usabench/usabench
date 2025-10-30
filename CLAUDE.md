# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

USABench is a comprehensive benchmark framework for evaluating language models on government economic data analysis tasks, featuring Text2SQL and Function Calling evaluations with real API integration. The codebase implements a clean architecture with modular evaluators, SDK interface, and CLI.

## Development Commands

### Environment Setup
```bash
# Set required API keys
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"  # Optional
export BLS_API_KEY="your-bls-key"              # Optional for function calling
export BEA_API_KEY="your-bea-key"              # Optional for function calling

# Install Python dependencies (preferred method)
pip install -e .

# Alternative: Install dependencies directly
pip install litellm sqlparse pydantic numpy pandas python-dotenv

# Install Node.js dependencies (for landing page development)
npm install
```

### Running Evaluations

The main interface is the CLI module accessible via `python3 -m USABench`:

```bash
# Quick mixed evaluation
python3 -m USABench --model gpt-4o --sql-samples 10 --function-samples 5

# Text2SQL only evaluation
python3 -m USABench --evaluation-type sql --model gpt-4o --sql-samples 50

# Function calling evaluation
python3 -m USABench --evaluation-type function --model gpt-4o --function-samples 10

# Full evaluation with reports
python3 -m USABench --evaluation-type full --model gpt-4o --save-results --generate-report

# Run baseline evaluation
./run_baseline.sh
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
│   ├── production_client.py # LiteLLM integration
│   └── client.py            # Legacy LLM client
├── evaluators/              # Evaluation implementations
│   ├── production_sql.py    # Production Text2SQL evaluator
│   ├── berkeley_function.py # Function calling evaluator
│   ├── sql.py              # Basic SQL evaluator
│   └── function.py         # Basic function evaluator
├── sdk/                     # High-level SDK interface
│   ├── api.py              # Main USABench class
│   ├── config.py           # Configuration management
│   └── results.py          # Results analysis
├── metrics/                 # Evaluation metrics
├── data/                    # Dataset and database
│   ├── usafacts.db         # SQLite database
│   ├── comprehensive_parallel_ground_truth.json    # SQL dataset (293 questions)
│   └── enhanced_function_calling_ground_truth.json # Function dataset (166 questions)
├── cli.py                   # Command-line interface
└── __main__.py             # Module entry point
```

### Key Design Patterns

- **Modular Evaluators**: Separate evaluators for SQL and function calling with pluggable architecture
- **Production Client**: Direct LiteLLM integration without framework dependencies for reliable API calls
- **SDK Interface**: High-level `USABench` class for programmatic access
- **CLI Integration**: Full-featured command-line interface via `python3 -m USABench`
- **Real API Integration**: Function calling evaluation uses actual BLS/BEA government APIs

### Data Flow

1. CLI/SDK → Configuration → Data Loader → Evaluator
2. Evaluator → LLM Client → Model Response → Metrics
3. Results → Analysis → Reports (JSON/CSV/Markdown)

## Testing and Validation

No formal test framework is configured. Validation approaches:
- Run small evaluations to verify functionality: `python3 -m USABench --model gpt-4o --sql-samples 5 --function-samples 5`
- Use baseline script: `./run_baseline.sh`
- Check results consistency and API connectivity
- Manual review of evaluation outputs

## Configuration

- **API Keys**: Set in environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, BLS_API_KEY, BEA_API_KEY)
- **Model Selection**: All LiteLLM-supported models (gpt-4o, claude-3-5-sonnet-20241022, etc.)
- **Data Location**: `USABench/data/usafacts.db` (SQLite database)
- **Results**: Configurable output directory with JSON/CSV/Markdown formats

## Datasets

- **SQL Dataset**: 293 Text2SQL questions in `comprehensive_parallel_ground_truth.json`
- **Function Calling Dataset**: 166 questions in `enhanced_function_calling_ground_truth.json`
- **Database Schema**: Government economic data from USAFacts, BLS, and BEA in SQLite format
- **Difficulty Levels**: Easy/Medium/Hard classifications for both evaluation types