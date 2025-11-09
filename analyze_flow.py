import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

CACHE_DIR = Path('.cache')
CACHE_DIR.mkdir(exist_ok=True)


class FlowAnalyzer:
    def __init__(self, flow_path: str):
        with open(flow_path) as f:
            self.flow_data = json.load(f)
    
    def get_flow_statistics(self) -> Dict[str, Any]:
        """Get basic statistics about the flow."""
        steps = self.flow_data.get('steps', [])
        captured_events = self.flow_data.get('capturedEvents', [])
        
        step_types = {}
        for step in steps:
            step_type = step.get('type', 'UNKNOWN')
            step_types[step_type] = step_types.get(step_type, 0) + 1
        
        return {
            'name': self.flow_data.get('name', 'Unknown Flow'),
            'total_steps': len(steps),
            'captured_events': len(captured_events),
            'step_types': step_types,
            'use_case': self.flow_data.get('useCase', 'Unknown')
        }
    
    def display_flow_info(self):
        """Display basic information about the flow."""
        stats = self.get_flow_statistics()
        
        print(f"\nFlow Name: {stats['name']}")
        print(f"Use Case: {stats['use_case']}")
        print(f"Total Steps: {stats['total_steps']}")
        print(f"Captured Events: {stats['captured_events']}")
        print("\nStep Types:")
        for step_type, count in stats['step_types'].items():
            print(f"  - {step_type}: {count}")


def main():
    print("Arcade Flow Analyzer")
    print("=" * 50)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found. Create a .env file with your API key.")
        sys.exit(1)
    
    if not os.path.exists('flow.json'):
        print("Error: flow.json not found")
        sys.exit(1)
    
    try:
        analyzer = FlowAnalyzer('flow.json')
        print("\nFlow loaded successfully!")
        analyzer.display_flow_info()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()