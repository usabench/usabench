"""Enhanced SQL evaluator with binary metrics and targeted schema support."""

from typing import Any, Dict, Optional

from USABench.core.base import BaseEvaluator, EvaluationConfig, UnifiedSample
from USABench.core.client import LLMClient
from USABench.metrics.binary_sql_metrics import Text2SQLEvaluator


class TargetedSchemaProvider:
    """Provides targeted schema based on question content."""

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
            'economic_indicators': """
TABLE: economic_indicators
COLUMNS: indicator_id, indicator_name, category, source, update_frequency, description
PURPOSE: Metadata about available economic indicators
EXAMPLE: SELECT DISTINCT indicator_name, category FROM economic_indicators WHERE source = 'BLS'
""",
            'gdp_by_industry': """
TABLE: gdp_by_industry
COLUMNS: record_id, industry_code, industry_name, year, quarter, gdp_contribution, percentage_of_total, unit, source
PURPOSE: Industry contributions to GDP over time
EXAMPLE: SELECT industry_name, SUM(gdp_contribution) as total_contribution FROM gdp_by_industry WHERE year = 2023 GROUP BY industry_name ORDER BY total_contribution DESC
"""
        }

    def get_targeted_schema(self, question: str) -> str:
        """Get targeted schema based on question content."""
        question_lower = question.lower()

        relevant_tables = []

        # Check for budget/spending related keywords
        if any(word in question_lower for word in ['outlays', 'spending', 'budget', 'defense', 'military', 'health', 'categories', 'functions', 'departments', 'federal']):
            relevant_tables.append('budget_outlays')

        # Check for economic indicator keywords
        if any(word in question_lower for word in ['cpi', 'consumer price', 'inflation', 'employment cost', 'workers', 'compensation', 'economic indicators', 'time periods', 'tracked', 'productivity']):
            relevant_tables.append('time_series_data')

        # Check for GDP/industry keywords
        if any(word in question_lower for word in ['gdp', 'industry', 'industries', 'contribution', 'economic sectors']):
            relevant_tables.append('industry_gdp')
            relevant_tables.append('gdp_by_industry')

        # Check for regional keywords
        if any(word in question_lower for word in ['state', 'states', 'regional', 'personal income', 'per capita', 'population']):
            relevant_tables.append('regional_data')

        # If no specific match, default to most relevant based on common patterns
        if not relevant_tables:
            if any(word in question_lower for word in ['top', 'highest', 'most', 'spending']):
                relevant_tables.append('budget_outlays')
            elif any(word in question_lower for word in ['trend', 'change', 'growth', 'decline']):
                relevant_tables.append('time_series_data')
            else:
                # Default to budget_outlays as it's most common
                relevant_tables.append('budget_outlays')

        # Build targeted schema
        schema_parts = []
        for table in relevant_tables:
            if table in self.schemas:
                schema_parts.append(self.schemas[table])

        # Add a brief overview if multiple tables
        if len(schema_parts) > 1:
            header = f"RELEVANT TABLES FOR YOUR QUERY ({len(schema_parts)} tables):\n\n"
            return header + "\n---\n".join(schema_parts)
        elif schema_parts:
            return schema_parts[0]
        else:
            # Fallback to budget_outlays
            return self.schemas['budget_outlays']


class EnhancedSQLEvaluator(BaseEvaluator):
    """Enhanced SQL evaluation with binary metrics and targeted schema."""

    def __init__(self, config: EvaluationConfig, db_path: str = "data/usafacts.db"):
        super().__init__(config)
        self.client = LLMClient(model=config.model_name, **config.__dict__)
        self.db_path = db_path
        self.binary_evaluator = Text2SQLEvaluator(db_path)
        self.schema_provider = TargetedSchemaProvider()

    def _generate_response(self, sample: UnifiedSample) -> str:
        """Generate SQL query using LLM with targeted schema."""
        # Get targeted schema based on question
        targeted_schema = self.schema_provider.get_targeted_schema(sample.question)

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Question: {sample.question}")
        logger.info(f"Selected schema: {targeted_schema[:200]}...")

        system_message = """You are a SQL expert. Generate a SQL query to answer the given question using the provided database schema.

Important guidelines:
- Use only the tables and columns described in the schema
- Write valid SQLite syntax
- Be precise and efficient
- Return only the SQL query without explanations"""

        user_message = f"""Question: {sample.question}

Database Schema:
{targeted_schema}

Generate the SQL query:"""

        response = self.client.generate_with_system(
            user_message=user_message,
            system_message=system_message,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        logger.info(f"Model response: {response[:200]}...")

        return response

    def _validate_response(
        self,
        sample: UnifiedSample,
        model_response: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """Validate SQL response using binary metrics."""
        # Extract SQL from model response
        sql = self._extract_sql(model_response)

        if not sql:
            return False, 0.0, {
                "error": "No SQL found in response",
                "model_response": model_response
            }

        # Use binary evaluator with correct method
        try:
            # Get expected results from metadata if available
            expected_results = sample.metadata.get('expected_result', []) if sample.metadata else []

            # Call the correct method
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
                    'execution_accuracy': evaluation_result.component_scores.get('execution_accuracy', {}),
                    'result_correctness': evaluation_result.component_scores.get('result_correctness', {}),
                    'targeted_schema_used': True,
                    'error_details': evaluation_result.error
                }
            )
        except Exception as e:
            return False, 0.0, {
                "error": str(e),
                "sql": sql
            }

    def _extract_sql(self, response: str) -> Optional[str]:
        """Extract SQL query from model response."""
        if not response:
            return None

        # Clean the response first
        sql = response.strip()

        # Look for SQL in code blocks (```sql or ```)
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        # Remove any trailing semicolons for consistency
        sql = sql.rstrip(';').strip()

        # Basic validation - check if it looks like SQL
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        if sql and any(keyword in sql.upper() for keyword in sql_keywords):
            return sql

        # If no SQL found yet, try to find SQL keywords directly
        lines = response.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if any(line.upper().startswith(keyword) for keyword in sql_keywords):
                # Collect all lines that look like SQL
                sql_lines = []
                for j in range(i, len(lines)):
                    curr_line = lines[j].strip()
                    if curr_line:
                        sql_lines.append(curr_line)
                        if ';' in curr_line:
                            break
                    elif sql_lines:  # Stop at empty line after SQL started
                        break
                return ' '.join(sql_lines).rstrip(';').strip()

        return None
