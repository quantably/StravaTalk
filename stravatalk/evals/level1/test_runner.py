"""
Flexible test runner for StravaTalk evaluation scenarios.
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import logging
from dataclasses import dataclass

# Import from the stravatalk package
try:
    # Try relative imports first (when run as module)
    from ..orchestrator import initialize_agents, process_query
    from ..agents.classify_agent import QueryType
except ImportError:
    # Fall back to absolute imports (when run directly)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import stravatalk.orchestrator as orchestrator_module
    from stravatalk.agents.classify_agent import QueryType
    
    # Monkey patch to use the module functions
    initialize_agents = orchestrator_module.initialize_agents
    process_query = orchestrator_module.process_query

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test assertion."""
    test_id: str
    turn_index: int
    assertion_type: str
    assertion_details: Any
    passed: bool
    actual_value: Any
    expected_value: Any
    error_message: Optional[str] = None


@dataclass
class ScenarioResult:
    """Result of an entire test scenario."""
    scenario_id: str
    description: str
    total_assertions: int
    passed_assertions: int
    failed_assertions: int
    test_results: List[TestResult]
    sql_query: str = ""
    user_query: str = ""
    
    @property
    def success_rate(self) -> float:
        if self.total_assertions == 0:
            return 0.0
        return self.passed_assertions / self.total_assertions


