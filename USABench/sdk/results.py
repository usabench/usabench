from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from USABench.core.base import EvaluationResult


class ResultsAnalyzer:
    """Analyzer for evaluation results with comprehensive metrics."""

    def __init__(self, results: List[EvaluationResult]):
        self.results = results
        self.df = self._results_to_dataframe()

    def _results_to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame for analysis."""
        data = []
        for result in self.results:
            data.append({
                'sample_id': result.sample_id,
                'question': result.question,
                'evaluation_type': result.evaluation_type.value,
                'difficulty': result.difficulty.value,
                'model_response': result.model_response,
                'is_correct': result.is_correct,
                'score': result.score,
                'execution_time': result.execution_time,
                'error_message': result.error_message,
                'timestamp': result.timestamp
            })
        return pd.DataFrame(data)

    def get_overall_metrics(self) -> Dict[str, Any]:
        """Calculate overall performance metrics."""
        if self.df.empty:
            return {}

        total_samples = len(self.df)
        correct_samples = self.df['is_correct'].sum()

        return {
            'total_samples': total_samples,
            'correct_samples': int(correct_samples),
            'accuracy': correct_samples / total_samples if total_samples > 0 else 0.0,
            'average_score': float(self.df['score'].mean()),
            'average_execution_time': float(self.df['execution_time'].mean()),
            'error_rate': float((self.df['error_message'].notna()).sum() / total_samples) if total_samples > 0 else 0.0
        }

    def get_metrics_by_type(self) -> Dict[str, Dict[str, Any]]:
        """Calculate metrics grouped by evaluation type."""
        metrics = {}

        for eval_type in self.df['evaluation_type'].unique():
            type_df = self.df[self.df['evaluation_type'] == eval_type]

            total = len(type_df)
            correct = type_df['is_correct'].sum()

            metrics[eval_type] = {
                'total_samples': total,
                'correct_samples': int(correct),
                'accuracy': correct / total if total > 0 else 0.0,
                'average_score': float(type_df['score'].mean()),
                'average_execution_time': float(type_df['execution_time'].mean()),
                'error_rate': float((type_df['error_message'].notna()).sum() / total) if total > 0 else 0.0
            }

        return metrics

    def get_metrics_by_difficulty(self) -> Dict[str, Dict[str, Any]]:
        """Calculate metrics grouped by difficulty level."""
        metrics = {}

        for difficulty in self.df['difficulty'].unique():
            diff_df = self.df[self.df['difficulty'] == difficulty]

            total = len(diff_df)
            correct = diff_df['is_correct'].sum()

            metrics[difficulty] = {
                'total_samples': total,
                'correct_samples': int(correct),
                'accuracy': correct / total if total > 0 else 0.0,
                'average_score': float(diff_df['score'].mean()),
                'average_execution_time': float(diff_df['execution_time'].mean()),
                'error_rate': float((diff_df['error_message'].notna()).sum() / total) if total > 0 else 0.0
            }

        return metrics

    def get_detailed_breakdown(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get detailed breakdown by type and difficulty."""
        breakdown = defaultdict(lambda: defaultdict(dict))

        for eval_type in self.df['evaluation_type'].unique():
            for difficulty in self.df['difficulty'].unique():
                subset_df = self.df[
                    (self.df['evaluation_type'] == eval_type) &
                    (self.df['difficulty'] == difficulty)
                ]

                if len(subset_df) > 0:
                    total = len(subset_df)
                    correct = subset_df['is_correct'].sum()

                    breakdown[eval_type][difficulty] = {
                        'total_samples': total,
                        'correct_samples': int(correct),
                        'accuracy': correct / total,
                        'average_score': float(subset_df['score'].mean()),
                        'average_execution_time': float(subset_df['execution_time'].mean())
                    }

        return dict(breakdown)

    def get_error_analysis(self) -> Dict[str, Any]:
        """Analyze errors and failure patterns."""
        error_df = self.df[self.df['error_message'].notna()]

        if error_df.empty:
            return {'total_errors': 0, 'error_patterns': {}}

        # Group errors by type and difficulty
        error_patterns = defaultdict(lambda: defaultdict(list))

        for _, row in error_df.iterrows():
            error_patterns[row['evaluation_type']][row['difficulty']].append(row['error_message'])

        return {
            'total_errors': len(error_df),
            'error_rate_by_type': {
                eval_type: float((self.df[self.df['evaluation_type'] == eval_type]['error_message'].notna()).sum() /
                               len(self.df[self.df['evaluation_type'] == eval_type]))
                for eval_type in self.df['evaluation_type'].unique()
            },
            'error_patterns': dict(error_patterns)
        }

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """Generate comprehensive evaluation report."""
        report_lines = []
        report_lines.append("# USABench Evaluation Report")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # Overall metrics
        overall = self.get_overall_metrics()
        report_lines.append("## Overall Performance")
        report_lines.append(f"- Total Samples: {overall.get('total_samples', 0)}")
        report_lines.append(f"- Correct Samples: {overall.get('correct_samples', 0)}")
        report_lines.append(f"- Overall Accuracy: {overall.get('accuracy', 0):.2%}")
        report_lines.append(f"- Average Score: {overall.get('average_score', 0):.3f}")
        report_lines.append(f"- Average Execution Time: {overall.get('average_execution_time', 0):.2f}s")
        report_lines.append(f"- Error Rate: {overall.get('error_rate', 0):.2%}")
        report_lines.append("")

        # Metrics by type
        by_type = self.get_metrics_by_type()
        report_lines.append("## Performance by Evaluation Type")
        for eval_type, metrics in by_type.items():
            report_lines.append(f"### {eval_type.upper()}")
            report_lines.append(f"- Samples: {metrics['total_samples']}")
            report_lines.append(f"- Accuracy: {metrics['accuracy']:.2%}")
            report_lines.append(f"- Average Score: {metrics['average_score']:.3f}")
            report_lines.append("")

        # Metrics by difficulty
        by_difficulty = self.get_metrics_by_difficulty()
        report_lines.append("## Performance by Difficulty")
        for difficulty, metrics in by_difficulty.items():
            report_lines.append(f"### {difficulty.upper()}")
            report_lines.append(f"- Samples: {metrics['total_samples']}")
            report_lines.append(f"- Accuracy: {metrics['accuracy']:.2%}")
            report_lines.append(f"- Average Score: {metrics['average_score']:.3f}")
            report_lines.append("")

        # Error analysis
        error_analysis = self.get_error_analysis()
        if error_analysis['total_errors'] > 0:
            report_lines.append("## Error Analysis")
            report_lines.append(f"- Total Errors: {error_analysis['total_errors']}")
            report_lines.append("- Error Rates by Type:")
            for eval_type, rate in error_analysis['error_rate_by_type'].items():
                report_lines.append(f"  - {eval_type}: {rate:.2%}")
            report_lines.append("")

        report_content = "\n".join(report_lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report_content)

        return report_content

    def save_results(self, output_dir: str, prefix: str = "evaluation"):
        """Save results in multiple formats."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_path = output_path / f"{prefix}_results_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump([
                {
                    'sample_id': r.sample_id,
                    'question': r.question,
                    'evaluation_type': r.evaluation_type.value,
                    'difficulty': r.difficulty.value,
                    'model_response': r.model_response,
                    'is_correct': r.is_correct,
                    'score': r.score,
                    'execution_time': r.execution_time,
                    'error_message': r.error_message,
                    'validation_details': r.validation_details,
                    'timestamp': r.timestamp.isoformat() if r.timestamp else None
                }
                for r in self.results
            ], f, indent=2)

        # Save CSV
        csv_path = output_path / f"{prefix}_results_{timestamp}.csv"
        self.df.to_csv(csv_path, index=False)

        # Save report
        report_path = output_path / f"{prefix}_report_{timestamp}.md"
        self.generate_report(str(report_path))

        return {
            'json_path': str(json_path),
            'csv_path': str(csv_path),
            'report_path': str(report_path)
        }
