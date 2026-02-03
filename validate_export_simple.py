"""Validate the golden records CSV export using pure Python."""

import csv
from collections import defaultdict

# Read CSV
records = []
with open('USABench/data/golden_records_consolidated.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    records = list(reader)

print("=" * 60)
print("CSV VALIDATION REPORT")
print("=" * 60)

# Validate counts
print("\n1. RECORD COUNTS:")
print(f"   Total records: {len(records)} (expected: 459)")
sql_count = sum(1 for r in records if r['question_type'] == 'sql')
func_count = sum(1 for r in records if r['question_type'] == 'function')
print(f"   SQL questions: {sql_count} (expected: 293)")
print(f"   Function questions: {func_count} (expected: 166)")

assert len(records) == 459, f"Expected 459 total records, got {len(records)}"
assert sql_count == 293, f"Expected 293 SQL questions, got {sql_count}"
assert func_count == 166, f"Expected 166 function questions, got {func_count}"
print("   ✓ All counts correct!")

# Validate no empty values in key columns
print("\n2. EMPTY VALUE CHECKS:")
key_columns = ['question_id', 'question_text', 'difficulty', 'question_type']
for col in key_columns:
    empty_count = sum(1 for r in records if not r.get(col, '').strip())
    status = "✓" if empty_count == 0 else "✗"
    print(f"   {status} {col}: {empty_count} empty values")
    assert empty_count == 0, f"Found empty values in {col}"

# Validate difficulty values
print("\n3. DIFFICULTY VALUES:")
valid_difficulties = {'easy', 'medium', 'hard'}
actual_difficulties = set(r['difficulty'] for r in records)
print(f"   Valid values: {valid_difficulties}")
print(f"   Actual values: {actual_difficulties}")
assert actual_difficulties.issubset(valid_difficulties), f"Invalid difficulty values: {actual_difficulties - valid_difficulties}"
print("   ✓ All difficulty values valid!")

# Difficulty distribution
print("\n4. DIFFICULTY DISTRIBUTION:")
diff_dist = defaultdict(lambda: defaultdict(int))
for r in records:
    diff_dist[r['question_type']][r['difficulty']] += 1

print("\n   SQL questions:")
for diff in ['easy', 'medium', 'hard']:
    count = diff_dist['sql'][diff]
    print(f"     {diff}: {count}")

print("\n   Function questions:")
for diff in ['easy', 'medium', 'hard']:
    count = diff_dist['function'][diff]
    print(f"     {diff}: {count}")
print("   Expected: easy: 11, medium: 48, hard: 107")

# Check SQL-specific fields
print("\n5. SQL-SPECIFIC FIELDS:")
sql_rows = [r for r in records if r['question_type'] == 'sql']
sql_with_query = sum(1 for r in sql_rows if r.get('reference_sql', '').strip())
sql_without_func = sum(1 for r in sql_rows if not r.get('function_sequence', '').strip())
print(f"   SQL rows with reference_sql: {sql_with_query}/{len(sql_rows)}")
print(f"   SQL rows with empty function_sequence: {sql_without_func}/{len(sql_rows)}")
assert sql_with_query == len(sql_rows), "Some SQL rows missing reference_sql"
print("   ✓ SQL-specific fields validated!")

# Check function-specific fields
print("\n6. FUNCTION-SPECIFIC FIELDS:")
func_rows = [r for r in records if r['question_type'] == 'function']
func_with_seq = sum(1 for r in func_rows if r.get('function_sequence', '').strip())
func_without_sql = sum(1 for r in func_rows if not r.get('reference_sql', '').strip())
print(f"   Function rows with function_sequence: {func_with_seq}/{len(func_rows)}")
print(f"   Function rows with empty reference_sql: {func_without_sql}/{len(func_rows)}")
assert func_with_seq == len(func_rows), "Some function rows missing function_sequence"
print("   ✓ Function-specific fields validated!")

# Sample records
print("\n7. SAMPLE RECORDS:")
first_sql = next(r for r in records if r['question_id'] == '1')
print("\n   First SQL question (ID 1):")
print(f"   Question: {first_sql['question_text'][:60]}...")
print(f"   Type: {first_sql['question_type']}")
print(f"   Difficulty: {first_sql['difficulty']}")
print(f"   Tables: {first_sql['primary_tables']}")
print(f"   Complexity: {first_sql['workflow_complexity']}")
print(f"   SQL length: {len(first_sql['reference_sql'])} chars")

first_func = next(r for r in records if r['question_type'] == 'function')
print(f"\n   First function question (ID {first_func['question_id']}):")
print(f"   Question: {first_func['question_text'][:60]}...")
print(f"   Type: {first_func['question_type']}")
print(f"   Difficulty: {first_func['difficulty']}")
print(f"   Functions: {first_func['primary_tables']}")
print(f"   Complexity: {first_func['workflow_complexity']}")
print(f"   Sequence length: {len(first_func['function_sequence'])} chars")

# Check question ID uniqueness
print("\n8. QUESTION ID UNIQUENESS:")
question_ids = [int(r['question_id']) for r in records]
unique_ids = set(question_ids)
print(f"   Total IDs: {len(question_ids)}")
print(f"   Unique IDs: {len(unique_ids)}")
assert len(question_ids) == len(unique_ids), "Duplicate question IDs found!"
print("   ✓ All question IDs are unique!")

print("\n" + "=" * 60)
print("✓ ALL VALIDATIONS PASSED!")
print("=" * 60)
