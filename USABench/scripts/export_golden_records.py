"""Export consolidated golden records to CSV.

This script combines SQL and function calling ground truth data into a single CSV
file with 459 total records (293 SQL + 166 Function Calling).

Note: This uses mock_fcl_ground_truth.json (abstract functions) for human-readable
exports. The benchmark evaluations use fcl_ground_truth.json (concrete BLS/BEA APIs).

Usage:
    python3 -m USABench.scripts.export_golden_records
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Any


class GoldenRecordExporter:
    """Export consolidated golden records to CSV."""

    def __init__(self, data_dir: str = "USABench/data"):
        self.data_dir = Path(data_dir)
        self.sql_file = self.data_dir / "text2sql_ground_truth.json"
        self.func_file = self.data_dir / "mock_fcl_ground_truth.json"
        self.output_file = self.data_dir / "golden_records_consolidated.csv"

    def infer_sql_difficulty(self, sql_query: str) -> str:
        """Infer difficulty from SQL complexity.

        Args:
            sql_query: SQL query string

        Returns:
            'easy', 'medium', or 'hard'
        """
        sql_lower = sql_query.lower()

        # Hard indicators
        hard_patterns = [
            'having', 'window', 'partition by', 'union', 'intersect',
            'except', 'with recursive', 'case when'
        ]
        if any(pattern in sql_lower for pattern in hard_patterns):
            return 'hard'

        # Count joins
        join_count = sql_lower.count(' join ')
        if join_count >= 2:
            return 'hard'

        # Check for subqueries (multiple SELECT statements)
        if sql_lower.count('select') > 1:
            return 'hard'

        # Medium indicators
        if 'group by' in sql_lower or join_count == 1:
            return 'medium'

        # Easy (simple queries)
        return 'easy'

    def extract_tables(self, sql_query: str) -> str:
        """Extract table names from SQL query.

        Args:
            sql_query: SQL query string

        Returns:
            Comma-separated list of table names
        """
        tables = []
        # Match FROM table_name and JOIN table_name patterns
        pattern = r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)'
        matches = re.findall(pattern, sql_query, re.IGNORECASE)

        for match in matches:
            # Extract non-empty groups from match tuple
            tables.extend([t for t in match if t])

        # Return unique tables, sorted
        return ','.join(sorted(set(tables))) if tables else ''

    def infer_sql_complexity(self, sql_query: str) -> str:
        """Infer workflow complexity from SQL patterns.

        Args:
            sql_query: SQL query string

        Returns:
            Workflow type: 'simple_query', 'aggregation', 'join_query', 'advanced', or 'set_operation'
        """
        sql_lower = sql_query.lower()

        # Advanced queries
        if 'having' in sql_lower or 'window' in sql_lower or 'case when' in sql_lower:
            return 'advanced'

        # Set operations
        if 'union' in sql_lower or 'intersect' in sql_lower or 'except' in sql_lower:
            return 'set_operation'

        # Joins
        if 'join' in sql_lower:
            return 'join_query'

        # Aggregations
        if 'group by' in sql_lower:
            return 'aggregation'

        # Simple queries
        return 'simple_query'

    def extract_function_names(self, function_sequence: List[Dict]) -> str:
        """Extract function names from function sequence.

        Args:
            function_sequence: List of function call dictionaries

        Returns:
            Comma-separated list of function names
        """
        if not function_sequence:
            return ''

        names = [f.get('function_name', '') for f in function_sequence]
        return ','.join(names)

    def process_sql_questions(self, sql_data: List[Dict]) -> List[Dict]:
        """Process SQL questions into CSV rows.

        Args:
            sql_data: List of SQL question dictionaries

        Returns:
            List of CSV row dictionaries
        """
        rows = []

        for q in sql_data:
            reference_sql = q.get('reference_sql', '')
            expected_result = q.get('expected_result', [])

            row = {
                'question_id': q['question_id'],
                'question_type': 'sql',
                'question_text': q['question_text'],
                'difficulty': self.infer_sql_difficulty(reference_sql),
                'primary_tables': self.extract_tables(reference_sql),
                'expected_output_rows': len(expected_result),
                'workflow_complexity': self.infer_sql_complexity(reference_sql),
                'generation_model': q.get('generation_model', ''),
                'generation_timestamp': q.get('generation_timestamp', ''),
                'reference_sql': reference_sql,
                'function_sequence': '',
                'expected_result_summary': q.get('expected_result_summary', ''),
                'success_criteria': ''
            }
            rows.append(row)

        return rows

    def process_function_questions(self, func_data: List[Dict]) -> List[Dict]:
        """Process function calling questions into CSV rows.

        Args:
            func_data: List of function calling question dictionaries

        Returns:
            List of CSV row dictionaries
        """
        rows = []

        for q in func_data:
            function_sequence = q.get('function_sequence', [])
            success_criteria = q.get('success_criteria', [])

            row = {
                'question_id': q['question_id'],
                'question_type': 'function',
                'question_text': q['question_text'],
                'difficulty': q.get('difficulty', 'medium'),
                'primary_tables': self.extract_function_names(function_sequence),
                'expected_output_rows': len(function_sequence),
                'workflow_complexity': q.get('workflow_type', 'single'),
                'generation_model': q.get('generation_method', ''),
                'generation_timestamp': '',
                'reference_sql': '',
                'function_sequence': json.dumps(function_sequence),
                'expected_result_summary': '',
                'success_criteria': ','.join(success_criteria) if isinstance(success_criteria, list) else success_criteria
            }
            rows.append(row)

        return rows

    def export(self) -> None:
        """Main export function."""
        print("Loading ground truth data...")

        # Load SQL data
        with open(self.sql_file, 'r', encoding='utf-8') as f:
            sql_json = json.load(f)
            sql_data = sql_json['ground_truth_data']

        # Load function data
        with open(self.func_file, 'r', encoding='utf-8') as f:
            func_json = json.load(f)
            func_data = func_json['ground_truth_data']

        print(f"Processing {len(sql_data)} SQL questions...")
        sql_rows = self.process_sql_questions(sql_data)

        print(f"Processing {len(func_data)} function calling questions...")
        func_rows = self.process_function_questions(func_data)

        # Merge and sort by question_id
        all_rows = sql_rows + func_rows
        all_rows.sort(key=lambda x: x['question_id'])

        # Export to CSV
        print(f"Exporting {len(all_rows)} records to {self.output_file}...")

        fieldnames = [
            'question_id', 'question_type', 'question_text', 'difficulty',
            'primary_tables', 'expected_output_rows', 'workflow_complexity',
            'generation_model', 'generation_timestamp',
            'reference_sql', 'function_sequence',
            'expected_result_summary', 'success_criteria'
        ]

        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"\n✓ Successfully exported to {self.output_file}")
        print(f"  Total records: {len(all_rows)}")
        print(f"  SQL questions: {len(sql_rows)}")
        print(f"  Function questions: {len(func_rows)}")

        # Print difficulty distribution
        print("\nDifficulty distribution:")
        sql_diff_counts = {}
        func_diff_counts = {}

        for row in sql_rows:
            diff = row['difficulty']
            sql_diff_counts[diff] = sql_diff_counts.get(diff, 0) + 1

        for row in func_rows:
            diff = row['difficulty']
            func_diff_counts[diff] = func_diff_counts.get(diff, 0) + 1

        print("\n  SQL questions:")
        for diff in ['easy', 'medium', 'hard']:
            count = sql_diff_counts.get(diff, 0)
            print(f"    {diff}: {count}")

        print("\n  Function questions:")
        for diff in ['easy', 'medium', 'hard']:
            count = func_diff_counts.get(diff, 0)
            print(f"    {diff}: {count}")


def main():
    """Main entry point."""
    exporter = GoldenRecordExporter()
    exporter.export()


if __name__ == "__main__":
    main()
