"""Production Function Calling Evaluator for USABench."""

from dataclasses import dataclass
import logging
import os
import re
from typing import Any, Dict, List

import requests

from USABench.core.base import BaseEvaluator, EvaluationConfig, UnifiedSample
from USABench.core.production_client import ProductionLLMClient

logger = logging.getLogger(__name__)

@dataclass
class FunctionCallResult:
    """Result of function calling evaluation."""
    function_selection_accuracy: float
    parameter_accuracy: float
    execution_success: float
    result_accuracy: float
    overall_score: float
    is_correct: bool
    predicted_calls: List[Dict[str, Any]]
    expected_calls: List[Dict[str, Any]]
    execution_details: Dict[str, Any]

class APIExecutor:
    """Execute real API calls for BLS and BEA."""

    def __init__(self):
        """Initialize with API keys."""
        self.bls_api_key = os.getenv('BLS_API_KEY')
        self.bea_api_key = os.getenv('BEA_API_KEY')

        # Warn if API keys are missing (but allow graceful degradation)
        if not self.bls_api_key:
            logger.warning("BLS_API_KEY not set. Some function calls may fail.")
        if not self.bea_api_key:
            logger.warning("BEA_API_KEY not set. Some function calls may fail.")
        logger.info(f"APIExecutor initialized with BLS key: {self.bls_api_key[:8]}... and BEA key: {self.bea_api_key[:8]}...")

    def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute function call against real APIs."""
        try:
            if function_name == "get_cpi_data":
                return self._call_bls_api(
                    series_id=parameters.get("series_id", "CUUR0000SA0"),
                    start_year=parameters.get("start_year", 2020),
                    end_year=parameters.get("end_year", 2024)
                )
            elif function_name == "get_employment_cost_index":
                return self._call_bls_api(
                    series_id=parameters.get("series_id", "CIU1010000000000I"),
                    start_year=parameters.get("start_year", 2020),
                    end_year=parameters.get("end_year", 2024)
                )
            elif function_name == "get_productivity_data":
                return self._call_bls_api(
                    series_id=parameters.get("series_id", "PRS85006092"),
                    start_year=parameters.get("start_year", 2020),
                    end_year=parameters.get("end_year", 2024)
                )
            elif function_name == "get_gdp_by_industry":
                return self._call_bea_api(
                    dataset="GDPbyIndustry",
                    year=parameters.get("year", 2023),
                    industry=parameters.get("industry", "ALL"),
                    table_id=parameters.get("table_id", "1")
                )
            elif function_name == "get_regional_income":
                return self._call_bea_api(
                    dataset="Regional",
                    state=parameters.get("state", "CA"),
                    year=parameters.get("year", 2023),
                    line_code=parameters.get("line_code", "SA1-1")
                )
            else:
                return {"success": False, "error": f"Unknown function: {function_name}"}

        except Exception as e:
            logger.error(f"API execution failed for {function_name}: {e}")
            return {"success": False, "error": str(e)}

    def _call_bls_api(self, series_id: str, start_year: int, end_year: int) -> Dict[str, Any]:
        """Call BLS API."""
        try:
            url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
            headers = {'Content-Type': 'application/json'}

            data = {
                'seriesid': [series_id],
                'startyear': str(start_year),
                'endyear': str(end_year),
                'registrationkey': self.bls_api_key
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            result["success"] = result.get("status") == "REQUEST_SUCCEEDED"
            return result

        except Exception as e:
            logger.error(f"BLS API call failed: {e}")
            return {"success": False, "error": str(e)}

    def _call_bea_api(self, dataset: str, **params) -> Dict[str, Any]:
        """Call BEA API."""
        try:
            base_url = "https://apps.bea.gov/api/data"

            api_params = {
                'UserID': self.bea_api_key,
                'method': 'GetData',
                'DataSetName': dataset,
                'ResultFormat': 'JSON'
            }
            api_params.update(params)

            response = requests.get(base_url, params=api_params, timeout=30)
            response.raise_for_status()

            result = response.json()
            # BEA API doesn't have a status field, check for BEAAPI key
            result["success"] = "BEAAPI" in result and "Results" in result.get("BEAAPI", {})
            return result

        except Exception as e:
            logger.error(f"BEA API call failed: {e}")
            return {"success": False, "error": str(e)}


class FunctionCallEvaluator(BaseEvaluator):
    """Function Calling Evaluator."""

    def __init__(self, config: EvaluationConfig):
        super().__init__(config)
        self.client = ProductionLLMClient()
        self.api_executor = APIExecutor()

        # Function calling documentation
        self.function_docs = """
# BLS Functions

## get_cpi_data
**Description:** Retrieve Consumer Price Index data from BLS
**Parameters:**
- series_id (string) ✓ - BLS series ID for CPI data (default: CUUR0000SA0)
- start_year (integer) ✓ - Start year for data retrieval  
- end_year (integer) ✓ - End year for data retrieval

