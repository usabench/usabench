from dataclasses import dataclass
from typing import List, Optional

from USABench.core.base import Difficulty


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark evaluation runs."""

    # Model configuration
    model_name: str = "gpt-4o"
    temperature: float = 0.0
    max_tokens: int = 2000
    timeout: int = 30

    # Dataset configuration
    data_dir: str = "data"
    sql_samples: Optional[int] = None
    function_samples: Optional[int] = None
    difficulty_filter: Optional[List[Difficulty]] = None

    # Database configuration
    db_path: str = "data/usafacts.db"

    # Output configuration
    output_dir: str = "results"
    save_results: bool = True
    generate_report: bool = True

    # Execution configuration
    parallel: bool = False
    batch_size: int = 10

    def to_evaluation_config(self):
        """Convert to core EvaluationConfig."""
        from core.base import EvaluationConfig
        return EvaluationConfig(
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            difficulty_filter=self.difficulty_filter
        )
