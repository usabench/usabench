"""
Binary SQL Metrics - Production-tested evaluation from usafacts_eval_v2
Direct copy of Text2SQLEvaluator from binary_evaluation_pipeline.py
"""

from dataclasses import dataclass
import difflib
import re
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Union


@dataclass
class BinaryEvaluationResult:
    """Result from binary SQL evaluation."""
    overall_pass: bool
    overall_score: float
    component_scores: Dict[str, Dict[str, Union[bool, float, str]]]
    execution_accuracy_score: float
    result_correctness_score: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class Text2SQLEvaluator:
    """
    Production Text2SQL evaluator from usafacts_eval_v2.
    Implements deterministic pass/fail evaluation with binary metrics.
    Thread-safe with connection pooling per thread.
    """

    def __init__(self, db_path: str):
        """Initialize with database path.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        # Thread-local storage for connections
        self._local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection.

        Reuses connections within the same thread for better performance.
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
        return self._local.connection

    def _get_connection_with_row_factory(self) -> sqlite3.Connection:
        """Get a thread-local database connection with row factory.

        Reuses connections within the same thread for better performance.
        """
        if not hasattr(self._local, 'connection_row') or self._local.connection_row is None:
            self._local.connection_row = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection_row.row_factory = sqlite3.Row
        return self._local.connection_row

    def evaluate_binary_correctness(
        self,
        candidate_sql: str,
        expected_sql: str,
        question: str,
        expected_results: Optional[List[Dict]] = None
    ) -> BinaryEvaluationResult:
        """
        Evaluate SQL with binary pass/fail criteria.
        
        Args:
            candidate_sql: Generated SQL query
            expected_sql: Expected SQL query (for reference)
            question: Original question
            expected_results: Expected query results
            
        Returns:
            BinaryEvaluationResult with component scores
        """
        # Initialize component scores
        components = {
            'execution_accuracy': {'pass': False, 'score': 0.0, 'details': ''},
            'result_correctness': {'pass': False, 'score': 0.0, 'details': ''}
        }

        error_details = None

        try:
            # 1. Execution Accuracy Test (threshold: 0.8)
            execution_result = self._test_execution(candidate_sql)
            components['execution_accuracy'] = execution_result

            if execution_result['pass']:
                # 2. Result Correctness Test (threshold: 0.9)
                if expected_results:
                    result_result = self._test_result_correctness(
                        candidate_sql,
                        expected_results
                    )
                    components['result_correctness'] = result_result
                else:
                    # If no expected results, just check if query returns data
                    components['result_correctness'] = {
                        'pass': True,
                        'score': 1.0,
                        'details': 'Query executed and returned results'
                    }

        except Exception as e:
            error_details = str(e)
            components['execution_accuracy']['details'] = f"Evaluation error: {str(e)}"

        # Calculate overall score and pass/fail
        execution_score = components['execution_accuracy']['score']
        result_score = components['result_correctness']['score']

        # Binary thresholds from usafacts_eval_v2
        execution_passes = execution_score >= 0.8
        result_passes = result_score >= 0.9

        # Overall pass requires both components to pass
        overall_pass = execution_passes and result_passes
        overall_score = (execution_score * 0.4 + result_score * 0.6)  # Weighted average

        return BinaryEvaluationResult(
            overall_pass=overall_pass,
            overall_score=overall_score,
            component_scores=components,
            execution_accuracy_score=execution_score,
            result_correctness_score=result_score,
            error=error_details,
            details={
                'generated_sql': candidate_sql,
                'expected_sql': expected_sql,
                'question': question
            }
        )

    def _test_execution(self, candidate_sql: str) -> Dict[str, Union[bool, float, str]]:
        """Test if SQL executes without errors."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Clean and prepare SQL
            clean_sql = self._clean_sql(candidate_sql)

            # Execute query
            cursor.execute(clean_sql)
            cursor.fetchall()  # Consume results

            return {
                'pass': True,
                'score': 1.0,
                'details': 'SQL executed successfully'
            }

        except sqlite3.Error as e:
            return {
                'pass': False,
                'score': 0.0,
                'details': f'SQL execution failed: {str(e)}'
            }
        except Exception as e:
            return {
                'pass': False,
                'score': 0.0,
                'details': f'Unexpected error: {str(e)}'
            }

    def _test_result_correctness(
        self,
        candidate_sql: str,
        expected_results: List[Dict]
    ) -> Dict[str, Union[bool, float, str]]:
        """Test if query results match expected results."""
        try:
            conn = self._get_connection_with_row_factory()
            cursor = conn.cursor()

            # Execute candidate SQL
            clean_sql = self._clean_sql(candidate_sql)
            cursor.execute(clean_sql)
            candidate_rows = cursor.fetchall()
            candidate_result = [dict(row) for row in candidate_rows]

            # Compare results (values only, not column names)
            similarity_score = self._compare_results(candidate_result, expected_results)

            # Pass if similarity >= 0.9 (90% match)
            passes = similarity_score >= 0.9

            return {
                'pass': passes,
                'score': similarity_score,
                'details': f'Result similarity: {similarity_score:.2f} (threshold: 0.9)'
            }

        except Exception as e:
            return {
                'pass': False,
                'score': 0.0,
                'details': f'Result comparison failed: {str(e)}'
            }

    def _clean_sql(self, sql: str) -> str:
        """Clean SQL query for execution."""
        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'```\s*', '', sql)

        # Remove comments
        sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

        # Clean whitespace
        sql = ' '.join(sql.split())

        return sql.strip()

    def _compare_results(
        self,
        candidate: List[Dict],
        expected: List[Dict]
    ) -> float:
        """Compare query results based on values only."""
        if not expected and not candidate:
            return 1.0

        if not expected or not candidate:
            return 0.0

        # Extract values only (ignore column names)
        candidate_values = []
        for row in candidate:
            candidate_values.append(tuple(sorted(str(v) for v in row.values())))

        expected_values = []
        for row in expected:
            expected_values.append(tuple(sorted(str(v) for v in row.values())))

        # Sort for comparison
        candidate_values.sort()
        expected_values.sort()

        # Calculate similarity
        if candidate_values == expected_values:
            return 1.0

        # Use sequence matcher for partial credit
        matcher = difflib.SequenceMatcher(None, candidate_values, expected_values)
        return matcher.ratio()
