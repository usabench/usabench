from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, Optional

from USABench.core.base import BaseEvaluator, EvaluationConfig, UnifiedSample
from USABench.core.client import LLMClient


class DatabaseValidationStrategy:
    """Validation strategy that executes SQL against actual database."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

    def validate(
        self,
        sample: UnifiedSample,
        model_response: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """Validate SQL by executing against database."""
        validation_details = {}

        try:
            # Extract SQL from model response
            predicted_sql = self._extract_sql(model_response)
            validation_details["predicted_sql"] = predicted_sql

            if not predicted_sql:
                return False, 0.0, {
                    **validation_details,
                    "error": "No SQL found in response"
                }

            # Execute predicted SQL
            predicted_result = self._execute_sql(predicted_sql)
            validation_details["predicted_result"] = predicted_result

            # Execute ground truth SQL if available
            ground_truth_result = None
            if sample.ground_truth_sql:
                ground_truth_result = self._execute_sql(sample.ground_truth_sql)
                validation_details["ground_truth_result"] = ground_truth_result

            # Compare results
            if ground_truth_result is not None:
                is_correct = self._compare_results(predicted_result, ground_truth_result)
                score = 1.0 if is_correct else 0.0
            else:
                # If no ground truth SQL, just check if execution was successful
                is_correct = predicted_result is not None
                score = 1.0 if is_correct else 0.0

            validation_details["comparison_method"] = "database_execution"
            return is_correct, score, validation_details

        except Exception as e:
            return False, 0.0, {
                **validation_details,
                "error": str(e),
                "comparison_method": "database_execution"
            }

    def _extract_sql(self, response: str) -> Optional[str]:
        """Extract SQL query from model response."""
        # Look for SQL in code blocks
        sql_pattern = r'```sql\s*(.*?)\s*```'
        match = re.search(sql_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Look for SQL in generic code blocks
        code_pattern = r'```\s*(.*?)\s*```'
        match = re.search(code_pattern, response, re.DOTALL)
        if match:
            sql_candidate = match.group(1).strip()
            # Basic check if it looks like SQL
            if any(keyword in sql_candidate.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                return sql_candidate

        # Look for SQL keywords directly in response
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if any(line.upper().startswith(keyword) for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                return line

        return None

    def _execute_sql(self, sql: str) -> Any:
        """Execute SQL query against database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)

                # For SELECT queries, fetch results
                if sql.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    return results
                else:
                    # For other queries, return number of affected rows
                    return cursor.rowcount

        except Exception as e:
            raise RuntimeError(f"SQL execution failed: {str(e)}")

    def _compare_results(self, predicted: Any, expected: Any) -> bool:
        """Compare query results."""
        if predicted is None and expected is None:
            return True
        if predicted is None or expected is None:
            return False

        # For list results (SELECT queries)
        if isinstance(predicted, list) and isinstance(expected, list):
            return predicted == expected

        # For scalar results
        return predicted == expected


class SQLEvaluator(BaseEvaluator):
    """SQL evaluation with database validation."""

    def __init__(self, config: EvaluationConfig, db_path: str = "data/usafacts.db"):
        super().__init__(config)
        self.client = LLMClient(model=config.model_name, **config.__dict__)
        self.validation_strategy = DatabaseValidationStrategy(db_path)

    def _generate_response(self, sample: UnifiedSample) -> str:
        """Generate SQL query using LLM."""
        system_message = """You are a SQL expert. Given a natural language question about economic data, write a precise SQL query to answer it.

Rules:
1. Only return the SQL query, no explanations
2. Use proper SQL syntax for SQLite
3. The database contains tables with economic data from BLS, BEA, and OMB
4. Format your response with the SQL query in a code block

Available tables and their schemas will be provided in the question context."""

        user_message = f"""Question: {sample.question}

Context: {sample.context or "No additional context provided"}

Write a SQL query to answer this question."""

        return self.client.generate_with_system(
            user_message=user_message,
            system_message=system_message,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

    def _validate_response(
        self,
        sample: UnifiedSample,
        model_response: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """Validate SQL response against database."""
        return self.validation_strategy.validate(sample, model_response)
