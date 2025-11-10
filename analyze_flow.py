import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

CACHE_DIR = Path('.cache')
CACHE_DIR.mkdir(exist_ok=True)


def get_cache_key(data: Any) -> str:
    """Generate a unique cache key from data."""
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


def get_cached(key: str) -> Any:
    """Get cached data if it exists."""
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        return json.load(open(cache_file))
    return None


def set_cache(key: str, data: Any):
    """Save data to cache."""
    cache_file = CACHE_DIR / f"{key}.json"
    json.dump(data, open(cache_file, 'w'), indent=2)


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
    
    def generate_summary(self, interactions: List[Dict[str, Any]]) -> str:
        """Generate summary using GPT-4 (with caching)."""
        cache_key = get_cache_key({
            'task': 'summary',
            'flow_name': self.flow_data.get('name', ''),
            'interactions': interactions
        })
        
        cached = get_cached(cache_key)
        if cached:
            print("Using cached summary")
            return cached['summary']
        
        # Build prompt
        flow_name = self.flow_data.get('name', 'Unknown Flow')
        action_list = "\n".join([f"{idx+1}. {interaction['action']}" for idx, interaction in enumerate(interactions)])
        
        prompt = f"""Analyze this Arcade flow and provide a summary.

        Flow: {flow_name}
        Actions: {action_list}

        Provide: 1) What the user was trying to accomplish, 2) Key steps taken, 3) Behavioral insights.
        Write in a friendly, professional tone."""
        
        print("⏳ Generating summary with GPT-4...")
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "Expert at analyzing user behavior and creating clear summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        summary = response.choices[0].message.content.strip()
        set_cache(cache_key, {'summary': summary})
        print("Summary generated successfully")
        return summary
    
    def generate_social_media_image(self, summary: str) -> str:
        """Generate social media image using DALL-E (with caching)."""
        flow_name = self.flow_data.get('name', 'Arcade Flow')
        cache_key = get_cache_key({'task': 'image', 'flow_name': flow_name, 'summary': summary})
        
        cached = get_cached(cache_key)
        image_url = None
        
        if cached:
            print("Checking cached image URL...")
            try:
                test_response = requests.head(cached['image_url'], timeout=5)
                if test_response.status_code == 200:
                    print("Using cached image URL")
                    image_url = cached['image_url']
                else:
                    print("Cached URL expired, generating new image...")
            except:
                print("Cached URL expired, generating new image...")
        
        if not image_url:
            prompt = f"""Create a modern social media image for: {flow_name}
                        
            Show: Clean e-commerce interface, shopping journey (search bar, products, cart), 
            vibrant colors (blues, reds, whites), user interactions, professional look.
            No text in image. Style: Modern, minimal, engaging.
            
            """
            
            print("Generating image with DALL-E...")
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            image_url = response.data[0].url
            set_cache(cache_key, {'image_url': image_url})
        
        filename = f"flow_social_media_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        print(f"Downloading to {filename}...")
        response = requests.get(image_url)
        
        if response.status_code != 200 or response.headers.get('content-type', '').startswith('text/'):
            raise Exception("Failed to download image - URL may have expired")
        
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    
    def generate_report(self) -> str:
        """Generate markdown report."""
        print("Analyzing flow...")
        interactions = self.extract_user_interactions()
        
        print("Generating summary...")
        summary = self.generate_summary(interactions)
        
        print("Creating social media image...")
        image_filename = self.generate_social_media_image(summary)
        
        flow_name = self.flow_data.get('name', 'Unknown Flow')
        report = f"""# Arcade Flow Analysis Report

        **Flow Name:** {flow_name}
        **Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

        ---

        ## Overview

        {summary}

        ---

        ## User Interactions

        """

        for i, interaction in enumerate(interactions, 1):
            report += f"{i}. **{interaction['action']}**\n"
            if interaction.get('details'):
                report += f"   - _{interaction['details']}_\n"
            report += "\n"
        
        report += f"""---

        ## Key Insights

        This flow demonstrates a user journey where the user:
        - Navigated through the interface
        - Interacted with various elements
        - Completed their intended task

        The flow showcases an intuitive user experience with clear interactions at each step.

        ---

        ## Social Media Image

        ![Flow Social Media Image](./{image_filename})


        ## Flow Statistics

        - **Total Steps:** {len(self.flow_data.get('steps', []))}
        - **User Interactions:** {len(interactions)}
        - **Flow Type:** {self.flow_data.get('useCase', 'Unknown')}

        ---
        """
        return report


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
        report = analyzer.generate_report()
        
        with open('FLOW_REPORT.md', 'w') as f:
            f.write(report)
        
        print("\nAnalysis complete!")
        print("Report saved to: FLOW_REPORT.md")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()