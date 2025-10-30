# USABench Technical Documentation: Complete Benchmark Guide

## Table of Contents
1. [Overview: What is USABench?](#overview-what-is-usabench)
2. [The Dataset Discovery Problem](#the-dataset-discovery-problem)
3. [Understanding the Two Evaluation Types](#understanding-the-two-evaluation-types)
4. [Deep Dive: Text2SQL Benchmark](#deep-dive-text2sql-benchmark)
5. [Deep Dive: Function Calling Benchmarks](#deep-dive-function-calling-benchmarks)
6. [How Models Are Evaluated](#how-models-are-evaluated)
7. [Complete Reference Guide](#complete-reference-guide)
8. [Troubleshooting and Best Practices](#troubleshooting-and-best-practices)

---

## Overview: What is USABench?

USABench is a benchmark framework designed to test how well AI language models can analyze government economic data. Think of it as a standardized test for AI models, but instead of math problems, the models answer questions about real economic data from the US government.

### The Two Main Tests

1. **Text2SQL Test**: Can the model convert English questions into SQL database queries?
   - Example: "What was the defense budget in 2020?" → `SELECT amount FROM budget_outlays WHERE function_name='National Defense' AND fiscal_year=2020`

2. **Function Calling Test**: Can the model call the right API functions to get data?
   - Example: "What's the current inflation rate?" → Call `get_cpi_data()` function with correct parameters

### Why This Matters

Government data is complex, scattered across multiple databases, and requires precise queries to access. Testing AI models on this data helps us understand:
- How well they understand core concepts
- Their ability to work with structured data
- Their precision in following specific formatting requirements
- Their capability to handle real-world data analysis tasks

---

## The Dataset Discovery Problem

### What We Found

When reviewing the codebase, we discovered an important discrepancy:

**What the README says:**
- "We have one function calling dataset with 166 questions"

**What actually exists:**
```
USABench/data/
├── enhanced_function_calling_ground_truth.json (166 questions)
└── fcl_ground_truth.json (167 questions)  ← This one isn't documented!
```

### Why Two Datasets?

These datasets serve completely different purposes:

1. **Enhanced Dataset** (166 questions)
   - Tests high-level analytical thinking
   - Uses abstract functions like "analyze_trends" or "compare_categories"
   - Focuses on complex multi-step reasoning
   - Think of it as testing "Can the AI plan a complex analysis?"

2. **FCL Dataset** (167 questions)
   - Tests real API calling abilities
   - Uses actual government APIs (BLS, BEA)
   - Focuses on getting real data from real sources
   - Think of it as testing "Can the AI actually fetch real data?"

### The Confusion

The repository uses BOTH datasets but for different evaluators:
- Some evaluation code uses the Enhanced dataset
- Other evaluation code uses the FCL dataset
- The Berkeley Function Evaluator doesn't use either (it generates expected calls from scratch)

---

## Understanding the Two Evaluation Types

### 1. Text2SQL Evaluation

**What it tests:** Can an AI model convert natural language questions into SQL queries?

**Real-world analogy:** It's like asking someone who doesn't know SQL to get data from a database. They need to understand:
- What data you're asking for
- Which table contains that data
- How to write the query correctly

**The Database:** A SQLite database (`usafacts.db`) containing:
- Government budget data (2014-2024)
- Economic indicators (inflation, employment, etc.)
- GDP by industry
- Regional economic data

### 2. Function Calling Evaluation

**What it tests:** Can an AI model call the right functions with the right parameters?

**Real-world analogy:** It's like giving someone a phone with speed-dial buttons for different government agencies. They need to:
- Know which agency to call for which data
- Know what specific information to request
- Format their request correctly

**Two Different Approaches:**

**Approach A: Abstract Functions (Enhanced Dataset)**
- Philosophical functions like "analyze_trends" or "identify_patterns"
- Tests reasoning and planning abilities
- No real data fetching

**Approach B: Real APIs (FCL Dataset)**
- Actual government API calls (Bureau of Labor Statistics, Bureau of Economic Analysis)
- Tests ability to work with real APIs
- Fetches real, live data

---

## Deep Dive: Text2SQL Benchmark

### How It Works: Step by Step

#### Step 1: Model Receives a Question
```
User asks: "What were the top 3 spending categories in 2020?"
```

#### Step 2: System Identifies Relevant Tables
The system uses a "Question Classifier" that thinks:
- "spending categories" → needs `budget_outlays` table
- "2020" → needs to filter by `fiscal_year`
- "top 3" → needs ORDER BY and LIMIT

#### Step 3: Model Gets Targeted Database Schema
Instead of showing the model the entire database structure (which would be overwhelming), it only sees relevant tables:

```sql
Table: budget_outlays
Columns:
- function_name (TEXT): Category of spending (Defense, Education, etc.)
- fiscal_year (INTEGER): Year of the budget (2014-2024)
- amount (REAL): Amount spent in millions
```

#### Step 4: Model Receives a Carefully Crafted Prompt

**System Instructions (Hidden from user):**
```
You are a SQL expert. Generate a SQL query to answer the given question using the provided database schema.

IMPORTANT: All government data is limited to years 2014-2024 only.

Important guidelines:
- Use only the tables and columns described in the schema
- Data covers 2014-2024 only
- Write valid SQLite syntax
- Be precise and efficient
- Return only the SQL query without explanations
```

**What the model sees:**
```
Question: What were the top 3 spending categories in 2020?

Database Schema:
Table: budget_outlays
- function_name (TEXT): Category of spending
- fiscal_year (INTEGER): Year (2014-2024)
- amount (REAL): Amount in millions

Generate the SQL query:
```

#### Step 5: Model Generates SQL
```sql
SELECT function_name, amount
FROM budget_outlays
WHERE fiscal_year = 2020
ORDER BY amount DESC
LIMIT 3;
```

#### Step 6: Evaluation
The system checks two things:
1. **Does the query run?** (80% of the score)
2. **Does it return the correct answer?** (90% weight on correctness)

### Complete List of Tables

The database contains four main tables:

#### 1. budget_outlays
- **What it contains:** Government spending by category and year
- **Example row:** Defense, 2020, 721500.0 (millions)
- **Use cases:** Budget analysis, spending trends, fiscal comparisons

#### 2. time_series_data
- **What it contains:** Economic indicators over time
- **Example row:** CPI, 2020-01, 257.971
- **Use cases:** Inflation tracking, employment trends, productivity analysis

#### 3. industry_gdp
- **What it contains:** GDP broken down by industry sector
- **Example row:** Manufacturing, 2020, 2287.5 (billions)
- **Use cases:** Industry analysis, economic sector comparisons

#### 4. gdp_by_industry
- **What it contains:** Regional GDP measurements
- **Example row:** California, Tech, 2020, 450.3 (billions)
- **Use cases:** Regional economic analysis, state comparisons

### Success Metrics

**Current Performance (GPT-4o):**
- Overall accuracy: 49.5% (145/293 questions correct)
- Query execution success: 92%
- Correct results when query runs: 54%

**Common Failures:**
- Wrong table names (e.g., using "government_spending" instead of "budget_outlays")
- Date range errors (asking for data outside 2014-2024)
- Complex aggregations with GROUP BY errors

---

## Deep Dive: Function Calling Benchmarks

### Dataset 1: Enhanced Function Calling (Abstract Reasoning)

This dataset tests whether models can plan complex analytical workflows.

#### The Five Core Functions

##### 1. query_economic_data()
**Purpose:** Get any economic indicator data
**Think of it as:** A universal economic data search engine

**Parameters Explained:**
- `source`: Where to get data from (BLS, BEA, etc.)
  - Example: "BLS" for labor statistics
- `year_range`: What time period to analyze
  - Example: [2020, 2024] for last 5 years
- `indicator_type`: What kind of data
  - Example: "CPI" for inflation, "GDP" for economic growth
- `aggregation`: How to summarize the data
  - Example: "average" to get mean values

**Example Call:**
```json
{
  "name": "query_economic_data",
  "arguments": {
    "source": "BLS",
    "year_range": [2020, 2024],
    "indicator_type": "CPI",
    "aggregation": "average"
  }
}
```

##### 2. query_budget_data()
**Purpose:** Get government spending information
**Think of it as:** Federal budget explorer

**Parameters Explained:**
- `function_name`: Category of spending
  - Example: "National Defense" or "Education"
- `fiscal_year`: Specific year or range
  - Example: 2023 for single year
- `min_amount`/`max_amount`: Filter by spending size
  - Example: min_amount=1000000 for major expenditures only

##### 3. analyze_trends()
**Purpose:** Find patterns over time
**Think of it as:** Trend detective

**When to use:**
- Finding growth rates
- Identifying cyclical patterns
- Detecting anomalies

##### 4. compare_categories()
**Purpose:** Compare two different data categories
**Think of it as:** Data comparison tool

**When to use:**
- Comparing defense vs education spending
- Comparing inflation across regions
- Comparing employment across industries

##### 5. identify_patterns()
**Purpose:** Discover hidden patterns in data
**Think of it as:** Pattern recognition AI

**When to use:**
- Finding seasonal trends
- Detecting correlations
- Identifying unusual data points

#### Workflow Types Explained

The Enhanced dataset includes six types of question workflows:

1. **Single (139 questions):** One function call answers the question
   - Example: "What was inflation in 2023?" → Just call query_economic_data()

2. **Comparative (11 questions):** Compare multiple data points
   - Example: "Compare defense and education spending" → Call compare_categories()

3. **Fallback (2 questions):** Try one approach, then another if it fails
   - Example: Try specific data, fall back to general data if not available

4. **Sequential (12 questions):** Multiple steps in order
   - Example: Get data → analyze trends → summarize findings

5. **Multi-step (1 question):** Complex analysis requiring multiple functions
   - Example: Complex economic analysis across multiple datasets

6. **Pattern Discovery (1 question):** Find hidden patterns
   - Example: Discover correlations between different economic indicators

### Dataset 2: FCL Ground Truth (Real API Calling)

This dataset tests whether models can actually call real government APIs.

#### The Five Real API Functions

##### 1. get_cpi_data() - Consumer Price Index (Inflation)
**What it does:** Gets inflation data from Bureau of Labor Statistics
**Real API:** https://api.bls.gov/publicAPI/v2/timeseries/data/

**Parameters:**
- `series_id`: Specific data series to retrieve
  - Default: "CUUR0000SA0" (overall US inflation)
  - Other examples: "CUUR0000SA0L1E" (food inflation)
- `start_year`: Beginning of date range (2014-2024)
- `end_year`: End of date range (2014-2024)

**Example Question → Function Call:**
```
Question: "What was inflation from 2020 to 2023?"
↓
Function: get_cpi_data
Parameters: series_id=CUUR0000SA0, start_year=2020, end_year=2023
```

##### 2. get_employment_cost_index() - Labor Costs
**What it does:** Gets data on how much it costs to employ workers
**Real API:** Same BLS API, different series

**Parameters:**
- `series_id`: Employment cost series
  - Default: "CIU1010000000000I" (total compensation)
- `start_year`/`end_year`: Date range

**Use case:** Understanding wage growth and labor market tightness

##### 3. get_productivity_data() - Economic Efficiency
**What it does:** Gets data on output per hour worked
**Real API:** BLS productivity statistics

**Parameters:**
- `series_id`: Productivity measure
  - Default: "PRS85006092" (nonfarm business productivity)
- `start_year`/`end_year`: Date range

**Use case:** Understanding economic efficiency trends

##### 4. get_gdp_by_industry() - Economic Output by Sector
**What it does:** Gets GDP data broken down by industry
**Real API:** https://apps.bea.gov/api/data/

**Parameters:**
- `year`: Which year's data
- `industry`: Specific industry or "ALL"
  - Examples: "Manufacturing", "Finance", "ALL"
- `table_id`: Which BEA table to use
  - Default: "1" (main GDP by industry table)

**Example Question → Function Call:**
```
Question: "What industries contributed most to GDP in 2023?"
↓
Function: get_gdp_by_industry
Parameters: year=2023, industry=ALL, table_id=1
```

##### 5. get_regional_income() - Income by State
**What it does:** Gets personal income data by state
**Real API:** BEA regional data API

**Parameters:**
- `state`: State name or FIPS code
  - Examples: "California", "CA", "06"
- `year`: Which year's data
- `line_code`: Specific income measure
  - Default: "SA1-1" (total personal income)

**Use case:** Comparing economic conditions across states

#### How FCL Evaluation Works

1. **Model gets a question:** "What's the inflation rate?"

2. **Model must respond with exact format:**
   ```
   Function: get_cpi_data
   Parameters: series_id=CUUR0000SA0, start_year=2023, end_year=2024
   ```

3. **System makes real API call** to government servers

4. **Scoring (4 components, each yes/no):**
   - ✅ Did model choose the right function? (get_cpi_data not get_gdp_by_industry)
   - ✅ Are parameters correct? (valid series_id, years in range)
   - ✅ Does API call succeed? (no errors)
   - ✅ Is returned data what was asked for? (actually inflation data)

---

## How Models Are Evaluated

### The Evaluation Pipeline

```
Question → Model → Response → Evaluator → Score
```

Let's trace through a complete example:

#### Example: Text2SQL Evaluation

**Step 1: Load Question**
```python
question = "What was the education budget in 2022?"
ground_truth_sql = "SELECT amount FROM budget_outlays WHERE function_name='Education' AND fiscal_year=2022"
```

**Step 2: Model Generates SQL**
```python
model_response = model.generate(question)
# Returns: "SELECT amount FROM budget_outlays WHERE function_name='Education' AND fiscal_year=2022"
```

**Step 3: Execute and Compare**
```python
# Try to run the SQL
execution_success = True  # Query runs without errors

# Compare results
model_result = execute_sql(model_response)  # Returns: 80.3 billion
ground_truth_result = execute_sql(ground_truth_sql)  # Returns: 80.3 billion

results_match = (model_result == ground_truth_result)  # True
```

**Step 4: Calculate Score**
```python
if execution_success and results_match:
    score = 1.0  # Perfect score
elif execution_success:
    score = 0.5  # Partial credit for valid SQL
else:
    score = 0.0  # No credit
```

### The Four Evaluators Explained

#### 1. ProductionSQLEvaluator
**Purpose:** Production-ready Text2SQL evaluation
**Dataset:** comprehensive_parallel_ground_truth.json (293 questions)
**Special Features:**
- Smart table selection (only shows relevant tables)
- Fixes common model mistakes (wrong table names)
- Binary scoring (pass/fail)

**How it works:**
1. Classifies question to identify needed tables
2. Shows model only relevant schema
3. Generates SQL
4. Executes and validates

#### 2. FunctionEvaluator (Generic)
**Purpose:** Basic function calling evaluation
**Dataset:** enhanced_function_calling_ground_truth.json (166 questions)
**Special Features:**
- Pattern matching for function names
- Similarity scoring for parameters
- Supports complex workflows

**How it works:**
1. Model generates function call
2. Compares to expected function
3. Checks parameter similarity
4. Assigns partial credit

#### 3. BerkeleyFunctionEvaluator
**Purpose:** Real API calling with live data
**Dataset:** None (generates expectations from questions)
**Special Features:**
- Actually calls government APIs
- 4-component binary scoring
- Real data validation

**How it works:**
1. Model interprets question
2. Generates API call
3. System executes real API call
4. Validates all four components

#### 4. BerkeleyFCLEvaluator
**Purpose:** Advanced function calling with ground truth
**Dataset:** fcl_ground_truth.json (167 questions)
**Special Features:**
- Cached API responses for consistency
- Detailed error analysis
- Performance metrics

**How it works:**
1. Model generates function call
2. Compares to expected call
3. Validates against cached real data
4. Provides detailed scoring

### Scoring Systems

#### Binary Scoring (Text2SQL)
- **1.0:** Query works and returns correct results
- **0.0:** Query fails or returns wrong results

#### 4-Component Scoring (Function Calling)
Each component is worth 0.25 points:
1. **Function Selection (0.25):** Right function?
2. **Parameter Accuracy (0.25):** Right parameters?
3. **Execution Success (0.25):** Call succeeds?
4. **Result Correctness (0.25):** Right data returned?

**Total Score:** Sum of all components (0.0 to 1.0)

---

## Complete Reference Guide

### Directory Structure

```
USABench/
├── data/                           # All datasets and database
│   ├── usafacts.db                # SQLite database with government data
│   ├── comprehensive_parallel_ground_truth.json  # 293 SQL questions
│   ├── enhanced_function_calling_ground_truth.json  # 166 analytical questions
│   └── fcl_ground_truth.json      # 167 API calling questions
│
├── evaluators/                     # Evaluation implementations
│   ├── production_sql.py          # Production SQL evaluator
│   ├── function.py                # Generic function evaluator
│   ├── berkeley_function.py       # Real API evaluator
│   └── berkeley_fcl.py            # FCL-style evaluator
│
├── core/                          # Core framework
│   ├── loader.py                  # Data loading logic
│   ├── production_client.py       # LLM client
│   └── base.py                    # Base classes
│
└── sdk/                           # High-level interface
    ├── api.py                     # Main USABench class
    └── config.py                  # Configuration
```

### Configuration Files

#### Environment Variables
```bash
# Required for OpenAI models
export OPENAI_API_KEY="sk-..."

# Required for Anthropic models
export ANTHROPIC_API_KEY="sk-ant-..."

# Required for function calling with real APIs
export BLS_API_KEY="your-bls-key"
export BEA_API_KEY="your-bea-key"
```

#### Python Configuration
```python
from USABench.sdk import BenchmarkConfig

config = BenchmarkConfig(
    model_name="gpt-4o",           # Which model to test
    sql_samples=50,                 # How many SQL questions
    function_samples=25,            # How many function questions
    temperature=0.0,                # Model temperature (0=deterministic)
    max_tokens=2000,                # Max response length
    save_results=True,              # Save to file?
    output_dir="./results"          # Where to save
)
```

### Command Line Interface

#### Basic Commands

**Test SQL only:**
```bash
python3 -m USABench --evaluation-type sql --model gpt-4o --sql-samples 50
```

**Test function calling only:**
```bash
python3 -m USABench --evaluation-type function --model gpt-4o --function-samples 25
```

**Test both:**
```bash
python3 -m USABench --evaluation-type mixed --model gpt-4o \
  --sql-samples 25 --function-samples 25
```

**Full evaluation with reports:**
```bash
python3 -m USABench --evaluation-type full --model gpt-4o \
  --save-results --generate-report
```

#### Advanced Options

**Filter by difficulty:**
```bash
# Easy questions only
python3 -m USABench --model gpt-4o --difficulty easy --sql-samples 20

# Hard questions only
python3 -m USABench --model gpt-4o --difficulty hard --sql-samples 20
```

**Compare models:**
```bash
# Test GPT-4
python3 -m USABench --model gpt-4o --evaluation-type mixed \
  --sql-samples 50 --function-samples 25 --output-dir ./gpt4-results

# Test Claude
python3 -m USABench --model claude-3-5-sonnet-20241022 \
  --evaluation-type mixed --sql-samples 50 --function-samples 25 \
  --output-dir ./claude-results
```

### Python SDK Usage

#### Basic Example
```python
from USABench.sdk import USABench, BenchmarkConfig

# Configure
config = BenchmarkConfig(
    model_name="gpt-4o",
    sql_samples=10,
    function_samples=10
)

# Run benchmark
benchmark = USABench(config)
results = benchmark.run_evaluation(evaluation_type="mixed")

# Print results
print(f"SQL Accuracy: {results.sql_accuracy:.1%}")
print(f"Function Score: {results.function_score:.1%}")
```

#### Advanced Example with Analysis
```python
from USABench.sdk import USABench, BenchmarkConfig

# Configure for comprehensive testing
config = BenchmarkConfig(
    model_name="gpt-4o",
    sql_samples=100,
    function_samples=50,
    save_results=True,
    generate_report=True
)

# Initialize benchmark
benchmark = USABench(config)

# Run and analyze
analysis = benchmark.run_and_analyze(evaluation_type="mixed")

# Detailed results
print("Overall Metrics:")
print(f"  Accuracy: {analysis['overall_metrics']['accuracy']:.1%}")
print(f"  Average Score: {analysis['overall_metrics']['average_score']:.3f}")
print(f"  Error Rate: {analysis['overall_metrics']['error_rate']:.1%}")

print("\nSQL Performance:")
print(f"  Accuracy: {analysis['metrics_by_type']['sql']['accuracy']:.1%}")
print(f"  Execution Success: {analysis['metrics_by_type']['sql']['execution_rate']:.1%}")

print("\nFunction Calling Performance:")
print(f"  Average Score: {analysis['metrics_by_type']['function']['average_score']:.3f}")
print(f"  Perfect Scores: {analysis['metrics_by_type']['function']['perfect_scores']}")

# Save detailed report
benchmark.save_report(analysis, "benchmark_report.md")
```

### Output Formats

#### JSON Output
```json
{
  "model": "gpt-4o",
  "timestamp": "2024-01-20T10:30:00",
  "overall_accuracy": 0.495,
  "sql_results": {
    "total": 50,
    "correct": 25,
    "accuracy": 0.50
  },
  "function_results": {
    "total": 25,
    "average_score": 0.20,
    "component_scores": {
      "function_selection": 0.35,
      "parameter_accuracy": 0.25,
      "execution_success": 1.00,
      "result_correctness": 0.20
    }
  }
}
```

#### CSV Output
```csv
question_id,question,model_response,score,success,error
1,"What was the defense budget in 2020?","SELECT amount FROM...",1.0,true,
2,"Get current inflation rate","Function: get_cpi_data...",0.75,true,
```

#### Markdown Report
```markdown
# Evaluation Report

## Summary
- Model: gpt-4o
- Date: 2024-01-20
- Overall Accuracy: 49.5%

## SQL Evaluation
- Questions: 50
- Correct: 25
- Accuracy: 50.0%

## Function Calling
- Questions: 25
- Average Score: 20.0%
...
```

---

## Troubleshooting and Best Practices

### Common Problems and Solutions

#### Problem 1: Function calling always returns 0%

**Symptoms:**
- All function calling evaluations score 0
- No errors shown

**Causes:**
1. Missing API keys for BLS/BEA
2. Using wrong evaluator
3. Network issues

**Solutions:**
```bash
# 1. Set API keys
export BLS_API_KEY="your-key"
export BEA_API_KEY="your-key"

# 2. Use correct evaluator
python3 -m USABench --evaluation-type function --model gpt-4o

# 3. Test API connectivity
curl "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0?startyear=2023&endyear=2024"
```

#### Problem 2: SQL queries use wrong table names

**Symptoms:**
- Model generates "government_spending" instead of "budget_outlays"
- Queries fail with "table not found"

**Causes:**
- Model making assumptions about table names
- Not using ProductionSQLEvaluator

**Solutions:**
- Use ProductionSQLEvaluator (it includes smart table name correction)
- Ensure schema is clearly provided in prompt

#### Problem 3: Dataset not found errors

**Symptoms:**
```
FileNotFoundError: enhanced_function_calling_ground_truth.json not found
```

**Causes:**
- Missing data files
- Wrong directory structure

**Solutions:**
```bash
# Check if files exist
ls -la USABench/data/

# Download missing files if needed
# (Contact repository maintainers)
```

#### Problem 4: Models timing out

**Symptoms:**
- Evaluation hangs
- Timeout errors

**Causes:**
- Model taking too long to respond
- API rate limits

**Solutions:**
```python
# Increase timeout
config = BenchmarkConfig(
    model_name="gpt-4o",
    timeout=60,  # Increase from default 30
    max_retries=3
)

# Reduce batch size
config.batch_size = 1  # Process one at a time
```

### Best Practices

#### For Running Evaluations

1. **Start Small**
   ```bash
   # Test with 5 questions first
   python3 -m USABench --model gpt-4o --sql-samples 5 --function-samples 5
   ```

2. **Verify Environment**
   ```bash
   # Check all dependencies
   python3 -c "import USABench; print('OK')"
   
   # Verify database
   sqlite3 USABench/data/usafacts.db "SELECT COUNT(*) FROM budget_outlays"
   ```

3. **Use Appropriate Models**
   - **For SQL:** GPT-4o, Claude Sonnet (good at structured output)
   - **For Functions:** GPT-4o (best at following exact formats)

4. **Monitor API Usage**
   - BLS API: 500 requests/day limit
   - BEA API: 1000 requests/minute limit
   - OpenAI: Check your rate limits

#### For Interpreting Results

1. **SQL Evaluation**
   - 50% accuracy is good (current GPT-4o baseline)
   - Check execution vs correctness separately
   - Common failures: date ranges, aggregations

2. **Function Calling**
   - 20% average is current baseline
   - Perfect execution (100%) but low correctness is common
   - Parameter accuracy is usually the weakest component

3. **Comparing Models**
   - Run same questions for fair comparison
   - Use same temperature (0.0 for consistency)
   - Run multiple times for reliability

### Performance Optimization

#### Speed Improvements

1. **Parallel Processing**
   ```python
   config.parallel_workers = 4  # Process 4 questions at once
   ```

2. **Caching**
   ```python
   config.use_cache = True  # Cache model responses
   ```

3. **Batch Evaluation**
   ```python
   # Process in batches
   config.batch_size = 10
   ```

#### Accuracy Improvements

1. **Temperature Settings**
   ```python
   # Lower = more consistent
   config.temperature = 0.0
   ```

2. **Prompt Engineering**
   - Clear, specific instructions
   - Examples in prompts
   - Explicit format requirements

3. **Model Selection**
   - Latest models generally perform better
   - GPT-4o > GPT-4 > GPT-3.5
   - Claude Sonnet competitive with GPT-4o

---

## Summary and Recommendations

### Key Takeaways

1. **Two Function Datasets Exist**
   - Enhanced: High-level analytical functions
   - FCL: Real API calling with government data
   - Both serve different evaluation purposes

2. **Evaluation is Comprehensive**
   - Text2SQL tests database query generation
   - Function calling tests API interaction
   - Multiple evaluators for different approaches

3. **Real-World Focus**
   - Real government data (2014-2024)
   - Real APIs (BLS, BEA)
   - Practical economic analysis tasks

### Recommendations for Users

1. **Start with Mixed Evaluation**
   - Tests both SQL and function calling
   - Gives comprehensive view of model capabilities

2. **Use Production Evaluators**
   - ProductionSQLEvaluator for SQL
   - BerkeleyFunctionEvaluator for functions
   - These are most robust and realistic

3. **Set Up Environment Properly**
   - All API keys configured
   - Database accessible
   - Dependencies installed

### Recommendations for Maintainers

1. **Update Documentation**
   - README should mention both function datasets
   - Clarify which evaluator uses which dataset

2. **Standardize Dataset Format**
   - Consider unifying the two function calling formats
   - Add dataset versioning

3. **Add Dataset Selection**
   - CLI flag to choose dataset explicitly
   - Clear documentation on dataset differences

4. **Improve Error Messages**
   - More helpful error messages
   - Better debugging information
   - Setup validation script

### Future Improvements

1. **Extended Time Ranges**
   - Currently limited to 2014-2024
   - Consider historical data options

2. **More Data Sources**
   - Add Federal Reserve data
   - Include Census Bureau
   - State-level databases

3. **Advanced Evaluations**
   - Multi-turn conversations
   - Complex reasoning chains
   - Cross-dataset queries

4. **Better Tooling**
   - Web interface for results
   - Automated comparison reports
   - Performance tracking over time

---

## Appendix A: Complete Function Reference

### Enhanced Dataset Functions (Full Details)

```python
# 1. query_economic_data
{
  "description": "Query economic indicators and time series data",
  "parameters": {
    "category": {
      "type": "string",
      "required": False,
      "description": "Economic category to filter by",
      "examples": ["employment", "inflation", "gdp"]
    },
    "source": {
      "type": "string", 
      "required": True,
      "description": "Data source agency",
      "values": ["BLS", "BEA", "OMB", "Census"]
    },
    "year_range": {
      "type": "tuple",
      "required": True,
      "description": "Start and end years",
      "format": "[start_year, end_year]",
      "constraints": "2014 <= year <= 2024"
    },
    "indicator_type": {
      "type": "string",
      "required": True,
      "description": "Specific economic indicator",
      "examples": ["CPI", "GDP", "unemployment_rate", "productivity"]
    },
    "aggregation": {
      "type": "string",
      "required": False,
      "description": "How to aggregate data",
      "values": ["sum", "average", "min", "max", "count"],
      "default": "average"
    }
  },
  "returns": {
    "type": "object",
    "fields": {
      "data": "array of economic data points",
      "metadata": "information about the query",
      "summary_statistics": "calculated aggregations"
    }
  }
}

# 2. query_budget_data
{
  "description": "Query government budget and spending data",
  "parameters": {
    "function_name": {
      "type": "string",
      "required": False,
      "description": "Budget function/category",
      "examples": ["National Defense", "Education", "Health", "Social Security"]
    },
    "fiscal_year": {
      "type": "integer",
      "required": False,
      "description": "Single fiscal year",
      "constraints": "2014 <= year <= 2024"
    },
    "year_range": {
      "type": "tuple",
      "required": False,
      "description": "Range of fiscal years",
      "format": "[start_year, end_year]"
    },
    "min_amount": {
      "type": "float",
      "required": False,
      "description": "Minimum spending threshold in millions",
      "example": 1000000.0
    },
    "max_amount": {
      "type": "float",
      "required": False,
      "description": "Maximum spending threshold in millions",
      "example": 500000000.0
    },
    "aggregation": {
      "type": "string",
      "required": True,
      "description": "How to aggregate results",
      "values": ["sum", "avg", "count", "max", "min"]
    }
  }
}

# 3. analyze_trends
{
  "description": "Analyze trends in economic or budget data",
  "parameters": {
    "data_type": {
      "type": "string",
      "required": True,
      "description": "Type of data to analyze",
      "values": ["budget", "economic", "combined"]
    },
    "time_period": {
      "type": "tuple",
      "required": True,
      "description": "Period to analyze",
      "format": "[start_year, end_year]"
    },
    "analysis_type": {
      "type": "string",
      "required": True,
      "description": "Type of analysis",
      "values": ["trend", "correlation", "comparison", "forecast"]
    },
    "categories": {
      "type": "list",
      "required": True,
      "description": "Categories to include in analysis",
      "example": ["Defense", "Education", "Healthcare"]
    },
    "metrics": {
      "type": "list",
      "required": False,
      "description": "Specific metrics to calculate",
      "examples": ["growth_rate", "volatility", "correlation_coefficient"]
    }
  }
}

# 4. compare_categories
{
  "description": "Compare two categories of data",
  "parameters": {
    "category1": {
      "type": "string",
      "required": True,
      "description": "First category",
      "example": "National Defense"
    },
    "category2": {
      "type": "string",
      "required": True,
      "description": "Second category",
      "example": "Education"
    },
    "metric": {
      "type": "string",
      "required": True,
      "description": "Comparison metric",
      "values": ["spending", "growth", "proportion", "efficiency"]
    },
    "time_period": {
      "type": "tuple",
      "required": True,
      "description": "Period for comparison",
      "format": "[start_year, end_year]"
    },
    "comparison_type": {
      "type": "string",
      "required": True,
      "description": "How to compare",
      "values": ["absolute", "relative", "percentage", "ratio"]
    }
  }
}

# 5. identify_patterns
{
  "description": "Identify patterns in economic data",
  "parameters": {
    "data_sources": {
      "type": "list",
      "required": True,
      "description": "Data sources to analyze",
      "example": ["BLS", "BEA", "budget"]
    },
    "pattern_type": {
      "type": "string",
      "required": True,
      "description": "Type of pattern to find",
      "values": ["cyclical", "seasonal", "correlation", "anomaly", "trend"]
    },
    "time_horizon": {
      "type": "string",
      "required": True,
      "description": "Time period for analysis",
      "values": ["short_term", "medium_term", "long_term"],
      "mapping": {
        "short_term": "1-2 years",
        "medium_term": "3-5 years",
        "long_term": "5+ years"
      }
    },
    "confidence_threshold": {
      "type": "float",
      "required": False,
      "description": "Minimum confidence for pattern detection",
      "range": "0.0 to 1.0",
      "default": 0.95
    }
  }
}
```

### FCL Dataset API Functions (Full Details)

```python
# BLS API Functions

# 1. get_cpi_data
{
  "api_endpoint": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
  "description": "Retrieve Consumer Price Index (inflation) data",
  "parameters": {
    "series_id": {
      "type": "string",
      "required": False,
      "default": "CUUR0000SA0",
      "description": "BLS series identifier",
      "common_values": {
        "CUUR0000SA0": "All items, U.S. city average",
        "CUUR0000SA0L1E": "All items less food and energy",
        "CUUR0000SAF": "Food",
        "CUUR0000SAH": "Housing"
      }
    },
    "start_year": {
      "type": "integer",
      "required": True,
      "description": "Starting year for data",
      "constraints": "2014 <= year <= 2024"
    },
    "end_year": {
      "type": "integer",
      "required": True,
      "description": "Ending year for data",
      "constraints": "start_year <= end_year <= 2024"
    }
  },
  "response_format": {
    "status": "REQUEST_SUCCEEDED",
    "data": [{
      "year": "2024",
      "period": "M01",
      "value": "310.326",
      "footnotes": []
    }]
  }
}

# 2. get_employment_cost_index
{
  "api_endpoint": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
  "description": "Retrieve Employment Cost Index data",
  "parameters": {
    "series_id": {
      "type": "string",
      "required": False,
      "default": "CIU1010000000000I",
      "description": "ECI series identifier",
      "common_values": {
        "CIU1010000000000I": "Total compensation, all workers",
        "CIU2010000000000I": "Wages and salaries, all workers",
        "CIU3010000000000I": "Benefits, all workers"
      }
    },
    "start_year": {
      "type": "integer",
      "required": True
    },
    "end_year": {
      "type": "integer",
      "required": True
    }
  }
}

# 3. get_productivity_data
{
  "api_endpoint": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
  "description": "Retrieve productivity and costs data",
  "parameters": {
    "series_id": {
      "type": "string",
      "required": False,
      "default": "PRS85006092",
      "description": "Productivity series identifier",
      "common_values": {
        "PRS85006092": "Nonfarm business labor productivity",
        "PRS85006112": "Nonfarm business unit labor costs",
        "PRS85006152": "Nonfarm business real hourly compensation"
      }
    },
    "start_year": {
      "type": "integer",
      "required": True
    },
    "end_year": {
      "type": "integer",
      "required": True
    }
  }
}

# BEA API Functions

# 4. get_gdp_by_industry
{
  "api_endpoint": "https://apps.bea.gov/api/data/",
  "description": "Retrieve GDP by industry data",
  "parameters": {
    "year": {
      "type": "integer",
      "required": True,
      "description": "Year for GDP data",
      "constraints": "2014 <= year <= 2024"
    },
    "industry": {
      "type": "string",
      "required": False,
      "default": "ALL",
      "description": "Industry code or ALL",
      "examples": [
        "ALL",
        "11", # Agriculture
        "21", # Mining
        "22", # Utilities
        "23", # Construction
        "31-33", # Manufacturing
        "51", # Information
        "52", # Finance
      ]
    },
    "table_id": {
      "type": "string",
      "required": False,
      "default": "1",
      "description": "BEA table identifier",
      "values": {
        "1": "Value Added by Industry",
        "5": "Value Added by Industry as % of GDP",
        "6": "Components of Value Added by Industry"
      }
    }
  },
  "response_format": {
    "BEAAPI": {
      "Results": {
        "Data": [{
          "Industry": "Manufacturing",
          "Year": "2023",
          "GDP": "2345.6"
        }]
      }
    }
  }
}

# 5. get_regional_income
{
  "api_endpoint": "https://apps.bea.gov/api/data/",
  "description": "Retrieve regional personal income data",
  "parameters": {
    "state": {
      "type": "string",
      "required": True,
      "description": "State name or FIPS code",
      "examples": [
        "California",
        "CA",
        "06", # FIPS code for California
        "Texas",
        "TX",
        "48" # FIPS code for Texas
      ]
    },
    "year": {
      "type": "integer",
      "required": True,
      "description": "Year for income data",
      "constraints": "2014 <= year <= 2024"
    },
    "line_code": {
      "type": "string",
      "required": False,
      "default": "SA1-1",
      "description": "Income measure line code",
      "common_values": {
        "SA1-1": "Total personal income",
        "SA1-2": "Population",
        "SA1-3": "Per capita personal income",
        "SA25N": "Total employment",
        "SA27N": "Wages and salaries"
      }
    }
  }
}
```

## Appendix B: Error Messages and Solutions

### Common Error Messages

```python
# Error 1: Missing API Key
"Error: BLS_API_KEY environment variable not set"
Solution: export BLS_API_KEY="your-api-key"

# Error 2: Table Not Found
"sqlite3.OperationalError: no such table: government_spending"
Solution: Correct table name is 'budget_outlays'

# Error 3: Dataset Not Found
"FileNotFoundError: fcl_ground_truth.json not found"
Solution: Check data directory structure, ensure file exists

# Error 4: API Rate Limit
"Error: BLS API rate limit exceeded (500 requests/day)"
Solution: Wait 24 hours or use different API key

# Error 5: Invalid Date Range
"Error: Year 2025 outside valid range (2014-2024)"
Solution: Ensure all queries use years 2014-2024

# Error 6: Model Timeout
"TimeoutError: Model took longer than 30 seconds"
Solution: Increase timeout in config or use faster model

# Error 7: Invalid Function Name
"Error: Function 'get_inflation' not recognized"
Solution: Use correct function name 'get_cpi_data'

# Error 8: Parameter Type Error
"TypeError: year_range must be tuple, not list"
Solution: Use (2020, 2024) not [2020, 2024]

# Error 9: Network Error
"ConnectionError: Unable to reach BLS API"
Solution: Check internet connection, verify API is online

# Error 10: JSON Parse Error
"JSONDecodeError: Model response is not valid JSON"
Solution: Model may need clearer format instructions
```

## Appendix C: Quick Reference Card

### Essential Commands

```bash
# Install
pip install litellm sqlparse pydantic numpy pandas python-dotenv

# Set API Keys
export OPENAI_API_KEY="sk-..."
export BLS_API_KEY="..."
export BEA_API_KEY="..."

# Quick Test
python3 -m USABench --model gpt-4o --sql-samples 5 --function-samples 5

# SQL Only
python3 -m USABench --evaluation-type sql --model gpt-4o --sql-samples 50

# Function Only
python3 -m USABench --evaluation-type function --model gpt-4o --function-samples 25

# Full Evaluation
python3 -m USABench --evaluation-type full --model gpt-4o --save-results

# Check Dataset Info
python3 -m USABench --dataset-info
```

### Key Files

```
data/usafacts.db                                    # SQL database
data/comprehensive_parallel_ground_truth.json       # SQL questions (293)
data/enhanced_function_calling_ground_truth.json    # Analytical functions (166)
data/fcl_ground_truth.json                         # API functions (167)
```

### Performance Baselines

| Model | SQL Accuracy | Function Score |
|-------|-------------|----------------|
| GPT-4o | 49.5% | 20% |
| GPT-4 | 45% | 18% |
| Claude Sonnet | 47% | 19% |
| GPT-3.5 | 35% | 12% |

---

This comprehensive documentation provides both the extreme detail requested and clear, accessible explanations for understanding the USABench evaluation framework. The document now includes extensive examples, step-by-step explanations, troubleshooting guides, and complete reference materials while maintaining readability through clear organization and plain language explanations.