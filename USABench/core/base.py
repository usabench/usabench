from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


class EvaluationType(Enum):
    SQL = "sql"
    FUNCTION = "function"


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class UnifiedSample:
    """Unified sample format for both SQL and function calling evaluations."""
    id: str
    question: str
    evaluation_type: EvaluationType
    difficulty: Difficulty
    context: Optional[str] = None

    # SQL-specific fields
    ground_truth_sql: Optional[str] = None
    ground_truth_result: Optional[Any] = None

    # Function calling specific fields
    ground_truth_functions: Optional[List[Dict[str, Any]]] = None
    available_functions: Optional[List[Dict[str, Any]]] = None

    # Common metadata
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvaluationResult:
    """Unified result format for evaluations."""
    sample_id: str
    question: str
    evaluation_type: EvaluationType
    difficulty: Difficulty

    # Model response
    model_response: str

    # Evaluation metrics
    is_correct: bool
    score: float

    # Detailed breakdown
    execution_result: Optional[Any] = None
    error_message: Optional[str] = None
    validation_details: Optional[Dict[str, Any]] = None

    # Timing
    execution_time: Optional[float] = None
    timestamp: Optional[datetime] = None

    # Additional context
    metadata: Optional[Dict[str, Any]] = None


class ValidationStrategy(Protocol):
    """Protocol for validation strategies."""

    def validate(
        self,
        sample: UnifiedSample,
        model_response: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """
        Validate model response against ground truth.
        
        Returns:
            tuple: (is_correct, score, validation_details)
        """
        ...


@dataclass
class EvaluationConfig:
    """Configuration for evaluation runs."""
    model_name: str = "gpt-4o"
    max_samples: Optional[int] = None
    difficulty_filter: Optional[List[Difficulty]] = None
    validation_strategy: Optional[str] = None
    timeout: int = 30
    temperature: float = 0.0
    max_tokens: int = 2000
    max_workers: int = 5  # Number of parallel workers for batch evaluation


class BaseEvaluator(ABC):
    """Base evaluator class implementing template method pattern."""

    def __init__(self, config: EvaluationConfig):
        self.config = config

    def evaluate_batch(
        self,
        samples: List[UnifiedSample],
        max_workers: Optional[int] = None,
        parallel: bool = True
    ) -> List[EvaluationResult]:
        """Evaluate a batch of samples with optional parallel execution.

        Args:
            samples: List of samples to evaluate.
            max_workers: Number of parallel workers. Defaults to config.max_workers.
            parallel: Whether to use parallel execution. Defaults to True.

        Returns:
            List of evaluation results in the same order as input samples.
        """
        if not parallel or len(samples) <= 1:
            # Sequential evaluation
            results = []
            for sample in samples:
                result = self.evaluate_single(sample)
                results.append(result)
            return results

        # Parallel evaluation with ThreadPoolExecutor
        workers = max_workers or self.config.max_workers
        results = [None] * len(samples)

        logger.info(f"Starting parallel evaluation of {len(samples)} samples with {workers} workers")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_idx = {
                executor.submit(self.evaluate_single, sample): idx
                for idx, sample in enumerate(samples)
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"Completed {completed}/{len(samples)} evaluations")
                except Exception as e:
                    # Handle any unexpected errors
                    sample = samples[idx]
                    logger.error(f"Evaluation failed for sample {sample.id}: {e}")
                    results[idx] = EvaluationResult(
                        sample_id=sample.id,
                        question=sample.question,
                        evaluation_type=sample.evaluation_type,
                        difficulty=sample.difficulty,
                        model_response="",
                        is_correct=False,
                        score=0.0,
                        error_message=f"Parallel execution error: {str(e)}",
                        timestamp=datetime.now()
                    )

        logger.info(f"Completed parallel evaluation of {len(samples)} samples")
        return results

    def evaluate_single(self, sample: UnifiedSample) -> EvaluationResult:
        """Template method for single sample evaluation."""
        start_time = datetime.now()

        try:
            # Generate model response
            model_response = self._generate_response(sample)

            # Validate response
            is_correct, score, validation_details = self._validate_response(sample, model_response)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            return EvaluationResult(
                sample_id=sample.id,
                question=sample.question,
                evaluation_type=sample.evaluation_type,
                difficulty=sample.difficulty,
                model_response=model_response,
                is_correct=is_correct,
                score=score,
                validation_details=validation_details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return EvaluationResult(
                sample_id=sample.id,
                question=sample.question,
                evaluation_type=sample.evaluation_type,
                difficulty=sample.difficulty,
                model_response="",
                is_correct=False,
                score=0.0,
                error_message=str(e),
                execution_time=execution_time,
                timestamp=datetime.now()
            )

    @abstractmethod
    def _generate_response(self, sample: UnifiedSample) -> str:
        """Generate model response for the sample."""
        pass

    @abstractmethod
    def _validate_response(
        self,
        sample: UnifiedSample,
        model_response: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """Validate model response against ground truth."""
        pass
