"""
Simple colored terminal viewer for test reports.
"""

import json
import sys


def print_colored_json(data, indent=0):
    """Print JSON with color coding for pass/fail."""
    
    # ANSI color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    spaces = "  " * indent
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "passed":
                color = GREEN if value else RED
                print(f'{spaces}"{key}": {color}{BOLD}{str(value).lower()}{RESET},')
            elif key in ["success_rate", "overall_success_rate"]:
                if isinstance(value, float):
                    percentage = value * 100 if value <= 1 else value
                    if percentage >= 80:
                        color = GREEN
                    elif percentage >= 50:
                        color = YELLOW
                    else:
                        color = RED
                    print(f'{spaces}"{key}": {color}{BOLD}{percentage:.1f}%{RESET},')
                else:
                    print(f'{spaces}"{key}": {value},')
            elif key in ["user_query", "sql_query"]:
                print(f'{spaces}"{CYAN}{key}{RESET}": "{BLUE}{value}{RESET}",')
            elif key == "error" and value:
                print(f'{spaces}"{key}": "{RED}{value}{RESET}",')
            elif isinstance(value, (dict, list)):
                print(f'{spaces}"{key}": {{' if isinstance(value, dict) else f'{spaces}"{key}": [')
                print_colored_json(value, indent + 1)
                print(f'{spaces}}},' if isinstance(value, dict) else f'{spaces}],')
            else:
                print(f'{spaces}"{key}": {json.dumps(value)},')
    
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                print(f'{spaces}{{' if isinstance(item, dict) else f'{spaces}[')
                print_colored_json(item, indent + 1)
                print(f'{spaces}}},' if isinstance(item, dict) else f'{spaces}],')
            else:
                print(f'{spaces}{json.dumps(item)},')


def view_report(report_file: str = "test_report.json"):
    """View test report with colors."""
    try:
        with open(report_file, 'r') as f:
            data = json.load(f)
        
        print(f"\n🧪 StravaTalk Test Report")
        print(f"📄 File: {report_file}")
        print("=" * 50)
        
        print_colored_json(data)
        
    except FileNotFoundError:
        print(f"❌ Report file not found: {report_file}")
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in file: {report_file}")


if __name__ == "__main__":
    report_file = sys.argv[1] if len(sys.argv) > 1 else "test_report.json"
    view_report(report_file)