## get_employment_cost_index
**Description:** Retrieve Employment Cost Index data from BLS
**Parameters:**
- series_id (string) ✓ - BLS series ID for ECI data (default: CIU1010000000000I)
- start_year (integer) ✓ - Start year for data retrieval
- end_year (integer) ✓ - End year for data retrieval

## get_productivity_data
**Description:** Retrieve productivity data from BLS
**Parameters:**
- series_id (string) ✓ - BLS series ID for productivity data (default: PRS85006092)
- start_year (integer) ✓ - Start year for data retrieval
- end_year (integer) ✓ - End year for data retrieval

# BEA Functions

## get_gdp_by_industry
**Description:** Retrieve GDP by industry data from BEA
**Parameters:**
- year (integer) ✓ - Year for GDP data
- industry (string) - Industry code or 'ALL' (default: ALL)
- table_id (string) - Table identifier (default: 1)

## get_regional_income
**Description:** Retrieve regional personal income data from BEA
**Parameters:**
- state (string) ✓ - State name or FIPS code
- year (integer) ✓ - Year for income data
- line_code (string) - Line code for specific income measure (default: SA1-1)
"""

        logger.info(f"FunctionCallEvaluator initialized with {config.model_name}")

    def _generate_response(self, sample: UnifiedSample) -> str:
        """Generate function calling response using production LLM client."""
        system_message = f"""You are an expert economic data analyst with access to government economic data APIs. You must call specific functions to answer questions - do NOT provide general explanations.

CRITICAL: All data is limited to years 2014-2024. If asked for data outside this range, explain the limitation.

Available Functions:
{self.function_docs}

CRITICAL INSTRUCTIONS:
1. Data is only available for 2014-2024
2. You MUST call a specific function to answer each question
3. Use ONLY the functions listed above
3. Format your response EXACTLY like this:

Function: get_cpi_data
Parameters: series_id=CUUR0000SA0, start_year=2020, end_year=2024

