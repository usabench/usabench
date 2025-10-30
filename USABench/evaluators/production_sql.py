"""Production SQL evaluator that works correctly with schema targeting."""

import logging
from typing import Any, Dict, List, Optional

from USABench.core.base import BaseEvaluator, EvaluationConfig, UnifiedSample
from USABench.core.production_client import EvaluationPrompt, ProductionLLMClient
from USABench.metrics.binary_sql_metrics import Text2SQLEvaluator

logger = logging.getLogger(__name__)

class QuestionClassifier:
    """Simple question classifier to identify relevant tables."""

    def classify_question(self, question: str) -> List[str]:
        """Classify question to identify relevant tables."""
        question_lower = question.lower()
        relevant_tables = []

        # Budget/spending keywords
        if any(word in question_lower for word in [
            'outlays', 'spending', 'budget', 'defense', 'military',
            'health', 'categories', 'functions', 'departments', 'federal'
        ]):
            relevant_tables.append('budget_outlays')

        # Economic indicator keywords
        if any(word in question_lower for word in [
            'cpi', 'consumer price', 'inflation', 'employment cost',
            'workers', 'compensation', 'economic indicators', 'productivity'
        ]):
            relevant_tables.append('time_series_data')

        # GDP/industry keywords
        if any(word in question_lower for word in [
            'gdp', 'industry', 'industries', 'contribution', 'economic sectors'
        ]):
            relevant_tables.extend(['industry_gdp', 'gdp_by_industry'])

        # Regional keywords
        if any(word in question_lower for word in [
            'state', 'states', 'regional', 'personal income', 'per capita', 'population'
        ]):
            relevant_tables.append('regional_data')

        # Default to budget_outlays if no match
        if not relevant_tables:
            relevant_tables.append('budget_outlays')

        return relevant_tables

class ProductionSchemaProvider:
    """Production schema provider with targeted schemas."""

    def __init__(self):
        self.schemas = {
            'budget_outlays': """
TABLE: budget_outlays  
COLUMNS: record_id, superfunction, function_name, fiscal_year, outlay_amount, unit, source
PURPOSE: Government spending data by function and fiscal year
EXAMPLE: SELECT function_name, SUM(outlay_amount) AS total_outlays FROM budget_outlays WHERE fiscal_year >= 2020 GROUP BY function_name ORDER BY total_outlays DESC LIMIT 10
""",
            'time_series_data': """
TABLE: time_series_data
COLUMNS: record_id, series_id, indicator_id, source, category, subcategory, year, period_type, period_value, period_name, fiscal_calendar, geographic_level, geographic_code, geographic_name, raw_value, numeric_value, unit, unit_multiplier, is_estimated, footnotes
KEY CATEGORIES: 'consumer_price_index', 'employment_cost_index', 'productivity_measures'
PURPOSE: Economic indicators and time series data from BLS and BEA
EXAMPLE: SELECT year, numeric_value FROM time_series_data WHERE category = 'consumer_price_index' AND year BETWEEN 2020 AND 2023 ORDER BY year
""",
            'industry_gdp': """
TABLE: industry_gdp
COLUMNS: record_id, industry_code, industry_name, year, gdp_value, unit, unit_multiplier, source
PURPOSE: GDP contribution by industry over time
EXAMPLE: SELECT industry_name, gdp_value FROM industry_gdp WHERE year = 2023 ORDER BY gdp_value DESC LIMIT 10
""",
            'regional_data': """
TABLE: regional_data
COLUMNS: record_id, state_code, state_name, region, year, personal_income, per_capita_income, population, unit, source
PURPOSE: Regional economic data by state
EXAMPLE: SELECT state_name, personal_income FROM regional_data WHERE year = 2023 ORDER BY personal_income DESC LIMIT 10
""",
            'gdp_by_industry': """
TABLE: gdp_by_industry
COLUMNS: record_id, industry_code, industry_name, year, quarter, gdp_contribution, percentage_of_total, unit, source
PURPOSE: Industry contributions to GDP over time
EXAMPLE: SELECT industry_name, SUM(gdp_contribution) as total_contribution FROM gdp_by_industry WHERE year = 2023 GROUP BY industry_name ORDER BY total_contribution DESC
"""
        }

    def get_targeted_schema(self, table_names: List[str]) -> str:
        """Get schema for specific tables."""
        schema_parts = []
        for table in table_names:
            if table in self.schemas:
                schema_parts.append(self.schemas[table])

        if len(schema_parts) > 1:
            header = f"RELEVANT TABLES FOR YOUR QUERY ({len(schema_parts)} tables):\n\n"
            return header + "\n---\n".join(schema_parts)
        elif schema_parts:
            return schema_parts[0]
        else:
            # Fallback to budget_outlays
            return self.schemas['budget_outlays']

