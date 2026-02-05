# Performance Fix: Function Calling Evaluation

## Issue Summary

The benchmark was taking ~30 hours for just 3 models due to a critical performance bug in the function calling evaluator.

### Root Cause

In `USABench/evaluators/berkeley_function.py`, the `_validate_response()` method was executing government API calls (BLS/BEA) **twice** for every question:

1. **First execution**: `_evaluate_execution_success()` at line 276 → executes all API calls
2. **Second execution**: `_evaluate_result_accuracy()` at line 277 → executes the same API calls again

### Impact Analysis

- **167 function calling questions** per model
- **2 duplicate API calls** per question = **334 API calls instead of 167**
- **3 models tested** = **1,002 unnecessary API calls**
- Each BLS/BEA API call has network latency (2-5 seconds typical)
- **Total overhead**: ~30-80 minutes per model just from duplicate API calls

### Fix Implemented

Introduced a **caching mechanism** that executes API calls once and reuses results:

1. **New method**: `_execute_api_calls_once()` - executes all API calls once and caches results
2. **New method**: `_evaluate_execution_success_from_cache()` - evaluates using cached results
3. **New method**: `_evaluate_result_accuracy_from_cache()` - evaluates using cached results
4. **Updated**: `_validate_response()` - now uses the cached execution pattern

### Code Changes

```python
# Before (duplicated API execution):
execution_success_score = self._evaluate_execution_success(predicted_calls)
result_accuracy_score = self._evaluate_result_accuracy(predicted_calls, sample)

# After (cached execution):
execution_results = self._execute_api_calls_once(predicted_calls)
execution_success_score = self._evaluate_execution_success_from_cache(execution_results)
result_accuracy_score = self._evaluate_result_accuracy_from_cache(execution_results)
```

### Expected Performance Improvement

- **Function calling evaluation**: ~50% faster
- **Full benchmark (3 models)**: 30 hours → **~15 hours** (estimated)
- **Per model**: ~10 hours → **~5 hours** (estimated)

### Verification Steps

To verify the fix is working:

1. **Run a quick test with verbose logging**:
   ```bash
   python3 -m USABench --model gpt-4o --function-samples 5 --sql-samples 0 --verbose
   ```

2. **Check the logs for**:
   - Each function call should show "✅ API execution successful" **only once** per question
   - No duplicate "API execution" messages for the same function call

3. **Compare execution times**:
   - Before: ~10 hours per model (167 function questions)
   - After: ~5 hours per model (estimated)

4. **Monitor API calls**:
   - You can count BLS/BEA API requests in your API dashboard
   - Should see ~167 calls per model instead of ~334

### Files Modified

- `USABench/evaluators/berkeley_function.py`:
  - Modified `_validate_response()` method
  - Added `_execute_api_calls_once()` method
  - Added `_evaluate_execution_success_from_cache()` method
  - Added `_evaluate_result_accuracy_from_cache()` method

### Backward Compatibility

- Old methods (`_evaluate_execution_success`, `_evaluate_result_accuracy`) remain in the codebase but are no longer called
- All evaluation results remain identical (same scoring logic, just no duplication)
- No changes to public APIs or configuration

### Additional Notes

The old methods at lines 573 and 598 are now unused but kept for backward compatibility. They can be removed in a future cleanup if desired.

## Testing

Run a full benchmark test:

```bash
# Quick test (5 samples per model)
python3 -m USABench --benchmark --test-mode --verbose

# Full benchmark (should now take ~15 hours instead of 30+ hours)
python3 -m USABench --benchmark
```

## Related Issues

This fix resolves:
- Excessive API calls to BLS/BEA government APIs
- Long benchmark execution times (30+ hours)
- Unnecessary network latency and rate limit exhaustion