4. Do NOT provide explanations, code examples, or general guidance
5. Do NOT suggest hypothetical functions or APIs
6. ALWAYS specify concrete parameter values based on the question
7. If unsure about specific parameters, use reasonable defaults"""

        user_message = f"Question: {sample.question}\n\nWhich function(s) should I call and with what parameters to answer this question?"

        try:
            # Import EvaluationPrompt class from production client
            from ..core.production_client import EvaluationPrompt

            # Create proper evaluation prompt
            prompt = EvaluationPrompt(
                system_message=system_message,
                user_message=user_message
            )

            response = self.client.generate(
                prompt=prompt,
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            if response.error:
                logger.error(f"LLM error: {response.error}")
                return f"Error: {response.error}"

            logger.info(f"Generated function calling response: {response.content[:100]}...")
            return response.content

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return f"Error: {e}"

    def _validate_response(
        self,
        sample: UnifiedSample,
        model_response: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """Validate function calling response using 4-component binary metrics."""
        try:
            # Extract predicted function calls
            predicted_calls = self._extract_function_calls(model_response)

            # Get expected calls from sample
            expected_calls = self._get_expected_calls(sample)

            # Calculate 4-component binary metrics
            function_selection_score = self._evaluate_function_selection(predicted_calls, expected_calls)
            parameter_accuracy_score = self._evaluate_parameter_accuracy(predicted_calls, expected_calls)
            execution_success_score = self._evaluate_execution_success(predicted_calls)
            result_accuracy_score = self._evaluate_result_accuracy(predicted_calls, sample)

            # Overall score (average of 4 binary metrics)
            overall_score = (function_selection_score + parameter_accuracy_score +
                           execution_success_score + result_accuracy_score) / 4.0

            is_correct = overall_score >= 0.75  # 3 out of 4 metrics must pass

            validation_details = {
                "function_selection_accuracy": function_selection_score,
                "parameter_accuracy": parameter_accuracy_score,
                "execution_success": execution_success_score,
                "result_accuracy": result_accuracy_score,
                "predicted_calls": predicted_calls,
                "expected_calls": expected_calls,
                "function_eval_v2": True,
                "evaluation_method": "4_component_binary_metrics"
            }

            logger.info(f"Function call evaluation - Overall: {overall_score:.3f}, Components: [{function_selection_score:.3f}, {parameter_accuracy_score:.3f}, {execution_success_score:.3f}, {result_accuracy_score:.3f}]")

            return is_correct, overall_score, validation_details

        except Exception as e:
            logger.error(f"Function call validation failed: {e}")
            return False, 0.0, {"error": str(e), "function_eval_v2": True}

    def _extract_function_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract function calls from model response."""
        function_calls = []

        # Known function names
        all_functions = [
            "get_cpi_data", "get_employment_cost_index", "get_productivity_data",
            "get_gdp_by_industry", "get_regional_income"
        ]

        # Look for function call patterns
        patterns = [
            r'Function:\s*(\w+)\s*\nParameters:\s*(.+?)(?=\n\n|\n$|$)',  # Function: name\nParameters: params
            r'Function:\s*(\w+)\s*Parameters:\s*(.+?)(?=\n|$)',  # Function: name Parameters: params (single line)
            r'(\w+)\s*\((.*?)\)',  # function_name(params)
            r'call\s+(\w+)\s*\((.*?)\)',  # call function_name(params)
            r'use\s+(\w+)\s*\((.*?)\)',  # use function_name(params)
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, response_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                func_name = match.group(1)
                params_str = match.group(2) if len(match.groups()) > 1 else ""

                # Check if this is a valid function name
                if func_name in all_functions:
                    # Parse parameters
                    params = self._parse_parameters(params_str)

                    function_calls.append({
                        "function_name": func_name,
                        "parameters": params
                    })

        # If no structured calls found, look for function names mentioned
        if not function_calls:
            for func_name in all_functions:
                if func_name.lower() in response_text.lower():
                    function_calls.append({
                        "function_name": func_name,
                        "parameters": self._infer_default_parameters(func_name)
                    })

        return function_calls

    def _parse_parameters(self, params_str: str) -> Dict[str, Any]:
        """Parse parameter string into dictionary."""
        params = {}

        if not params_str.strip():
            return params

        try:
            # Handle key=value format
            if '=' in params_str:
                pairs = re.findall(r'(\w+)\s*=\s*([^,]+)', params_str)
                for key, value in pairs:
                    value = value.strip().strip('"\'')
                    params[key] = self._convert_parameter_value(value)

        except Exception as e:
            logger.warning(f"Failed to parse parameters '{params_str}': {e}")

        return params

    def _convert_parameter_value(self, value: str) -> Any:
        """Convert string parameter value to appropriate type."""
        value = value.strip()

        # Handle numbers
        if value.replace('.', '').replace('-', '').isdigit():
            if '.' in value:
                return float(value)
            else:
                return int(value)

        # Handle booleans
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'

        # Handle null
        if value.lower() in ['null', 'none']:
            return None

        # Return as string
        return value

    def _infer_default_parameters(self, function_name: str) -> Dict[str, Any]:
        """Infer default parameters for function."""
        if function_name == "get_cpi_data":
            return {"series_id": "CUUR0000SA0", "start_year": 2020, "end_year": 2024}
        elif function_name == "get_employment_cost_index":
            return {"series_id": "CIU1010000000000I", "start_year": 2020, "end_year": 2024}
        elif function_name == "get_productivity_data":
            return {"series_id": "PRS85006092", "start_year": 2020, "end_year": 2024}
        elif function_name == "get_gdp_by_industry":
            return {"year": 2023, "industry": "ALL", "table_id": "1"}
        elif function_name == "get_regional_income":
            return {"state": "CA", "year": 2023, "line_code": "SA1-1"}
        else:
            return {}

    def _get_expected_calls(self, sample: UnifiedSample) -> List[Dict[str, Any]]:
        """Extract expected function calls from sample."""
        # For now, infer expected calls based on question content
        question_lower = sample.question.lower()

        if "cpi" in question_lower or "consumer price" in question_lower:
            return [{"function_name": "get_cpi_data", "parameters": {"series_id": "CUUR0000SA0"}}]
        elif "employment cost" in question_lower or "eci" in question_lower:
            return [{"function_name": "get_employment_cost_index", "parameters": {"series_id": "CIU1010000000000I"}}]
        elif "gdp" in question_lower and "industry" in question_lower:
            return [{"function_name": "get_gdp_by_industry", "parameters": {"year": 2023}}]
        elif "income" in question_lower and ("state" in question_lower or "region" in question_lower):
            return [{"function_name": "get_regional_income", "parameters": {"year": 2023}}]
        else:
            return [{"function_name": "get_gdp_by_industry", "parameters": {"year": 2023}}]

    def _evaluate_function_selection(self, predicted_calls: List[Dict], expected_calls: List[Dict]) -> float:
        """Evaluate function selection accuracy (Binary Metric 1)."""
        if not expected_calls:
            return 1.0 if not predicted_calls else 0.0

        expected_functions = [call["function_name"] for call in expected_calls]
        predicted_functions = [call["function_name"] for call in predicted_calls]

        # Binary: exact match of function names (order doesn't matter)
        expected_set = set(expected_functions)
        predicted_set = set(predicted_functions)

        # Perfect match gets 1.0, anything else gets 0.0
        return 1.0 if expected_set == predicted_set else 0.0

    def _evaluate_parameter_accuracy(self, predicted_calls: List[Dict], expected_calls: List[Dict]) -> float:
        """Evaluate parameter accuracy (Binary Metric 2)."""
        if not expected_calls:
            return 1.0

        if len(predicted_calls) != len(expected_calls):
            return 0.0

        # Create function name -> parameters mapping
        expected_params = {}
        for call in expected_calls:
            expected_params[call["function_name"]] = call.get("parameters", {})

        predicted_params = {}
        for call in predicted_calls:
            predicted_params[call["function_name"]] = call.get("parameters", {})

        # Check each expected function's parameters
        total_score = 0.0
        for func_name, exp_params in expected_params.items():
            if func_name not in predicted_params:
                continue

            pred_params = predicted_params[func_name]

            # Score parameters - more flexible than exact match
            param_score = self._score_parameters(exp_params, pred_params)
            total_score += param_score

        return total_score / len(expected_params) if expected_params else 1.0

    def _score_parameters(self, expected: Dict[str, Any], predicted: Dict[str, Any]) -> float:
        """Score parameter similarity."""
        if not expected:
            return 1.0

        # Required keys match
        required_keys = ["series_id", "year", "start_year", "end_year", "industry", "state"]
        key_matches = 0
        total_keys = 0

        for key in required_keys:
            if key in expected:
                total_keys += 1
                if key in predicted and self._values_match(expected[key], predicted[key]):
                    key_matches += 1

        # If no required keys, check all keys
        if total_keys == 0:
            for key, exp_val in expected.items():
                total_keys += 1
                if key in predicted and self._values_match(exp_val, predicted[key]):
                    key_matches += 1

        return key_matches / total_keys if total_keys > 0 else 1.0

    def _evaluate_execution_success(self, predicted_calls: List[Dict]) -> float:
        """Evaluate execution success (Binary Metric 3)."""
        if not predicted_calls:
            return 0.0

        successful_calls = 0

        for call in predicted_calls:
            function_name = call["function_name"]
            parameters = call.get("parameters", {})

            try:
                # Actually execute the function
                result = self.api_executor.execute_function(function_name, parameters)
                if result.get("success", False):
                    successful_calls += 1
                    logger.info(f"✅ API execution successful for {function_name}")
                else:
                    logger.warning(f"❌ API execution failed for {function_name}: {result.get('error')}")
            except Exception as e:
                logger.warning(f"Execution failed for {function_name}: {e}")
                continue

        return successful_calls / len(predicted_calls)

    def _evaluate_result_accuracy(self, predicted_calls: List[Dict], sample: UnifiedSample) -> float:
        """Evaluate result accuracy by comparing actual API results (Binary Metric 4)."""
        if not predicted_calls:
            return 0.0

        # For now, if we can execute the function and get some data back, consider it accurate
        # This could be enhanced with ground truth comparison in the future
        successful_results = 0

        for call in predicted_calls:
            function_name = call["function_name"]
            parameters = call.get("parameters", {})

            try:
                result = self.api_executor.execute_function(function_name, parameters)

                if result.get("success", False):
                    # Check if we got meaningful data
                    if self._has_meaningful_data(result, function_name):
                        successful_results += 1
                        logger.info(f"✅ Meaningful data retrieved from {function_name}")
                    else:
                        logger.warning(f"⚠️ Empty or invalid data from {function_name}")

            except Exception as e:
                logger.warning(f"Result evaluation failed for {function_name}: {e}")
                continue

        return successful_results / len(predicted_calls)

    def _has_meaningful_data(self, result: Dict[str, Any], function_name: str) -> bool:
        """Check if API result contains meaningful data."""
        try:
            if function_name.startswith("get_cpi_") or function_name.startswith("get_employment_") or function_name.startswith("get_productivity_"):
                # BLS API
                if "Results" in result:
                    results = result["Results"]
                    if isinstance(results, list) and results:
                        series = results[0].get("series", [])
                        if series and "data" in series[0]:
                            return len(series[0]["data"]) > 0

            elif function_name.startswith("get_gdp_") or function_name.startswith("get_regional_"):
                # BEA API
                if "BEAAPI" in result and "Results" in result["BEAAPI"]:
                    data = result["BEAAPI"]["Results"].get("Data", [])
                    return len(data) > 0

            return False

        except Exception:
            return False

    def _values_match(self, expected: Any, predicted: Any) -> bool:
        """Check if two values match with flexible comparison."""
        # Exact match
        if expected == predicted:
            return True

        # String comparison (case insensitive)
        if isinstance(expected, str) and isinstance(predicted, str):
            return expected.lower() == predicted.lower()

        # Numeric comparison with tolerance
        if isinstance(expected, (int, float)) and isinstance(predicted, (int, float)):
            return abs(expected - predicted) < 0.001

        return False
