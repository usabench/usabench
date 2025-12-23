# USABench: Government Data Analysis Benchmark

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-Supported-green.svg)](https://github.com/BerriAI/litellm)

A comprehensive benchmark framework for evaluating language models on government data analysis tasks, featuring Text2SQL evaluation and function calling evaluation with real API execution.

## 🚀 Features

### 🎯 Dual Evaluation Framework
- **Text2SQL Evaluation**: 293 questions with targeted schema injection and binary metrics
- **Function Calling Evaluation**: 166 questions with real BLS/BEA API execution and 4-component scoring

### 🏗️ Production Architecture
- **ProductionSQLEvaluator**: Advanced Text2SQL with question classification and targeted schema
- **FunctionCallEvaluator**: Real API execution with BLS/BEA integration
- **Clean Architecture**: Modular design with core, evaluators, SDK, and CLI layers

### 🌐 Real API Integration
- **BLS (Bureau of Labor Statistics)**: CPI, Employment Cost Index, Productivity data
- **BEA (Bureau of Economic Analysis)**: GDP by Industry, Regional Income data
- **4-Component Binary Metrics**: Function Selection, Parameter Accuracy, Execution Success, Result Accuracy

### 📊 Comprehensive Results
- **Multiple Output Formats**: JSON, CSV, Markdown reports
- **Performance Analytics**: By evaluation type, difficulty, and detailed breakdowns
- **Error Analysis**: Comprehensive failure analysis and debugging information

## 🏁 Quick Start

### Installation

#### Option 1: Using uv (Recommended)
```bash
# Install using uv (fast Python package manager)
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows
```

#### Option 2: Using pip
```bash
# Install dependencies
pip install litellm sqlparse pydantic numpy pandas python-dotenv

# Or install from pyproject.toml
pip install -e .
```

### Environment Configuration

#### Option 1: Using .env file (Recommended)
Create a `.env` file in the project root:
```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
BLS_API_KEY=your-bls-key
BEA_API_KEY=your-bea-key
EOF
```

#### Option 2: Export environment variables
```bash
# Set API keys in your shell
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"  # Optional
export BLS_API_KEY="your-bls-key"              # Optional for function calling
export BEA_API_KEY="your-bea-key"              # Optional for function calling
```

**Note**: The `.env` file is automatically loaded by python-dotenv when running evaluations. Make sure your `.env` file is not committed to version control.

### Basic Usage
```bash
# Quick mixed evaluation
python3 -m USABench --model gpt-4o --sql-samples 10 --function-samples 5

# Text2SQL only (high performance)
python3 -m USABench --evaluation-type sql --model gpt-4o --sql-samples 50

# Function calling evaluation
python3 -m USABench --evaluation-type function --model gpt-4o --function-samples 10

# Full evaluation with reports
python3 -m USABench --evaluation-type full --model gpt-4o --save-results --generate-report
```

## 📁 Architecture

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
│   ├── comprehensive_parallel_ground_truth.json
│   └── enhanced_function_calling_ground_truth.json
├── cli.py                   # Command-line interface
└── README.md               # This file
```

## 🎯 Evaluation Types

### Text2SQL Evaluation
- **Dataset**: 293 carefully curated SQL questions
- **Performance**: ~50% accuracy with GPT-4o
- **Features**: Targeted schema injection, question classification, binary metrics
- **Tables**: `budget_outlays`, `time_series_data`, `industry_gdp`, etc.

### Function Calling Evaluation
- **Dataset**: 166 function calling questions
- **APIs**: Real BLS and BEA government data APIs
- **Metrics**: 4-component binary scoring system
- **Functions**: `get_cpi_data`, `get_employment_cost_index`, `get_gdp_by_industry`, etc.

## 🔧 CLI Interface

### Model Configuration
```bash
--model gpt-4o                    # Model selection
--temperature 0.0                 # Sampling temperature
--max-tokens 2000                 # Maximum response tokens
```

### Evaluation Types
```bash
--evaluation-type sql             # Text2SQL only
--evaluation-type function        # Function calling only
--evaluation-type mixed           # Both evaluations
--evaluation-type full            # All available samples
```

### Sample Control
```bash
--sql-samples 50                  # Number of SQL questions
--function-samples 25             # Number of function calling questions
--difficulty easy medium          # Filter by difficulty
```

### Output Options
```bash
--save-results                    # Save JSON/CSV results
--generate-report                 # Generate Markdown report
--output-dir ./results            # Custom output directory
--verbose                         # Detailed logging
```

## 🌟 Supported Models

### OpenAI Models
- `gpt-4o` (Recommended)
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

### Anthropic Models
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`

### Other Models
Any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers)

## 📊 Performance Benchmarks

