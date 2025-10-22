from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


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


class BaseEvaluator(ABC):
    """Base evaluator class implementing template method pattern."""

    def __init__(self, config: EvaluationConfig):
        self.config = config

    def evaluate_batch(self, samples: List[UnifiedSample]) -> List[EvaluationResult]:
        """Evaluate a batch of samples."""
        results = []
        for sample in samples:
            result = self.evaluate_single(sample)
            results.append(result)
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
