"""Function Calling evaluator."""

import json
import re
from typing import Any, Dict, List

from USABench.core.base import BaseEvaluator, EvaluationConfig, UnifiedSample
from USABench.core.client import LLMClient

# Function calling documentation
FUNCTION_CALL_DOCS = """
# Available Functions

## ⚠️ DATA AVAILABILITY: All data is limited to 2014-2024

## BLS Functions (Bureau of Labor Statistics)

### get_cpi_data
Retrieve Consumer Price Index data from BLS
Parameters:
- series_id (string, required): BLS series ID for CPI data (default: CUUR0000SA0)
- start_year (integer, required): Start year for data retrieval (2014-2024)
- end_year (integer, required): End year for data retrieval (2014-2024)

### get_employment_cost_index
Retrieve Employment Cost Index data from BLS
Parameters:
- series_id (string, required): BLS series ID for ECI data (default: CIU1010000000000I)
- start_year (integer, required): Start year for data retrieval (2014-2024)
- end_year (integer, required): End year for data retrieval (2014-2024)

## BEA Functions (Bureau of Economic Analysis)

### get_gdp_by_industry
Retrieve GDP by industry data from BEA
Parameters:
- year (integer, required): Year for GDP data (2014-2024)
- industry (string, optional): Industry code or 'ALL' (default: ALL)
- table_id (string, optional): Table identifier (default: 1)

### get_regional_income
Retrieve regional personal income data from BEA
Parameters:
- state (string, required): State name or FIPS code
- year (integer, required): Year for income data (2014-2024)
- line_code (string, optional): Line code for specific income measure (default: SA1-1)

## Budget Functions

### get_budget_outlays
Retrieve federal budget outlays data
Parameters:
- function_name (string, optional): Budget function name
- fiscal_year (integer, optional): Specific fiscal year
- min_amount (float, optional): Minimum spending amount
- max_amount (float, optional): Maximum spending amount
"""


