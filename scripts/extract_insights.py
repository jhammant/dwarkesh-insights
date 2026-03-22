#!/usr/bin/env python3
"""
Scrape Dwarkesh transcripts from podscripts.co and extract insights via Gemini.
Does NOT store full transcripts (legal compliance).
"""

import json
import os
import sys
import time
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

try:
    import google.genai as genai
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-genai"])
    import google.genai as genai

EPISODES_FILE = Path(__file__).parent.parent / "data" / "episodes.json"
INSIGHTS_DIR = Path(__file__).parent.parent / "data" / "insights"
API_KEY_FILE = Path.home() / ".config" / "gemini" / "api-key.json"
PROGRESS_FILE = Path(__file__).parent.parent / "data" / "progress.json"

INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# Load API key
with open(API_KEY_FILE) as f:
    API_KEY = json.load(f)['apiKey']

client = genai.Client(api_key=API_KEY)

EXTRACTION_PROMPT = """
Analyze this Dwarkesh Podcast podcast transcript and extract structured insights. Return ONLY valid JSON.

{
  "guest_name": "Full name of the guest (NOT Joe Rogan)",
  "expertise_area": "Primary expertise",
  "episode_title": "Episode title",
  "key_insights": [
    {"insight": "One sentence summary", "quote": "Best direct quote supporting this (verbatim from transcript)", "importance": "high/medium/low"}
  ],
  "topics": ["topic1", "topic2"],
  "actionable_advice": [
    {"advice": "Specific recommendation", "how_to": "How to implement"}
  ],
  "contrarian_claims": [
    {"claim": "Surprising or contrarian viewpoint", "context": "Why it's contrarian"}
  ]
}

Keep quotes SHORT (1-3 sentences max). Extract 3-8 key insights, 2-5 advice items, and any contrarian claims.

TRANSCRIPT:
"""


class TranscriptParser(HTMLParser):
    """Extract transcript text from podscripts.co episode page"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_transcript = False
        self.depth = 0
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')
        if 'transcript' in cls.lower() or 'episode-text' in cls.lower():
            self.in_transcript = True
            self.depth = 0
        if self.in_transcript:
            self.depth += 1
            
    def handle_endtag(self, tag):
        if self.in_transcript:
            self.depth -= 1
            if self.depth <= 0:
                self.in_transcript = False
                
    def handle_data(self, data):
        if self.in_transcript:
            text = data.strip()
            if text:
                self.text_parts.append(text)


def fetch_transcript(url):
    """Fetch and extract transcript text from podscripts.co"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        parser = TranscriptParser()
        parser.feed(html)
        
        if parser.text_parts:
            return ' '.join(parser.text_parts)
        
        # Fallback: find large text blocks
        # Remove HTML tags and find the main content
        clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # Take the middle chunk (skip nav/header/footer)
        if len(clean) > 2000:
            return clean[500:-500]
        return clean if len(clean) > 200 else None
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def extract_insights(transcript, episode):
    """Use Gemini to extract insights from transcript"""
    # Truncate to ~30k chars (Gemini context limit consideration)
    if len(transcript) > 30000:
        transcript = transcript[:30000]
    
    prompt = EXTRACTION_PROMPT + transcript
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        text = response.text.strip()
        # Clean markdown wrapping
        if text.startswith('```'):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
        
        data = json.loads(text)
        data['episode_id'] = episode.get('slug', '')
        data['episode_url'] = episode.get('url', '')
        
        # Override guest_name with episode title (Gemini often fails on this)
        title = episode.get('title', '')
        if title:
            import re as _re
            title_guest = _re.sub(r'^#?\d+\s*[-–—]\s*', '', title).strip()
            title_guest = _re.sub(r'\s*\(.*?\)\s*$', '', title_guest)
            title_guest = _re.sub(r'\s*-\s*MMA Show.*$', '', title_guest, flags=_re.IGNORECASE)
            if title_guest and len(title_guest) > 1:
                data['guest_name'] = title_guest
                data['_name_source'] = 'episode_title'
        
        return data
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  Gemini error: {e}")
        if '429' in str(e) or 'quota' in str(e).lower():
            print("  Rate limited, waiting 60s...")
            time.sleep(60)
        return None


def load_progress():
    if PROGRESS_FILE.exists():
        return json.load(open(PROGRESS_FILE))
    return {'completed': [], 'failed': []}


def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


def main():
    episodes = json.load(open(EPISODES_FILE))
    progress = load_progress()
    
    # Skip already processed
    done = set(progress['completed'])
    remaining = [ep for ep in episodes if ep.get('slug', '') not in done]
    
    print(f"Total: {len(episodes)}, Done: {len(done)}, Remaining: {len(remaining)}")
    
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    count = 0
    
    for ep in remaining:
        if count >= batch_size:
            print(f"\nBatch limit ({batch_size}) reached. Run again to continue.")
            break
            
        slug = ep.get('slug', '')
        url = ep.get('url', f"https://podscripts.co/podcasts/the-joe-rogan-experience/{slug}")
        title = ep.get('title', slug)
        
        print(f"\n[{count+1}/{batch_size}] {title}")
        
        # 1. Fetch transcript (not stored)
        transcript = fetch_transcript(url)
        if not transcript or len(transcript) < 200:
            print(f"  Skipped — no/short transcript")
            progress['failed'].append(slug)
            save_progress(progress)
            continue
        
        print(f"  Transcript: {len(transcript)} chars")
        
        # 2. Extract insights via Gemini
        insights = extract_insights(transcript, ep)
        if not insights:
            print(f"  Skipped — extraction failed")
            progress['failed'].append(slug)
            save_progress(progress)
            continue
        
        # 3. Save insights only (NOT transcript)
        out_file = INSIGHTS_DIR / f"{slug}.json"
        with open(out_file, 'w') as f:
            json.dump(insights, f, indent=2)
        
        print(f"  ✅ Saved: {insights.get('guest_name', '?')} — {len(insights.get('key_insights', []))} insights")
        
        progress['completed'].append(slug)
        save_progress(progress)
        count += 1
        
        # Rate limit: ~2s between requests
        time.sleep(2)
    
    print(f"\n{'='*50}")
    print(f"Done: {len(progress['completed'])} total, {count} this run")
    print(f"Failed: {len(progress['failed'])}")


if __name__ == '__main__':
    main()
