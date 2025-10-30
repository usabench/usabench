import json
import re
from typing import Any, Dict, List

from USABench.core.base import BaseEvaluator, EvaluationConfig, UnifiedSample
from USABench.core.client import LLMClient


class FunctionCallValidationStrategy:
    """Validation strategy for function calling evaluation."""

    def validate(
        self,
        sample: UnifiedSample,
        model_response: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """Validate function calling response."""
        validation_details = {}

        try:
            # Extract function calls from response
            predicted_calls = self._extract_function_calls(model_response)
            validation_details["predicted_calls"] = predicted_calls

            # Get ground truth calls
            ground_truth_calls = sample.ground_truth_functions or []
            validation_details["ground_truth_calls"] = ground_truth_calls

            # Compare function calls
            is_correct, score = self._compare_function_calls(
                predicted_calls,
                ground_truth_calls
            )

            validation_details["comparison_method"] = "function_call_matching"
            validation_details["exact_match"] = is_correct
            validation_details["similarity_score"] = score

            return is_correct, score, validation_details

        except Exception as e:
            return False, 0.0, {
                **validation_details,
                "error": str(e),
                "comparison_method": "function_call_matching"
            }

    def _extract_function_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract function calls from model response."""
        function_calls = []

        # Look for JSON function call patterns
        json_pattern = r'\{[^{}]*"name"[^{}]*"arguments"[^{}]*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)

        for match in matches:
            try:
                call_data = json.loads(match)
                if "name" in call_data:
                    function_calls.append(call_data)
            except json.JSONDecodeError:
                continue

        # Look for function call patterns like function_name(arg1=value1, arg2=value2)
        func_pattern = r'(\w+)\((.*?)\)'
        func_matches = re.findall(func_pattern, response)

        for func_name, args_str in func_matches:
            try:
                # Parse arguments
                args = {}
                if args_str.strip():
                    # Simple argument parsing (handles key=value format)
                    arg_pairs = [arg.strip() for arg in args_str.split(',')]
                    for pair in arg_pairs:
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            args[key] = value

                function_calls.append({
                    "name": func_name,
                    "arguments": args
                })
            except:
                continue

        return function_calls

    def _compare_function_calls(
        self,
        predicted: List[Dict[str, Any]],
        expected: List[Dict[str, Any]]
    ) -> tuple[bool, float]:
        """Compare predicted function calls with expected ones."""
        if not expected:
            # If no ground truth, just check if any functions were called
            return len(predicted) > 0, 1.0 if len(predicted) > 0 else 0.0

        if not predicted:
            return False, 0.0

        # Check for exact match
        if len(predicted) != len(expected):
            return False, self._calculate_partial_score(predicted, expected)

        # Sort both lists by function name for comparison
        predicted_sorted = sorted(predicted, key=lambda x: x.get("name", ""))
        expected_sorted = sorted(expected, key=lambda x: x.get("name", ""))

        exact_match = True
        for pred, exp in zip(predicted_sorted, expected_sorted):
            if not self._function_calls_match(pred, exp):
                exact_match = False
                break

        if exact_match:
            return True, 1.0
        else:
            return False, self._calculate_partial_score(predicted, expected)

    def _function_calls_match(self, call1: Dict[str, Any], call2: Dict[str, Any]) -> bool:
        """Check if two function calls match exactly."""
        if call1.get("name") != call2.get("name"):
            return False

        args1 = call1.get("arguments", {})
        args2 = call2.get("arguments", {})

        return args1 == args2

    def _calculate_partial_score(
        self,
        predicted: List[Dict[str, Any]],
        expected: List[Dict[str, Any]]
    ) -> float:
        """Calculate partial score based on similarity."""
        if not expected:
            return 0.0

        total_score = 0.0

        for exp_call in expected:
            best_match_score = 0.0

            for pred_call in predicted:
                score = self._function_similarity(pred_call, exp_call)
                best_match_score = max(best_match_score, score)

            total_score += best_match_score

        return total_score / len(expected)

    def _function_similarity(self, call1: Dict[str, Any], call2: Dict[str, Any]) -> float:
        """Calculate similarity score between two function calls."""
        score = 0.0

        # Function name match (50% of score)
        if call1.get("name") == call2.get("name"):
            score += 0.5

        # Arguments match (50% of score)
        args1 = call1.get("arguments", {})
        args2 = call2.get("arguments", {})

        if not args1 and not args2:
            score += 0.5
        elif args1 and args2:
            # Calculate argument overlap
            all_keys = set(args1.keys()) | set(args2.keys())
            if all_keys:
                matching_keys = sum(1 for key in all_keys if args1.get(key) == args2.get(key))
                score += 0.5 * (matching_keys / len(all_keys))

        return score


class FunctionEvaluator(BaseEvaluator):
    """Function calling evaluation with call parsing and validation."""

    def __init__(self, config: EvaluationConfig):
        super().__init__(config)
        self.client = LLMClient(model=config.model_name, **config.__dict__)
        self.validation_strategy = FunctionCallValidationStrategy()

    def _generate_response(self, sample: UnifiedSample) -> str:
        """Generate function calling response using LLM."""
        # Format available functions for the prompt
        functions_str = ""
        if sample.available_functions:
            functions_str = "\n".join([
                f"- {func.get('name', 'unknown')}: {func.get('description', 'No description')}"
                for func in sample.available_functions
            ])

        system_message = """You are a function calling assistant. Given a natural language question and a list of available functions, determine which functions to call and with what arguments to answer the question.

IMPORTANT: All government data is limited to years 2014-2024 only.

Rules:
1. Only call functions that are provided in the available functions list
2. Data is only available for years 2014-2024
3. Use the exact function names and parameter names as specified
4. Return function calls in JSON format: {"name": "function_name", "arguments": {"param": "value"}}
5. If asked for data outside 2014-2024, explain the limitation
6. If multiple functions are needed, return multiple JSON objects
7. If no functions are needed, explain why

Be precise with function names and arguments."""

        user_message = f"""Question: {sample.question}

Available Functions:
{functions_str}

Context: {sample.context or "No additional context provided"}

What function(s) should be called to answer this question?"""

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
        """Validate function calling response."""
        return self.validation_strategy.validate(sample, model_response)
