# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

USABench is a production-ready benchmark framework for evaluating language models on government economic data analysis tasks. It features dual evaluation capabilities: Text2SQL evaluation with targeted schema injection and function calling evaluation with real BLS/BEA API execution.

## Key Features

- **Text2SQL Evaluation**: 293 questions achieving ~50% accuracy with production evaluator
- **Function Calling Evaluation**: 166 questions with real API execution and 4-component binary metrics
- **Production Architecture**: Clean separation with core, evaluators, SDK, and CLI layers
- **Real API Integration**: BLS (Bureau of Labor Statistics) and BEA (Bureau of Economic Analysis) APIs
- **Multi-format Output**: JSON, CSV, and Markdown reports with comprehensive analytics

## Architecture

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
├── data/                    # Dataset and database
│   ├── usafacts.db         # SQLite database (government data)
│   ├── comprehensive_parallel_ground_truth.json  # 293 Text2SQL questions
│   └── enhanced_function_calling_ground_truth.json # 166 function questions
├── cli.py                   # Command-line interface
└── README.md               # Complete documentation
```

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install litellm sqlparse pydantic numpy pandas python-dotenv

# Install development dependencies (includes ruff)
pip install -e ".[dev]"

# Set required API keys
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"  # Optional
export BLS_API_KEY="your-bls-key"              # For function calling
export BEA_API_KEY="your-bea-key"              # For function calling
```

### Running Evaluations
```bash
# Quick mixed evaluation
python3 -m USABench --model gpt-4o --sql-samples 10 --function-samples 5

# Text2SQL only (high performance - 49.5% accuracy)
python3 -m USABench --evaluation-type sql --model gpt-4o --sql-samples 50

# Function calling evaluation (real API execution)
python3 -m USABench --evaluation-type function --model gpt-4o --function-samples 10

# Full evaluation with all samples and reports
python3 -m USABench --evaluation-type full --model gpt-4o --save-results --generate-report
```

### Testing and Validation
```bash
# Code quality checks
ruff check .                    # Run linter
ruff format .                   # Format code
ruff check --fix .              # Auto-fix issues

# Quick system test
python3 -m USABench --model gpt-4o --sql-samples 3 --function-samples 3

# Dataset information
python3 -m USABench --dataset-info

# Model compatibility check
python3 -m USABench --list-models

# Validate database connection
python3 -c "import sqlite3; print('DB OK:', sqlite3.connect('data/usafacts.db').execute('SELECT COUNT(*) FROM budget_outlays').fetchone())"

# Run tests (if available)
pytest tests/ -v
```

## Core Components

### Production Evaluators

**ProductionSQLEvaluator** (`evaluators/production_sql.py`):
- Advanced Text2SQL with question classification and targeted schema injection
- Achieves 49.5% accuracy on 293 questions with GPT-4o
- Binary metrics with execution accuracy (0.8) and result correctness (0.9)
- Fixes table name issues (generates correct 'budget_outlays' instead of 'government_spending')

**FunctionCallEvaluator** (`evaluators/berkeley_function.py`):
- Function Calling evaluation with 4-component metrics
- Real BLS/BEA API execution with provided keys
- 4-component binary metrics: Function Selection, Parameter Accuracy, Execution Success, Result Accuracy
- Fixes 0% results issue - now achieving 20% average score with perfect API execution

### SDK Interface

**USABench Class** (`sdk/api.py`):
- High-level interface for all evaluation types
- Lazy initialization of evaluators
- Comprehensive results analysis and reporting
- Fluent API for configuration

### CLI Interface

**Command-Line Tool** (`cli.py`):
- Professional CLI with comprehensive options
- Supports all evaluation types: sql, function, mixed, full
- Multi-format output with detailed reporting
- Error handling and validation

## Data Sources

### Database Schema (`data/usafacts.db`)
- **budget_outlays**: Government spending by function, fiscal year
- **time_series_data**: Economic indicators (CPI, employment, productivity)
- **industry_gdp**: GDP by industry sector
- **gdp_by_industry**: Regional GDP measurements

### Evaluation Datasets
- **Text2SQL**: 293 questions targeting government budget and economic data
- **Function Calling**: 166 questions with real BLS/BEA API functions
- **Difficulty Levels**: Easy (30%), Medium (50%), Hard (20%)

## Performance Benchmarks

### Recent Results (GPT-4o)
- **Text2SQL**: 49.5% accuracy (145/293 questions correct)
- **Function Calling**: 20% average score with 100% API execution success
- **Mixed Evaluation**: 30% overall accuracy combining both evaluation types
- **API Integration**: BLS/BEA APIs responding successfully with real data

