import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Difficulty, EvaluationType, UnifiedSample


class DataLoader:
    """Enhanced data loader for ground truth datasets."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.sql_ground_truth_file = self.data_dir / "text2sql_ground_truth.json"
        self.function_ground_truth_file = self.data_dir / "enhanced_function_calling_ground_truth.json"
        self.function_eval_file = self.data_dir / "fcl_ground_truth.json"

    def load_sql_samples(
        self,
        max_samples: Optional[int] = None,
        difficulty_filter: Optional[List[Difficulty]] = None
    ) -> List[UnifiedSample]:
        """Load SQL evaluation samples from ground truth."""
        if not self.sql_ground_truth_file.exists():
            raise FileNotFoundError(f"SQL ground truth file not found: {self.sql_ground_truth_file}")

        with open(self.sql_ground_truth_file) as f:
            data = json.load(f)

        # Handle different JSON structures
        questions = data.get("questions", data.get("ground_truth_data", []))

        samples = []
        for i, item in enumerate(questions):
            if max_samples and len(samples) >= max_samples:
                break

            # Map difficulty
            difficulty_mapping = {
                "easy": Difficulty.EASY,
                "medium": Difficulty.MEDIUM,
                "hard": Difficulty.HARD
            }

            difficulty = difficulty_mapping.get(
                item.get("difficulty", "medium").lower(),
                Difficulty.MEDIUM
            )

            # Apply difficulty filter
            if difficulty_filter and difficulty not in difficulty_filter:
                continue

            sample = UnifiedSample(
                id=item.get("question_id", f"sql_{i}"),
                question=item.get("question_text", item.get("question", "")),
                evaluation_type=EvaluationType.SQL,
                difficulty=difficulty,
                ground_truth_sql=item.get("reference_sql", item.get("ground_truth_sql", item.get("sql", ""))),
                context=item.get("context"),
                metadata={
                    "category": item.get("category"),
                    "complexity": item.get("complexity"),
                    "expected_result": item.get("expected_result"),
                    "source": "comprehensive_parallel_ground_truth"
                }
            )
            samples.append(sample)

        return samples

    def load_function_samples(
        self,
        max_samples: Optional[int] = None,
        difficulty_filter: Optional[List[Difficulty]] = None
    ) -> List[UnifiedSample]:
        """Load function calling evaluation samples from ground truth."""
        if not self.function_ground_truth_file.exists():
            raise FileNotFoundError(f"Function ground truth file not found: {self.function_ground_truth_file}")

        with open(self.function_ground_truth_file) as f:
            data = json.load(f)

        # Handle different JSON structures
        questions = data.get("questions", data.get("ground_truth_data", []))

        samples = []
        for i, item in enumerate(questions):
            if max_samples and len(samples) >= max_samples:
                break

            # Map difficulty
            difficulty_mapping = {
                "easy": Difficulty.EASY,
                "medium": Difficulty.MEDIUM,
                "hard": Difficulty.HARD
            }

            difficulty = difficulty_mapping.get(
                item.get("difficulty", "medium").lower(),
                Difficulty.MEDIUM
            )

            # Apply difficulty filter
            if difficulty_filter and difficulty not in difficulty_filter:
                continue

            # Convert function_sequence to ground_truth_functions format
            ground_truth_functions = []
            if "function_sequence" in item:
                for func in item["function_sequence"]:
                    ground_truth_functions.append({
                        "name": func.get("function_name"),
                        "arguments": func.get("parameters", {})
                    })
            else:
                ground_truth_functions = item.get("ground_truth_functions", [])

            sample = UnifiedSample(
                id=item.get("question_id", f"func_{i}"),
                question=item.get("question_text", item.get("question", "")),
                evaluation_type=EvaluationType.FUNCTION,
                difficulty=difficulty,
                ground_truth_functions=ground_truth_functions,
                available_functions=data.get("available_functions", item.get("available_functions", [])),
                context=item.get("context"),
                metadata={
                    "category": item.get("category"),
                    "workflow_type": item.get("workflow_type"),
                    "source": "enhanced_function_calling_ground_truth"
                }
            )
            samples.append(sample)

        return samples

    def load_mixed_samples(
        self,
        sql_count: Optional[int] = None,
        function_count: Optional[int] = None,
        difficulty_filter: Optional[List[Difficulty]] = None
    ) -> List[UnifiedSample]:
        """Load mixed SQL and function calling samples."""
        samples = []

        if sql_count is None or sql_count > 0:
            sql_samples = self.load_sql_samples(
                max_samples=sql_count,
                difficulty_filter=difficulty_filter
            )
            samples.extend(sql_samples)

        if function_count is None or function_count > 0:
            function_samples = self.load_function_samples(
                max_samples=function_count,
                difficulty_filter=difficulty_filter
            )
            samples.extend(function_samples)

        return samples

    def load_function_eval_samples(
        self,
        max_samples: Optional[int] = None,
        difficulty_filter: Optional[List[Difficulty]] = None
    ) -> List[UnifiedSample]:
        """Load function calling evaluation samples."""
        if not self.function_eval_file.exists():
            raise FileNotFoundError(f"Function eval ground truth file not found: {self.function_eval_file}")

        with open(self.function_eval_file) as f:
            data = json.load(f)

        questions = data.get("questions", [])

        samples = []
        for i, item in enumerate(questions):
            if max_samples and len(samples) >= max_samples:
                break

            # Map difficulty if available
            difficulty_str = item.get("difficulty", "medium")
            if isinstance(difficulty_str, str):
                difficulty_mapping = {
                    "easy": Difficulty.EASY,
                    "medium": Difficulty.MEDIUM,
                    "hard": Difficulty.HARD
                }
                difficulty = difficulty_mapping.get(difficulty_str.lower(), Difficulty.MEDIUM)
            else:
                difficulty = Difficulty.MEDIUM

            # Apply difficulty filter
            if difficulty_filter and difficulty not in difficulty_filter:
                continue

            # Convert expected_functions to ground_truth_functions format
            ground_truth_functions = []
            for func in item.get("expected_functions", []):
                ground_truth_functions.append({
                    "name": func.get("function_name"),
                    "arguments": func.get("parameters", {})
                })

            sample = UnifiedSample(
                id=f"fcl_{item.get('question_id', i)}",
                question=item.get("question", ""),
                evaluation_type=EvaluationType.FUNCTION,
                difficulty=difficulty,
                ground_truth_functions=ground_truth_functions,
                available_functions=[],  # Function eval has predefined functions
                context=item.get("context"),
                metadata={
                    "ground_truth_results": item.get("ground_truth_results"),
                    "category": item.get("category", "discovery"),
                    "source": "function_eval"
                }
            )
            samples.append(sample)

        return samples

    def get_dataset_info(self) -> Dict[str, Any]:
        """Get information about available datasets."""
        info = {}

        # SQL dataset info
        if self.sql_ground_truth_file.exists():
            with open(self.sql_ground_truth_file) as f:
                sql_data = json.load(f)
                sql_questions = sql_data.get("questions", sql_data.get("ground_truth_data", []))
                info["sql"] = {
                    "total_questions": len(sql_questions),
                    "file": str(self.sql_ground_truth_file)
                }

        # Function dataset info
        if self.function_ground_truth_file.exists():
            with open(self.function_ground_truth_file) as f:
                func_data = json.load(f)
                func_questions = func_data.get("questions", func_data.get("ground_truth_data", []))
                info["function"] = {
                    "total_questions": len(func_questions),
                    "file": str(self.function_ground_truth_file)
                }

        # Function eval dataset info
        if self.function_eval_file.exists():
            with open(self.function_eval_file) as f:
                fcl_data = json.load(f)
                fcl_questions = fcl_data.get("questions", [])
                info["function_eval"] = {
                    "total_questions": len(fcl_questions),
                    "file": str(self.function_eval_file)
                }

        return info