### Recent Results (GPT-4o)
- **Text2SQL**: 49.5% accuracy (145/293 questions correct)
- **Function Calling**: 20% average score with 100% API execution success
- **Mixed Evaluation**: 30% overall accuracy combining both evaluation types

### Key Achievements
- ✅ **Real API Integration**: BLS/BEA APIs executing successfully
- ✅ **Function Calling**: 4-component binary metrics working
- ✅ **Production Ready**: Comprehensive CLI and SDK interfaces
- ✅ **Multi-format Output**: JSON, CSV, and Markdown reports

## 🛠️ Advanced Usage

### Model Comparison
```bash
# GPT-4o evaluation
python3 -m USABench --model gpt-4o --evaluation-type mixed \
  --sql-samples 50 --function-samples 25 --save-results \
  --output-dir ./gpt4o-results

# Claude Sonnet evaluation
python3 -m USABench --model claude-3-5-sonnet-20241022 \
  --evaluation-type mixed --sql-samples 50 --function-samples 25 \
  --save-results --output-dir ./claude-results
```

### Research & Development
```bash
# Quick testing with small samples
python3 -m USABench --model gpt-4o --sql-samples 5 --function-samples 5

# Difficulty-specific evaluation
python3 -m USABench --model gpt-4o --difficulty easy --sql-samples 20
python3 -m USABench --model gpt-4o --difficulty hard --sql-samples 20
```

### Production Benchmarking
```bash
# Comprehensive evaluation with all features
python3 -m USABench --evaluation-type full --model gpt-4o \
  --save-results --generate-report --output-dir ./production-benchmark \
  --verbose
```

## 🔍 Dataset Information

### SQL Dataset
- **File**: `comprehensive_parallel_ground_truth.json`
- **Questions**: 293 Text2SQL evaluation questions
- **Difficulty**: Easy (30%), Medium (50%), Hard (20%)
- **Tables**: Government economic data (budget, GDP, employment, etc.)

### Function Calling Dataset
- **File**: `enhanced_function_calling_ground_truth.json`
- **Questions**: 166 function calling evaluation questions
- **APIs**: Real BLS and BEA government data APIs
- **Functions**: 5+ government data API functions with real execution

### Database Schema
- **File**: `usafacts.db` (SQLite)
- **Tables**: `budget_outlays`, `time_series_data`, `industry_gdp`, `gdp_by_industry`
- **Data**: Real government economic data from USAFacts, BLS, and BEA

## 🐛 Troubleshooting

### Common Issues

**API Authentication Errors**
```bash
# Option 1: Use .env file (recommended)
# Create .env file with your API keys:
cat > .env << EOF
EOF

# Option 2: Export environment variables
export OPENAI_API_KEY="your-key"
export BLS_API_KEY="your-bls-key"  # For function calling
export BEA_API_KEY="your-bea-key"  # For function calling
```

**Database Connection Issues**
```bash
# Check database path
python3 -m USABench --dataset-info --data-dir USABench/data
```

**Import Errors**
```bash
# Install missing dependencies
pip install litellm sqlparse pydantic numpy pandas python-dotenv
```

## 📈 Output Examples

### Console Output
```
🚀 Initializing USABench...
   Model: gpt-4o
   Evaluation Type: mixed
   Available: 293 SQL, 166 Function questions

⏳ Running mixed evaluation...

============================================================
EVALUATION RESULTS SUMMARY
============================================================

📊 Overall Performance:
   Total Samples: 10
   Accuracy: 30.0%
   Average Score: 0.490
   Avg Execution Time: 5.61s
   Error Rate: 0.0%

📋 Performance by Type:
   SQL:
     - Samples: 5
     - Accuracy: 60.0%
     - Avg Score: 0.781
   FUNCTION:
     - Samples: 5
     - Accuracy: 0.0%
     - Avg Score: 0.200

✅ Evaluation completed successfully!
```
---

**USABench** - Benchmarking AI on Government Data

![USAFacts](/usafacts_logo_magenta.svg)

Project support provided by [USAFacts](https://www.usafacts.org). 



# Disclaimer

The USABench project is provided for **academic, research, and public interest purposes only**.  

No representations or warranties of any kind are made regarding the accuracy, completeness, reliability, or fitness for any particular purpose of the materials provided herein.

All content, code, and data are provided **“as is”**, without warranty of any kind, express or implied, including but not limited to warranties of merchantability, non-infringement, or fitness for a particular purpose.

Use of the USABench name, logo, or any attribution to the project or its sponsors must not suggest or imply endorsement, partnership, or certification unless explicitly authorized in writing by the respective organization.

Project sponsors and contributors disclaim all liability for any loss, injury, claim, or damage arising from use of this project, its benchmarks, or derivative works.

By using or contributing to this project, you agree to these terms and to the [Apache License 2.0](LICENSE).

