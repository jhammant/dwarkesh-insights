#!/usr/bin/env python3
"""
Tier 2 Consensus Finder: Add canonical claims to insights, then find real cross-guest agreement.

Phase 1: For each insight file, ask Gemini to tag each key_insight with a canonical_claim
         (a normalized 8-12 word statement of the core claim).
Phase 2: Group by canonical_claim, rank by unique guest count.
Phase 3: Output validated_consensus.json — things 3+ guests independently agree on.

Uses Gemini 2.0 Flash free tier. ~1 API call per insight file.
"""

import json
import time
import sys
import os
from pathlib import Path
from collections import defaultdict
import argparse

# Setup Gemini
try:
    import google.genai as genai
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-genai"])
    import google.genai as genai

API_KEY_FILE = Path.home() / ".config" / "gemini" / "api-key.json"

def load_api_key():
    if API_KEY_FILE.exists():
        data = json.loads(API_KEY_FILE.read_text())
        return data.get('apiKey', data.get('api_key', ''))
    return os.environ.get('GEMINI_API_KEY', '')

API_KEY = load_api_key()
if not API_KEY:
    print("❌ No Gemini API key found")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)

PROMPT_TEMPLATE = """You are analyzing podcast insights to find consensus across episodes.

For each insight below, generate a "canonical_claim" — a normalized 8-12 word statement of the CORE FACTUAL OR OPINION CLAIM being made. 

Rules:
- Strip guest-specific context, make it universal
- Use present tense, declarative form
- Be specific enough that only genuinely similar claims match
- BAD: "Exercise is good" (too vague)
- GOOD: "Regular cold exposure significantly improves mental resilience"
- BAD: "Sleep matters" (too vague)  
- GOOD: "Consistent sleep schedule matters more than total sleep hours"

Guest: {guest}
Episode: {episode}

Insights to canonicalize:
{insights_text}

Return ONLY a JSON array of objects, one per insight:
[
  {{"original": "the original insight text", "canonical_claim": "the 8-12 word canonical claim", "category": "one of: health, psychology, business, science, society, technology, philosophy, relationships, creativity, politics, other"}}
]

Return ONLY valid JSON, no markdown, no explanation."""


def process_insight_file(filepath, delay=4.0):
    """Add canonical claims to all insights in a file."""
    with open(filepath) as f:
        data = json.load(f)
    
    # Skip if already processed
    if data.get('_consensus_processed'):
        return data, True
    
    insights = data.get('key_insights', [])
    if not insights:
        return data, True
    
    guest = data.get('guest_name', 'Unknown')
    episode = data.get('episode_title', 'Unknown')
    
    insights_text = "\n".join(f"- {i['insight']}" for i in insights)
    
    prompt = PROMPT_TEMPLATE.format(
        guest=guest,
        episode=episode,
        insights_text=insights_text
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        text = response.text.strip()
        # Clean markdown wrapping
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
        
        canonical_data = json.loads(text)
        
        # Merge canonical claims back into insights
        for i, insight in enumerate(insights):
            if i < len(canonical_data):
                insight['canonical_claim'] = canonical_data[i].get('canonical_claim', '')
                insight['claim_category'] = canonical_data[i].get('category', 'other')
        
        data['_consensus_processed'] = True
        
        # Save back
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        time.sleep(delay)
        return data, True
        
    except Exception as e:
        if '429' in str(e) or 'quota' in str(e).lower():
            print(f"  Rate limited, waiting 60s...")
            time.sleep(60)
            return data, False  # Signal retry
        print(f"  Error: {e}")
        time.sleep(delay)
        return data, False


def build_consensus(insights_dir, min_guests=3):
    """Phase 2: Group by canonical claim and find real consensus."""
    claim_groups = defaultdict(list)
    
    for filepath in sorted(insights_dir.glob("*.json")):
        with open(filepath) as f:
            data = json.load(f)
        
        guest = data.get('guest_name', 'Unknown')
        episode_id = data.get('episode_id', '')
        episode_title = data.get('episode_title', '')
        
        for insight in data.get('key_insights', []):
            claim = insight.get('canonical_claim', '').strip().lower()
            if not claim:
                continue
            
            claim_groups[claim].append({
                'guest': guest,
                'episode_id': episode_id,
                'episode_title': episode_title,
                'original_insight': insight['insight'],
                'quote': insight.get('quote', ''),
                'importance': insight.get('importance', 'medium'),
                'category': insight.get('claim_category', 'other')
            })
    
    # Filter to claims with multiple unique guests
    consensus = []
    for claim, entries in claim_groups.items():
        unique_guests = list(set(e['guest'] for e in entries if e['guest'] and e['guest'] != 'Unknown'))
        if len(unique_guests) >= min_guests:
            # Pick best examples (one per guest, prefer high importance + quotes)
            seen = set()
            examples = []
            for e in sorted(entries, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x['importance'], 0), reverse=True):
                if e['guest'] not in seen:
                    seen.add(e['guest'])
                    examples.append(e)
                if len(examples) >= 5:
                    break
            
            consensus.append({
                'canonical_claim': claim,
                'category': entries[0].get('category', 'other'),
                'guest_count': len(unique_guests),
                'total_mentions': len(entries),
                'guests': sorted(unique_guests),
                'examples': examples
            })
    
    # Sort by guest count (most agreement first)
    consensus.sort(key=lambda x: x['guest_count'], reverse=True)
    
    return consensus