class ProductionSQLEvaluator(BaseEvaluator):
    """Production SQL evaluator that works correctly."""

    def __init__(self, config: EvaluationConfig, db_path: str = "data/usafacts.db"):
        super().__init__(config)
        self.db_path = db_path

        # Initialize production components
        self.client = ProductionLLMClient(
            default_model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )

        self.classifier = QuestionClassifier()
        self.schema_provider = ProductionSchemaProvider()
        self.binary_evaluator = Text2SQLEvaluator(db_path)

        logger.info(f"Initialized ProductionSQLEvaluator with {config.model_name}")

    def _generate_response(self, sample: UnifiedSample) -> str:
        """Generate SQL using production approach."""
        # Step 1: Classify question to identify relevant tables
        relevant_tables = self.classifier.classify_question(sample.question)
        logger.info(f"Classified question to use tables: {relevant_tables}")

        # Step 2: Get targeted schema for those tables
        targeted_schema = self.schema_provider.get_targeted_schema(relevant_tables)
        logger.info(f"Using targeted schema with {len(targeted_schema)} characters")

        # Step 3: Generate SQL with clean prompt
        system_message = """You are a SQL expert. Generate a SQL query to answer the given question using the provided database schema.

IMPORTANT: All government data is limited to years 2014-2024 only.
If asked for data outside this range, explain that data is not available.

Important guidelines:
- Use only the tables and columns described in the schema
- Data covers 2014-2024 only
- Write valid SQLite syntax
- Be precise and efficient
- Return only the SQL query without explanations"""

        user_message = f"""Question: {sample.question}

Database Schema:
{targeted_schema}

Generate the SQL query:"""

        prompt = EvaluationPrompt(
            system_message=system_message,
            user_message=user_message
        )

        # Step 4: Generate with production client
        logger.info(f"Generating SQL with {self.config.model_name}")
        response = self.client.generate(prompt, model=self.config.model_name)

        if response.error:
            logger.error(f"Generation error: {response.error}")
            return f"-- Error: {response.error}"

        logger.info(f"Generated response: {response.content[:100]}...")
        return response.content

    def _validate_response(
        self,
        sample: UnifiedSample,
        model_response: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """Validate SQL response using production binary metrics."""
        # Extract SQL from response
        sql = self._extract_sql(model_response)

        if not sql:
            logger.warning("No SQL found in response")
            return False, 0.0, {
                "error": "No SQL found in response",
                "model_response": model_response[:200]
            }

        logger.info(f"Extracted SQL: {sql}")

        # Check table usage for debugging
        if "budget_outlays" in sql:
            logger.info("✅ SUCCESS: Generated SQL uses correct 'budget_outlays' table")
        elif any(table in sql for table in ["government_spending", "budget_data"]):
            logger.warning("❌ WARNING: Generated SQL uses incorrect table name")

        try:
            # Use binary evaluator
            expected_results = sample.metadata.get('expected_result', []) if sample.metadata else []

            evaluation_result = self.binary_evaluator.evaluate_binary_correctness(
                candidate_sql=sql,
                expected_sql=sample.ground_truth_sql or "",
                question=sample.question,
                expected_results=expected_results
            )

            return (
                evaluation_result.overall_pass,
                evaluation_result.overall_score,
                {
                    'extracted_sql': sql,
                    'execution_accuracy': evaluation_result.component_scores.get('execution_accuracy', {}),
                    'result_correctness': evaluation_result.component_scores.get('result_correctness', {}),
                    'production_evaluator_used': True,
                    'error_details': evaluation_result.error
                }
            )
        except Exception as e:
            logger.error(f"Binary evaluation error: {e}")
            return False, 0.0, {
                "error": str(e),
                "sql": sql
            }

    def _extract_sql(self, response: str) -> Optional[str]:
        """Extract SQL from model response."""
        if not response:
            return None

        sql = response.strip()

        # Handle code blocks
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        # Remove trailing semicolons
        sql = sql.rstrip(';').strip()

        # Basic validation
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        if sql and any(keyword in sql.upper() for keyword in sql_keywords):
            return sql

        # Try to find SQL in response
        lines = response.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if any(line.upper().startswith(keyword) for keyword in sql_keywords):
                sql_lines = [line]
                for j in range(i+1, len(lines)):
                    curr_line = lines[j].strip()
                    if curr_line:
                        sql_lines.append(curr_line)
                        if ';' in curr_line:
                            break
                    elif sql_lines:
                        break
                return ' '.join(sql_lines).rstrip(';').strip()

        return None
