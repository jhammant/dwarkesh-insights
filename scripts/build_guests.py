#!/usr/bin/env python3
"""
Build guests.json from insight files.
Cleans bad names, builds proper episode titles, deduplicates.
"""

import json
import re
import os
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
INSIGHTS_DIR = ROOT / "data" / "insights"

def load_config(config_path=None):
    if config_path:
        with open(config_path) as f:
            return json.load(f)
    # Try default
    default = ROOT / "config.json"
    if default.exists():
        with open(default) as f:
            return json.load(f)
    return {
        "short_name": "Podcast",
        "bad_guest_names": ["Not applicable", "Not provided", "N/A", "Various",
                           "Unknown", "Multiple", "null", "undefined", ""],
        "bad_episode_titles": ["N/A", "Unknown", "Episode", "null", "undefined", ""],
        "episode_title_builder": "#{number} — {guest}",
        "slug": ""
    }

def fix_episode_title(title, episode_id, guest_name, config):
    """Fix bad episode titles using episode ID and guest name."""
    bad_titles = config.get('bad_episode_titles', [])
    podcast_name = config.get('podcast_name', '')
    short_name = config.get('short_name', 'Episode')
    
    is_bad = (
        not title or 
        title in bad_titles or 
        title == podcast_name or
        title.startswith('Episode #')
    )
    
    if not is_bad:
        return title
    
    # Build from episode_id
    match = re.match(r'^(\d+)', episode_id or '')
    num = match.group(1) if match else ''
    guest = guest_name if guest_name and guest_name not in config.get('bad_guest_names', []) else ''
    
    template = config.get('episode_title_builder', '#{number} — {guest}')
    
    if num and guest:
        return template.replace('{number}', num).replace('{guest}', guest).replace('{short_name}', short_name)
    elif num:
        return f"{short_name} #{num}"
    elif guest:
        return f"{short_name} — {guest}"
    return f"{short_name} Episode"

def build_guests(config):
    """Build guests.json from insight files."""
    bad_names = set(config.get('bad_guest_names', []))
    bad_names.add(None)
    
    guests = defaultdict(lambda: {
        'episodes': [],
        'insights_count': 0,
        'advice_count': 0,
        'contrarian_count': 0,
        'topics': [],
        'expertise': 'Various Topics'
    })
    
    files = sorted(INSIGHTS_DIR.glob("*.json"))
    print(f"Processing {len(files)} insight files...")
    
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        
        guest = data.get('guest_name', '') or data.get('guest', '')
        if guest in bad_names:
            continue
        
        episode_id = data.get('episode_id', f.stem)
        raw_title = data.get('episode_title', '')
        title = fix_episode_title(raw_title, episode_id, guest, config)
        
        slug = config.get('source_config', {}).get('podscripts_slug', config.get('slug', ''))
        url = f"https://podscripts.co/podcasts/{slug}/{episode_id}" if slug else ''
        
        g = guests[guest]
        
        # Avoid duplicate episodes
        existing_ids = {ep['episode_id'] for ep in g['episodes']}
        if episode_id not in existing_ids:
            g['episodes'].append({
                'title': title,
                'url': url,
                'episode_id': episode_id
            })
        
        g['insights_count'] += len(data.get('key_insights', []))
        g['advice_count'] += len(data.get('actionable_advice', []))
        g['contrarian_count'] += len(data.get('contrarian_claims', []))
        g['topics'].extend(data.get('topics', []))
        
        if data.get('expertise_area') and data['expertise_area'] != 'Unknown':
            g['expertise'] = data['expertise_area']
    
    # Build final list
    result = []
    for name, data in sorted(guests.items(), key=lambda x: len(x[1]['episodes']), reverse=True):
        # Deduplicate topics
        topic_counts = defaultdict(int)
        for t in data['topics']:
            topic_counts[t] += 1
        top_topics = sorted(topic_counts.keys(), key=lambda x: topic_counts[x], reverse=True)[:10]
        
        result.append({
            'name': name,
            'episode_count': len(data['episodes']),
            'episodes': data['episodes'],
            'insights_count': data['insights_count'],
            'advice_count': data['advice_count'],
            'contrarian_count': data['contrarian_count'],
            'topics': top_topics,
            'expertise': data['expertise'],
            'top_insights': []  # Could populate from data
        })
    
    return result

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=None)
    args = parser.parse_args()
    
    config = load_config(args.config)
    guests = build_guests(config)
    
    # Write to both docs/data/ and web/data/
    for out_dir in [ROOT / "docs" / "data", ROOT / "web" / "data"]:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "guests.json"
        with open(out_path, 'w') as f:
            json.dump(guests, f, indent=2)
    
    print(f"\n✅ Generated guests.json:")
    print(f"   - {len(guests)} guests")
    total_eps = sum(g['episode_count'] for g in guests)
    print(f"   - Total episodes: {total_eps}")
    
    short = config.get('short_name', 'Podcast')
    print(f"\n🎤 Top 10 guests by episode count:")
    for i, g in enumerate(guests[:10]):
        print(f"   {i+1}. {g['name']}: {g['episode_count']} episodes")

if __name__ == '__main__':
    main()
