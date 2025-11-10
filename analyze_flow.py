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
    
    def extract_user_interactions(self) -> List[Dict[str, Any]]:
        """Extract all user interactions from the flow."""
        interactions = []
        
        # Process all steps (can be any type: CHAPTER, IMAGE, VIDEO, etc.)
        for step in self.flow_data.get('steps', []):
            step_type = step.get('type', '')
            action = self._extract_action_from_step(step, step_type)
            if action:
                interactions.append(action)
        
        # Process captured events (typing, scrolling, dragging, etc.)
        for event in self.flow_data.get('capturedEvents', []):
            action = self._extract_action_from_event(event)
            if action:
                interactions.append(action)
        
        return interactions
    
    def _extract_action_from_step(self, step: Dict, step_type: str) -> Dict[str, Any]:
        """Extract action description from any step type."""
        if step_type == 'CHAPTER':
            title = step.get('title', '')
            if title and 'thank you' not in title.lower():
                return {
                    'type': 'chapter',
                    'action': f"Started section: {title}",
                    'details': step.get('subtitle', '')
                }
        
        elif step_type == 'IMAGE':
            hotspots = step.get('hotspots', [])
            click_context = step.get('clickContext', {})
            
            if hotspots and hotspots[0].get('label'):
                return {
                    'type': 'click',
                    'action': hotspots[0]['label'].replace('*', '').strip(),
                    'url': step.get('pageContext', {}).get('url', '')
                }
            
            text = click_context.get('text', '')
            element_type = click_context.get('elementType', '')
            if text or element_type:
                action_text = f"Clicked {element_type}: {text}" if text else f"Clicked {element_type}"
                return {
                    'type': 'click',
                    'action': action_text.strip(),
                    'url': step.get('pageContext', {}).get('url', '')
                }
        
        elif step_type == 'VIDEO':
            # Video steps show motion, details come from captured events
            return None
        
        else:
            if step.get('title'):
                return {
                    'type': step_type.lower(),
                    'action': f"Interacted with {step_type}: {step.get('title')}",
                    'details': step.get('subtitle', '')
                }
        
        return None
    
    def _extract_action_from_event(self, event: Dict) -> Dict[str, Any]:
        """Extract action from captured events."""
        event_type = event.get('type', '')
        
        if event_type == 'typing':
            return {
                'type': 'typing',
                'action': 'Typed search query',
                'details': 'User entered text in search field'
            }
        elif event_type == 'scrolling':
            return {
                'type': 'scroll',
                'action': 'Scrolled page to view more content',
                'details': 'User browsed through available options'
            }
        elif event_type == 'dragging':
            return {
                'type': 'drag',
                'action': 'Dragged element',
                'details': 'User performed drag interaction'
            }
        elif event_type == 'click':
            return {
                'type': 'click',
                'action': 'Clicked on page',
                'details': 'User performed click interaction'
            }
        
        return None


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
        
        # Extract and display user interactions
        print("\n" + "=" * 50)
        print("EXTRACTING USER INTERACTIONS")
        print("=" * 50)
        interactions = analyzer.extract_user_interactions()
        
        print(f"\nFound {len(interactions)} user interactions:\n")
        for i, interaction in enumerate(interactions, 1):
            print(f"{i}. {interaction['action']}")
            if interaction.get('details'):
                print(f"   └─ {interaction['details']}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()