class FunctionCallEvaluator(BaseEvaluator):
    """Function Calling evaluator."""

    def __init__(self, config: EvaluationConfig):
        super().__init__(config)
        self.client = LLMClient(model=config.model_name, **config.__dict__)

    def _generate_response(self, sample: UnifiedSample) -> str:
        """Generate function calling response using LLM."""
        system_message = """You are a function calling assistant. Given a natural language question, determine which functions to call to answer the question.

Available functions and their parameters are provided below. You must:
1. Select the appropriate function(s) to answer the question
2. Provide correct parameters based on the question
3. Return function calls in JSON format: {"function_name": "name", "parameters": {...}}
4. If multiple functions are needed, return an array of function calls
5. Only use functions from the provided list

""" + FUNCTION_CALL_DOCS

        user_message = f"""Question: {sample.question}

Based on the available functions, what function call(s) would you make to answer this question? Return only the JSON function call(s)."""

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
        """Validate function calling response with 4-component metrics."""
        # Extract function calls from model response
        predicted_calls = self._extract_function_calls(model_response)
        expected_calls = sample.ground_truth_functions or []

        # Calculate 4-component function calling metrics
        metrics = self._calculate_berkeley_metrics(predicted_calls, expected_calls)

        # Overall pass if function selection is correct AND parameters are mostly correct
        overall_pass = (
            metrics['function_selection_accuracy'] >= 0.8 and
            metrics['parameter_accuracy'] >= 0.6
        )

        # Overall score is weighted average
        overall_score = (
            0.3 * metrics['function_selection_accuracy'] +
            0.3 * metrics['parameter_accuracy'] +
            0.2 * metrics['execution_success'] +
            0.2 * metrics['result_accuracy']
        )

        return overall_pass, overall_score, metrics

    def _extract_function_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract function calls from model response."""
        function_calls = []

        # Try to parse as JSON first
        try:
            # Look for JSON in the response
            json_pattern = r'\{.*?\}'
            json_matches = re.findall(json_pattern, response, re.DOTALL)

            for match in json_matches:
                try:
                    data = json.loads(match)
                    if 'function_name' in data:
                        function_calls.append({
                            "name": data['function_name'],
                            "arguments": data.get('parameters', {})
                        })
                except:
                    pass

            # Also try parsing the entire response as JSON array
            if not function_calls:
                try:
                    data = json.loads(response)
                    if isinstance(data, list):
                        for item in data:
                            if 'function_name' in item:
                                function_calls.append({
                                    "name": item['function_name'],
                                    "arguments": item.get('parameters', {})
                                })
                    elif isinstance(data, dict) and 'function_name' in data:
                        function_calls.append({
                            "name": data['function_name'],
                            "arguments": data.get('parameters', {})
                        })
                except:
                    pass
        except:
            pass

        # Fallback: Look for function call patterns
        if not function_calls:
            # Pattern: function_name(param1=value1, param2=value2)
            func_pattern = r'(\w+)\((.*?)\)'
            func_matches = re.findall(func_pattern, response)

            for func_name, args_str in func_matches:
                if func_name in ['get_cpi_data', 'get_employment_cost_index', 'get_gdp_by_industry', 'get_regional_income', 'get_budget_outlays']:
                    args = {}
                    if args_str.strip():
                        # Simple argument parsing
                        arg_pairs = [arg.strip() for arg in args_str.split(',')]
                        for pair in arg_pairs:
                            if '=' in pair:
                                key, value = pair.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"\'')
                                # Try to convert to appropriate type
                                try:
                                    if value.isdigit():
                                        value = int(value)
                                    elif '.' in value and value.replace('.', '').isdigit():
                                        value = float(value)
                                except:
                                    pass
                                args[key] = value

                    function_calls.append({
                        "name": func_name,
                        "arguments": args
                    })

        return function_calls

    def _calculate_berkeley_metrics(
        self,
        predicted: List[Dict[str, Any]],
        expected: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate function calling metrics."""

        # 1. Function Selection Accuracy
        function_selection = self._calculate_function_selection_accuracy(predicted, expected)

        # 2. Parameter Accuracy
        parameter_accuracy = self._calculate_parameter_accuracy(predicted, expected)

        # 3. Execution Success (simulated - would need actual API execution)
        execution_success = self._calculate_execution_success(predicted)

        # 4. Result Accuracy (simulated - would need ground truth results)
        result_accuracy = self._calculate_result_accuracy(predicted, expected)

        return {
            'function_selection_accuracy': function_selection,
            'parameter_accuracy': parameter_accuracy,
            'execution_success': execution_success,
            'result_accuracy': result_accuracy,
            'predicted_calls': predicted,
            'expected_calls': expected
        }

    def _calculate_function_selection_accuracy(
        self,
        predicted: List[Dict[str, Any]],
        expected: List[Dict[str, Any]]
    ) -> float:
        """Calculate function selection accuracy."""
        if not expected:
            return 1.0 if not predicted else 0.0

        if not predicted:
            return 0.0

        predicted_names = set(call.get('name') for call in predicted)
        expected_names = set(call.get('name') for call in expected)

        if not expected_names:
            return 1.0

        # Calculate F1 score for function names
        intersection = predicted_names & expected_names
        if not intersection:
            return 0.0

        precision = len(intersection) / len(predicted_names) if predicted_names else 0
        recall = len(intersection) / len(expected_names) if expected_names else 0

        if precision + recall == 0:
            return 0.0

        f1 = 2 * (precision * recall) / (precision + recall)
        return f1

    def _calculate_parameter_accuracy(
        self,
        predicted: List[Dict[str, Any]],
        expected: List[Dict[str, Any]]
    ) -> float:
        """Calculate parameter accuracy."""
        if not expected:
            return 1.0 if not predicted else 0.0

        if not predicted:
            return 0.0

        total_score = 0.0
        matches = 0

        for exp_call in expected:
            exp_name = exp_call.get('name')
            exp_args = exp_call.get('arguments', {})

            # Find matching predicted call
            for pred_call in predicted:
                if pred_call.get('name') == exp_name:
                    pred_args = pred_call.get('arguments', {})

                    # Calculate parameter match score
                    if not exp_args:
                        score = 1.0 if not pred_args else 0.5
                    else:
                        matching_params = 0
                        total_params = len(exp_args)

                        for key, value in exp_args.items():
                            if key in pred_args:
                                pred_value = pred_args[key]
                                # Flexible comparison
                                if self._parameters_match(value, pred_value):
                                    matching_params += 1

                        score = matching_params / total_params if total_params > 0 else 0

                    total_score += score
                    matches += 1
                    break

        return total_score / len(expected) if expected else 0.0

    def _parameters_match(self, expected, predicted) -> bool:
        """Check if two parameter values match (with some flexibility)."""
        if expected == predicted:
            return True

        # Handle numeric comparisons
        try:
            if abs(float(expected) - float(predicted)) < 0.01:
                return True
        except:
            pass

        # Handle string comparisons (case-insensitive)
        try:
            if str(expected).lower() == str(predicted).lower():
                return True
        except:
            pass

        # Handle year ranges (e.g., 2023 vs 2024 might both be valid for "recent")
        try:
            exp_year = int(expected)
            pred_year = int(predicted)
            if abs(exp_year - pred_year) <= 1:  # Within 1 year
                return True
        except:
            pass

        return False

    def _calculate_execution_success(self, predicted: List[Dict[str, Any]]) -> float:
        """Calculate execution success (simulated)."""
        if not predicted:
            return 0.0

        # Check if the predicted calls are well-formed
        valid_calls = 0
        for call in predicted:
            if self._is_valid_function_call(call):
                valid_calls += 1

        return valid_calls / len(predicted) if predicted else 0.0

    def _is_valid_function_call(self, call: Dict[str, Any]) -> bool:
        """Check if a function call is valid."""
        if not isinstance(call, dict):
            return False

        if 'name' not in call:
            return False

        func_name = call.get('name')
        args = call.get('arguments', {})

        # Validate based on function name
        if func_name == 'get_cpi_data':
            return 'start_year' in args and 'end_year' in args
        elif func_name == 'get_employment_cost_index':
            return 'start_year' in args and 'end_year' in args
        elif func_name == 'get_gdp_by_industry':
            return 'year' in args
        elif func_name == 'get_regional_income':
            return 'state' in args and 'year' in args
        elif func_name == 'get_budget_outlays':
            return True  # All parameters are optional
        else:
            return False

    def _calculate_result_accuracy(
        self,
        predicted: List[Dict[str, Any]],
        expected: List[Dict[str, Any]]
    ) -> float:
        """Calculate result accuracy (simulated)."""
        # In a real implementation, this would compare actual API results
        # For now, we'll use a combination of function and parameter accuracy
        function_acc = self._calculate_function_selection_accuracy(predicted, expected)
        param_acc = self._calculate_parameter_accuracy(predicted, expected)

        # Result accuracy is lower than parameter accuracy (harder to get right)
        return (function_acc * 0.4 + param_acc * 0.6) * 0.8