### Key Achievements
- **Production Ready**: Complete CLI and SDK interfaces working
- **Real API Integration**: BLS/BEA APIs executing successfully
- **Function Calling**: 4-component binary metrics implemented
- **Schema Targeting**: Fixed table name generation issues
- **Multi-format Output**: JSON, CSV, Markdown reports with analytics

## Configuration

### API Keys
- **OPENAI_API_KEY**: Required for OpenAI models (GPT-4o, etc.)
- **ANTHROPIC_API_KEY**: Required for Anthropic models (Claude, etc.)
- **BLS_API_KEY**: Required for function calling evaluation (Bureau of Labor Statistics)
- **BEA_API_KEY**: Required for function calling evaluation (Bureau of Economic Analysis)

### Model Support
- **OpenAI**: gpt-4o (recommended), gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
- **Anthropic**: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
- **Other**: Any model supported by LiteLLM

### Paths and Files
- **Data Directory**: `data/` (contains database and ground truth files)
- **Database**: `data/usafacts.db` (SQLite with government economic data)
- **Results**: `results/` (JSON, CSV, Markdown output files)
- **Configuration**: `sdk/config.py` (BenchmarkConfig class)

## Common Issues and Solutions

### Import Errors
```bash
# Ensure all dependencies are installed
pip install litellm sqlparse pydantic numpy pandas python-dotenv
```

### API Authentication
```bash
# Set environment variables
export OPENAI_API_KEY="your-key"
export BLS_API_KEY="your-bls-key"  # For function calling
export BEA_API_KEY="your-bea-key"  # For function calling
```

### Database Issues
```bash
# Check database exists and is readable
ls -la data/usafacts.db
python3 -c "import sqlite3; print('Tables:', [t[0] for t in sqlite3.connect('data/usafacts.db').execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()])"
```

### Function Calling 0% Results
- Ensure BLS_API_KEY and BEA_API_KEY environment variables are set
- Check network connectivity to BLS/BEA APIs
- Verify BerkeleyFunctionEvaluator is being used (not basic FunctionEvaluator)

## Testing Framework

No formal test framework is configured. Validation is done through:
- CLI integration tests with small sample sizes
- API connectivity tests for BLS/BEA endpoints
- Database schema validation
- Model response parsing validation

## Contributing Guidelines

1. **Code Style**: Follow existing patterns in evaluators and core modules
2. **Error Handling**: Implement comprehensive error handling with logging
3. **Documentation**: Update README.md and inline documentation
4. **Testing**: Validate with multiple models and sample sizes
5. **Performance**: Monitor evaluation speed and accuracy metrics

## Important Notes

- **Database File**: The `usafacts.db` file is included and should be committed with code changes
- **API Keys**: Never commit API keys to the repository
- **Results Files**: Results in `results/` directory are examples and can be ignored/excluded
- **Cache Files**: `__pycache__` directories can be ignored
- **Production Use**: The system is production-ready with proper error handling and logging

## Examples

### Python SDK Usage
```python
from USABench.sdk import USABench, BenchmarkConfig

# Configure benchmark
config = BenchmarkConfig(
    model_name="gpt-4o",
    sql_samples=50,
    function_samples=25,
    save_results=True
)

# Run evaluation
benchmark = USABench(config)
analysis = benchmark.run_and_analyze(evaluation_type="mixed")

print(f"Overall Accuracy: {analysis['overall_metrics']['accuracy']:.1%}")
print(f"SQL Accuracy: {analysis['metrics_by_type']['sql']['accuracy']:.1%}")
print(f"Function Score: {analysis['metrics_by_type']['function']['average_score']:.3f}")
```

### Advanced CLI Usage
```bash
# Model comparison workflow
python3 -m USABench --model gpt-4o --evaluation-type mixed --sql-samples 50 --function-samples 25 --save-results --output-dir ./gpt4o-results
python3 -m USABench --model claude-3-5-sonnet-20241022 --evaluation-type mixed --sql-samples 50 --function-samples 25 --save-results --output-dir ./claude-results

# Research and development
python3 -m USABench --model gpt-4o --difficulty easy --sql-samples 20
python3 -m USABench --model gpt-4o --difficulty hard --sql-samples 10

# Production benchmarking
python3 -m USABench --evaluation-type full --model gpt-4o --save-results --generate-report --output-dir ./production-benchmark --verbose
```