def main():
    parser = argparse.ArgumentParser(description='Find real consensus across podcast episodes')
    parser.add_argument('--insights-dir', type=Path, required=True, help='Path to insights directory')
    parser.add_argument('--output', type=Path, help='Output file (default: data/analysis/validated_consensus.json)')
    parser.add_argument('--delay', type=float, default=4.0, help='Delay between API calls')
    parser.add_argument('--min-guests', type=int, default=3, help='Minimum guests for consensus')
    parser.add_argument('--skip-tagging', action='store_true', help='Skip Phase 1, just build from existing tags')
    parser.add_argument('--limit', type=int, help='Limit number of files to process')
    args = parser.parse_args()
    
    insights_dir = args.insights_dir
    output = args.output or insights_dir.parent / "analysis" / "validated_consensus.json"
    
    if not args.skip_tagging:
        # Phase 1: Tag insights with canonical claims
        files = sorted(insights_dir.glob("*.json"))
        if args.limit:
            files = files[:args.limit]
        
        total = len(files)
        processed = 0
        skipped = 0
        failed = 0
        
        print(f"Phase 1: Tagging {total} files with canonical claims...")
        print(f"  Delay: {args.delay}s (free tier: 15 RPM, 1500 RPD)")
        
        for filepath in files:
            # Check if already processed
            with open(filepath) as f:
                data = json.load(f)
            
            if data.get('_consensus_processed'):
                skipped += 1
                continue
            
            data, success = process_insight_file(filepath, args.delay)
            
            if success:
                processed += 1
            else:
                # Retry once
                data, success = process_insight_file(filepath, args.delay * 2)
                if success:
                    processed += 1
                else:
                    failed += 1
            
            if (processed + failed) % 50 == 0:
                print(f"  Progress: {processed + skipped}/{total} done, {failed} failed")
        
        print(f"\n  Phase 1 complete: {processed} tagged, {skipped} already done, {failed} failed")
    
    # Phase 2: Build consensus
    print(f"\nPhase 2: Finding consensus (min {args.min_guests} guests)...")
    consensus = build_consensus(insights_dir, args.min_guests)
    
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w') as f:
        json.dump(consensus, f, indent=2)
    
    print(f"\n✅ Found {len(consensus)} validated consensus items")
    print(f"   Output: {output}")
    
    if consensus:
        print(f"\n🏆 Top 10 consensus claims:")
        for i, c in enumerate(consensus[:10]):
            print(f"   {i+1}. [{c['guest_count']} guests] {c['canonical_claim']}")
            print(f"      Guests: {', '.join(c['guests'][:5])}")


if __name__ == '__main__':
    main()
