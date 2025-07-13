# StravaTalk Evaluation System

A flexible test runner for evaluating the StravaTalk LLM system with comprehensive assertions.

## Quick Start

```bash
# Option 1: Run from project root as module (recommended)
python -m stravatalk.evals.test_runner

# Option 2: Run from evals directory
cd stravatalk/evals
python test_runner.py

# Both will generate test_report.json AND test_report.html with detailed results

# View results with colors
python view_report.py  # Terminal colors
open test_report.html   # Full HTML report with colors
```

## Supported Assertion Types

### Classification Assertions
```json
{
  "expected_classification": "TEXT_AND_TABLE"
}
```
Validates that the query is classified correctly.

### Text Content Assertions
```json
{
  "expected_text_contains": ["12", "runs", "November"],
  "expected_text_not_contains": ["cycling", "swimming"]
}
```
Validates that the response text contains/doesn't contain specific phrases.

### Table Structure Assertions
```json
{
  "table_expected_row_count": 48,
  "table_expected_columns": ["name", "distance", "start_date", "type"]
}
```
Validates table structure and size.

### Date Range Assertions (New!)
```json
{
  "table_expected_date_range": "last_week"
}
```
Validates that all table data falls within the expected date range.

**Supported date range formats:**
- `"last_week"` - Previous Monday to Sunday
- `"this_week"` - Current Monday to Sunday  
- `"2023-11-01:2023-11-30"` - Specific date range

## Adding New Test Scenarios

To add a new test scenario to `evals.json`:

```json
{
  "id": "your_test_id",
  "description": "Description of what this tests",
  "turns": [
    {
      "user_input": "Your test query",
      "expected_classification": "TEXT_AND_TABLE",
      "table_expected_row_count": 10,
      "table_expected_date_range": "last_week",
      "expected_text_contains": ["expected", "phrases"]
    }
  ]
}
```

## Test Report Output

The test runner generates a detailed JSON report with:
- Overall success rates
- Per-scenario results
- Individual assertion results
- Error messages for failed assertions

## Example: Date Range Validation

For your "Show all my runs from last week" query, you can now add:

```json
{
  "user_input": "Show all my runs from last week",
  "expected_classification": "TEXT_AND_TABLE",
  "table_expected_date_range": "last_week",
  "expected_text_contains": ["runs", "last week"]
}
```

This will validate that:
1. Query is classified as TEXT_AND_TABLE
2. All returned activities are from last week's date range
3. Response text mentions "runs" and "last week"

## Running Specific Tests

You can modify the test runner to run specific scenarios:

```python
# Run only specific test IDs
runner = EvalTestRunner()
runner.run_scenario(specific_scenario_data)
```