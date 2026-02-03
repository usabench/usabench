"""Validate the golden records CSV export."""

import pandas as pd

# Read CSV
df = pd.read_csv('USABench/data/golden_records_consolidated.csv')

print("=" * 60)
print("CSV VALIDATION REPORT")
print("=" * 60)

# Validate counts
print("\n1. RECORD COUNTS:")
print(f"   Total records: {len(df)} (expected: 459)")
sql_count = (df['question_type'] == 'sql').sum()
func_count = (df['question_type'] == 'function').sum()
print(f"   SQL questions: {sql_count} (expected: 293)")
print(f"   Function questions: {func_count} (expected: 166)")

assert len(df) == 459, f"Expected 459 total records, got {len(df)}"
assert sql_count == 293, f"Expected 293 SQL questions, got {sql_count}"
assert func_count == 166, f"Expected 166 function questions, got {func_count}"
print("   ✓ All counts correct!")

# Validate no nulls in key columns
print("\n2. NULL VALUE CHECKS:")
null_checks = {
    'question_id': df['question_id'].notna().all(),
    'question_text': df['question_text'].notna().all(),
    'difficulty': df['difficulty'].notna().all(),
    'question_type': df['question_type'].notna().all()
}

for col, is_valid in null_checks.items():
    status = "✓" if is_valid else "✗"
    print(f"   {status} {col}: {'No nulls' if is_valid else 'Has nulls!'}")

assert all(null_checks.values()), "Found null values in critical columns"

# Validate difficulty values
print("\n3. DIFFICULTY VALUES:")
valid_difficulties = {'easy', 'medium', 'hard'}
actual_difficulties = set(df['difficulty'].unique())
print(f"   Valid values: {valid_difficulties}")
print(f"   Actual values: {actual_difficulties}")
assert actual_difficulties.issubset(valid_difficulties), f"Invalid difficulty values: {actual_difficulties - valid_difficulties}"
print("   ✓ All difficulty values valid!")

# Difficulty distribution
print("\n4. DIFFICULTY DISTRIBUTION:")
distribution = df.groupby(['question_type', 'difficulty']).size().unstack(fill_value=0)
print(distribution)

# Expected function distribution
print("\n   Function questions expected:")
print("     easy: 11, medium: 48, hard: 107")

# Check SQL-specific fields
print("\n5. SQL-SPECIFIC FIELDS:")
sql_rows = df[df['question_type'] == 'sql']
sql_with_query = sql_rows['reference_sql'].notna().sum()
sql_without_func = (sql_rows['function_sequence'] == '').sum()
print(f"   SQL rows with reference_sql: {sql_with_query}/{len(sql_rows)}")
print(f"   SQL rows with empty function_sequence: {sql_without_func}/{len(sql_rows)}")
assert sql_with_query == len(sql_rows), "Some SQL rows missing reference_sql"
print("   ✓ SQL-specific fields validated!")

# Check function-specific fields
print("\n6. FUNCTION-SPECIFIC FIELDS:")
func_rows = df[df['question_type'] == 'function']
func_with_seq = func_rows['function_sequence'].apply(lambda x: x != '').sum()
func_without_sql = (func_rows['reference_sql'] == '').sum()
print(f"   Function rows with function_sequence: {func_with_seq}/{len(func_rows)}")
print(f"   Function rows with empty reference_sql: {func_without_sql}/{len(func_rows)}")
assert func_with_seq == len(func_rows), "Some function rows missing function_sequence"
print("   ✓ Function-specific fields validated!")

# Sample records
print("\n7. SAMPLE RECORDS:")
print("\n   First SQL question (ID 1):")
first_sql = df[df['question_id'] == 1].iloc[0]
print(f"   Question: {first_sql['question_text'][:60]}...")
print(f"   Type: {first_sql['question_type']}")
print(f"   Difficulty: {first_sql['difficulty']}")
print(f"   Tables: {first_sql['primary_tables']}")
print(f"   SQL length: {len(str(first_sql['reference_sql']))} chars")

print("\n   First function question (ID 17):")
first_func = df[df['question_id'] == 17].iloc[0]
print(f"   Question: {first_func['question_text'][:60]}...")
print(f"   Type: {first_func['question_type']}")
print(f"   Difficulty: {first_func['difficulty']}")
print(f"   Functions: {first_func['primary_tables']}")
print(f"   Sequence length: {len(str(first_func['function_sequence']))} chars")

print("\n" + "=" * 60)
print("✓ ALL VALIDATIONS PASSED!")
print("=" * 60)