class EvalTestRunner:
    """Test runner for evaluation scenarios."""
    
    def __init__(self, evals_file: str = None):
        if evals_file is None:
            # Default to evals.json in the same directory as this script
            evals_file = os.path.join(os.path.dirname(__file__), "evals.json")
        self.evals_file = evals_file
        self.agents = None
        self.test_results: List[TestResult] = []
        self.scenario_results: List[ScenarioResult] = []
        self.mock_current_date = None
        
    def initialize_system(self):
        """Initialize the StravaTalk system for testing."""
        try:
            self.agents = initialize_agents(current_date=self.mock_current_date)
            logger.info("✅ System initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize system: {e}")
            return False
    
    def load_evals(self) -> Dict[str, Any]:
        """Load evaluation scenarios from JSON file."""
        try:
            with open(self.evals_file, 'r') as f:
                evals = json.load(f)
            
            # Extract mock current date if present
            self.mock_current_date = evals.get("mock_current_date")
            if self.mock_current_date:
                logger.info(f"📅 Using mock current date: {self.mock_current_date}")
                
            logger.info(f"✅ Loaded {len(evals['test_scenarios'])} test scenarios")
            return evals
        except Exception as e:
            logger.error(f"❌ Failed to load evals: {e}")
            return {}
    
    def run_query(self, user_input: str, athlete_id: int = 149225109) -> Dict[str, Any]:
        """Run a query through the system."""
        try:
            classify_agent, sql_agent, response_agent, table_response_agent, clarify_agent = self.agents
            result = process_query(
                classify_agent, sql_agent, response_agent, table_response_agent, clarify_agent,
                user_input, athlete_id
            )
            return result
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def assert_classification(self, test_id: str, turn_index: int, expected: str, actual: QueryType) -> TestResult:
        """Assert that classification matches expected value."""
        passed = actual.value == expected.lower()
        return TestResult(
            test_id=test_id,
            turn_index=turn_index,
            assertion_type="classification",
            assertion_details=expected,
            passed=passed,
            actual_value=actual.value,
            expected_value=expected.lower(),
            error_message=None if passed else f"Expected {expected}, got {actual.value}"
        )
    
    def assert_text_contains(self, test_id: str, turn_index: int, expected_phrases: List[str], actual_text: str) -> List[TestResult]:
        """Assert that text contains expected phrases."""
        results = []
        for phrase in expected_phrases:
            passed = any(phrase.lower() in actual_text.lower() for phrase in [phrase])
            results.append(TestResult(
                test_id=test_id,
                turn_index=turn_index,
                assertion_type="text_contains",
                assertion_details=phrase,
                passed=passed,
                actual_value=actual_text,
                expected_value=phrase,
                error_message=None if passed else f"Text does not contain '{phrase}'"
            ))
        return results
    
    def assert_text_contains_any(self, test_id: str, turn_index: int, expected_phrases: List[str], actual_text: str) -> TestResult:
        """Assert that text contains ANY of the expected phrases (OR logic)."""
        passed = any(phrase.lower() in actual_text.lower() for phrase in expected_phrases)
        return TestResult(
            test_id=test_id,
            turn_index=turn_index,
            assertion_type="text_contains_any",
            assertion_details=expected_phrases,
            passed=passed,
            actual_value=actual_text,
            expected_value=f"ANY of: {expected_phrases}",
            error_message=None if passed else f"Text does not contain any of: {expected_phrases}"
        )
    
    def assert_text_not_contains(self, test_id: str, turn_index: int, forbidden_phrases: List[str], actual_text: str) -> List[TestResult]:
        """Assert that text does not contain forbidden phrases."""
        results = []
        for phrase in forbidden_phrases:
            passed = phrase.lower() not in actual_text.lower()
            results.append(TestResult(
                test_id=test_id,
                turn_index=turn_index,
                assertion_type="text_not_contains",
                assertion_details=phrase,
                passed=passed,
                actual_value=actual_text,
                expected_value=f"NOT {phrase}",
                error_message=None if passed else f"Text contains forbidden phrase '{phrase}'"
            ))
        return results
    
    def assert_table_row_count(self, test_id: str, turn_index: int, expected_count: int, actual_data: pd.DataFrame) -> TestResult:
        """Assert that table has expected number of rows."""
        if actual_data is None:
            return TestResult(
                test_id=test_id,
                turn_index=turn_index,
                assertion_type="table_row_count",
                assertion_details=expected_count,
                passed=False,
                actual_value=None,
                expected_value=expected_count,
                error_message="No table data returned"
            )
        
        actual_count = len(actual_data)
        passed = actual_count == expected_count
        return TestResult(
            test_id=test_id,
            turn_index=turn_index,
            assertion_type="table_row_count",
            assertion_details=expected_count,
            passed=passed,
            actual_value=actual_count,
            expected_value=expected_count,
            error_message=None if passed else f"Expected {expected_count} rows, got {actual_count}"
        )
    
    def assert_table_columns(self, test_id: str, turn_index: int, expected_columns: List[str], actual_data: pd.DataFrame) -> TestResult:
        """Assert that table has expected columns."""
        if actual_data is None:
            return TestResult(
                test_id=test_id,
                turn_index=turn_index,
                assertion_type="table_columns",
                assertion_details=expected_columns,
                passed=False,
                actual_value=None,
                expected_value=expected_columns,
                error_message="No table data returned"
            )
        
        actual_columns = list(actual_data.columns)
        passed = all(col in actual_columns for col in expected_columns)
        return TestResult(
            test_id=test_id,
            turn_index=turn_index,
            assertion_type="table_columns",
            assertion_details=expected_columns,
            passed=passed,
            actual_value=actual_columns,
            expected_value=expected_columns,
            error_message=None if passed else f"Missing columns: {set(expected_columns) - set(actual_columns)}"
        )
    
    def assert_date_range(self, test_id: str, turn_index: int, date_range: str, actual_data: pd.DataFrame) -> TestResult:
        """Assert that table data falls within expected date range."""
        if actual_data is None:
            return TestResult(
                test_id=test_id,
                turn_index=turn_index,
                assertion_type="date_range",
                assertion_details=date_range,
                passed=False,
                actual_value=None,
                expected_value=date_range,
                error_message="No table data returned"
            )
        
        # Parse date range (e.g., "last_week", "2023-11-01:2023-11-30")
        try:
            start_date, end_date = self._parse_date_range(date_range)
            
            # Check if data has date column
            date_columns = [col for col in actual_data.columns if 'date' in col.lower() or 'start' in col.lower()]
            if not date_columns:
                return TestResult(
                    test_id=test_id,
                    turn_index=turn_index,
                    assertion_type="date_range",
                    assertion_details=date_range,
                    passed=False,
                    actual_value="No date column found",
                    expected_value=date_range,
                    error_message="No date column found in table data"
                )
            
            date_col = date_columns[0]
            actual_dates = pd.to_datetime(actual_data[date_col])
            
            # Handle timezone issues - convert to timezone-naive if needed
            if actual_dates.dt.tz is not None:
                actual_dates = actual_dates.dt.tz_localize(None)
            
            # Convert to date-only for comparison (ignore time component)
            actual_dates_only = actual_dates.dt.date
            start_date_only = start_date.date()
            end_date_only = end_date.date()
            
            # Check if all dates are within range
            passed = all((actual_dates_only >= start_date_only) & (actual_dates_only <= end_date_only))
            
            return TestResult(
                test_id=test_id,
                turn_index=turn_index,
                assertion_type="date_range",
                assertion_details=date_range,
                passed=passed,
                actual_value=f"{actual_dates.min()} to {actual_dates.max()}",
                expected_value=f"{start_date} to {end_date}",
                error_message=None if passed else f"Some dates outside range {start_date} to {end_date}"
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                turn_index=turn_index,
                assertion_type="date_range",
                assertion_details=date_range,
                passed=False,
                actual_value=str(e),
                expected_value=date_range,
                error_message=f"Date range validation failed: {str(e)}"
            )
    
    def _get_current_date(self) -> datetime:
        """Get current date, using mock date if set."""
        if self.mock_current_date:
            return datetime.strptime(self.mock_current_date, "%Y-%m-%d")
        return datetime.now()
    
    def _parse_date_range(self, date_range: str) -> tuple:
        """Parse date range string into start and end dates."""
        now = self._get_current_date()
        
        if date_range == "last_week":
            end_date = now - timedelta(days=now.weekday() + 1)  # Last Sunday
            start_date = end_date - timedelta(days=6)  # Previous Monday
        elif date_range == "this_week":
            start_date = now - timedelta(days=now.weekday())  # This Monday
            end_date = start_date + timedelta(days=6)  # This Sunday
        elif ":" in date_range:
            # Format: "2023-11-01:2023-11-30"
            start_str, end_str = date_range.split(":")
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
        else:
            raise ValueError(f"Unsupported date range format: {date_range}")
        
        return start_date, end_date
    
    def run_turn(self, scenario_id: str, turn_index: int, turn_data: Dict[str, Any]) -> tuple:
        """Run a single turn and evaluate all assertions. Returns (results, sql_query)."""
        results = []
        
        # Execute the query
        user_input = turn_data["user_input"]
        logger.info(f"🔄 Running query: {user_input}")
        
        query_result = self.run_query(user_input)
        
        if not query_result.get("success", False):
            # If query failed, mark all assertions as failed
            for key in turn_data:
                if key.startswith("expected_"):
                    results.append(TestResult(
                        test_id=scenario_id,
                        turn_index=turn_index,
                        assertion_type=key,
                        assertion_details=turn_data[key],
                        passed=False,
                        actual_value="Query failed",
                        expected_value=turn_data[key],
                        error_message=f"Query execution failed: {query_result.get('error', 'Unknown error')}"
                    ))
            return results, query_result.get("sql_query", "")
        
        # Extract actual values
        classification = query_result.get("classification", {})
        response_text = query_result.get("response_text", "")
        table_data = query_result.get("data")
        sql_query = query_result.get("sql_query", "")
        
        # Log classification explanation for debugging unexpected CLARIFY results
        if hasattr(classification, 'query_type') and classification.query_type.value == "clarify":
            explanation = getattr(classification, 'explanation', 'No explanation available')
            logger.warning(f"🔍 Query '{user_input}' classified as CLARIFY: {explanation}")
        
        # Run assertions based on what's present in the turn data
        for key, value in turn_data.items():
            if key == "expected_classification":
                results.append(self.assert_classification(scenario_id, turn_index, value, classification.query_type))
            
            elif key == "expected_text_contains":
                results.extend(self.assert_text_contains(scenario_id, turn_index, value, response_text))
            
            elif key == "expected_text_contains_any":
                results.append(self.assert_text_contains_any(scenario_id, turn_index, value, response_text))
            
            elif key == "expected_text_not_contains":
                results.extend(self.assert_text_not_contains(scenario_id, turn_index, value, response_text))
            
            elif key == "table_expected_row_count":
                results.append(self.assert_table_row_count(scenario_id, turn_index, value, table_data))
            
            elif key == "table_expected_columns":
                results.append(self.assert_table_columns(scenario_id, turn_index, value, table_data))
            
            elif key == "table_expected_date_range":
                results.append(self.assert_date_range(scenario_id, turn_index, value, table_data))
        
        return results, sql_query
    
    def run_scenario(self, scenario: Dict[str, Any]) -> ScenarioResult:
        """Run a complete test scenario."""
        scenario_id = scenario["id"]
        description = scenario["description"]
        turns = scenario["turns"]
        
        logger.info(f"🚀 Running scenario: {scenario_id}")
        
        all_results = []
        scenario_sql_query = ""
        scenario_user_query = ""
        
        for turn_index, turn_data in enumerate(turns):
            turn_results, sql_query = self.run_turn(scenario_id, turn_index, turn_data)
            all_results.extend(turn_results)
            if sql_query:  # Capture the first non-empty SQL query
                scenario_sql_query = sql_query
            if not scenario_user_query:  # Capture the first user query
                scenario_user_query = turn_data.get("user_input", "")
        
        # Calculate statistics
        total_assertions = len(all_results)
        passed_assertions = sum(1 for r in all_results if r.passed)
        failed_assertions = total_assertions - passed_assertions
        
        scenario_result = ScenarioResult(
            scenario_id=scenario_id,
            description=description,
            total_assertions=total_assertions,
            passed_assertions=passed_assertions,
            failed_assertions=failed_assertions,
            test_results=all_results,
            sql_query=scenario_sql_query,
            user_query=scenario_user_query
        )
        
        # Log results
        logger.info(f"✅ Scenario {scenario_id}: {passed_assertions}/{total_assertions} assertions passed ({scenario_result.success_rate:.1%})")
        
        return scenario_result
    
    def run_all_scenarios(self) -> Dict[str, Any]:
        """Run all test scenarios and return summary."""
        evals = self.load_evals()
        if not evals:
            return {"error": "Failed to load evals"}
        
        if not self.initialize_system():
            return {"error": "Failed to initialize system"}
        
        self.scenario_results = []
        
        for scenario in evals["test_scenarios"]:
            scenario_result = self.run_scenario(scenario)
            self.scenario_results.append(scenario_result)
        
        # Calculate overall statistics
        total_scenarios = len(self.scenario_results)
        successful_scenarios = sum(1 for s in self.scenario_results if s.failed_assertions == 0)
        total_assertions = sum(s.total_assertions for s in self.scenario_results)
        passed_assertions = sum(s.passed_assertions for s in self.scenario_results)
        
        summary = {
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "total_assertions": total_assertions,
            "passed_assertions": passed_assertions,
            "overall_success_rate": passed_assertions / total_assertions if total_assertions > 0 else 0.0,
            "scenario_results": self.scenario_results
        }
        
        logger.info(f"🎯 Overall Results: {passed_assertions}/{total_assertions} assertions passed ({summary['overall_success_rate']:.1%})")
        logger.info(f"📊 Scenarios: {successful_scenarios}/{total_scenarios} fully successful")
        
        return summary
    
    def generate_report(self, output_file: str = "test_report.json"):
        """Generate a detailed test report."""
        # Make output file relative to this script's directory if no path specified
        if not os.path.dirname(output_file):
            output_file = os.path.join(os.path.dirname(__file__), output_file)
        summary = self.run_all_scenarios()
        
        # Convert results to serializable format
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_scenarios": summary["total_scenarios"],
                "successful_scenarios": summary["successful_scenarios"],
                "total_assertions": summary["total_assertions"],
                "passed_assertions": summary["passed_assertions"],
                "overall_success_rate": summary["overall_success_rate"]
            },
            "scenarios": []
        }
        
        for scenario_result in summary["scenario_results"]:
            scenario_data = {
                "id": scenario_result.scenario_id,
                "description": scenario_result.description,
                "user_query": scenario_result.user_query,
                "sql_query": scenario_result.sql_query,
                "success_rate": scenario_result.success_rate,
                "total_assertions": scenario_result.total_assertions,
                "passed_assertions": scenario_result.passed_assertions,
                "failed_assertions": scenario_result.failed_assertions,
                "test_results": [
                    {
                        "assertion_type": tr.assertion_type,
                        "passed": tr.passed,
                        "expected": tr.expected_value,
                        "actual": tr.actual_value,
                        "error": tr.error_message
                    }
                    for tr in scenario_result.test_results
                ]
            }
            report["scenarios"].append(scenario_data)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Report saved to {output_file}")
        
        # Generate HTML report for better visualization
        try:
            from .html_report_generator import generate_html_report
            html_file = output_file.replace('.json', '.html')
            generate_html_report(output_file, html_file)
            logger.info(f"🌐 HTML report saved to {html_file}")
        except ImportError:
            logger.warning("HTML report generator not available")
        
        return report


if __name__ == "__main__":
    # Example usage
    runner = EvalTestRunner()
    report = runner.generate_report()
    
    # Print summary
    print(f"\n🎯 Test Summary:")
    print(f"Scenarios: {report['summary']['successful_scenarios']}/{report['summary']['total_scenarios']} successful")
    print(f"Assertions: {report['summary']['passed_assertions']}/{report['summary']['total_assertions']} passed")
    print(f"Overall Success Rate: {report['summary']['overall_success_rate']:.1%}")