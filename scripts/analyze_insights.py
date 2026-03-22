#!/usr/bin/env python3
"""
Cross-episode analysis: Find consensus patterns, contradictions, and common themes.
Uses Gemini-assigned topics from extraction (not keyword matching).
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
import re

INSIGHTS_DIR = Path(__file__).parent.parent / "data" / "insights"
ANALYSIS_DIR = Path(__file__).parent.parent / "data" / "analysis"


def load_all_insights():
    """Load all insight files."""
    insights = []
    for file in INSIGHTS_DIR.glob("*.json"):
        with open(file, 'r') as f:
            insights.append(json.load(f))
    return insights


def normalize_topic(topic):
    """Normalize topic names (case, duplicates)."""
    t = topic.strip().title()
    # Merge duplicates
    merges = {
        'Stand-Up Comedy': 'Comedy',
        'Standup Comedy': 'Comedy',
        'Martial Arts': 'MMA',
        'Mixed Martial Arts': 'MMA',
        'Ufo': 'UFOs',
        'Ufos': 'UFOs',
        'Artificial Intelligence': 'AI',
        'Mental Health': 'Mental Health',
        'Social Media': 'Social Media',
        'Conspiracy Theory': 'Conspiracy Theories',
        'Drug Policy': 'Drugs & Policy',
        'Drug Use': 'Drugs & Policy',
        'Drugs': 'Drugs & Policy',
    }
    return merges.get(t, t)


def analyze_topics(all_insights):
    """Analyze topic distribution across episodes."""
    topic_counts = Counter()
    topic_episodes = defaultdict(list)

    for insight in all_insights:
        episode_id = insight['episode_id']
        for topic in insight.get('topics', []):
            nt = normalize_topic(topic)
            topic_counts[nt] += 1
            topic_episodes[nt].append({
                'id': episode_id,
                'title': insight.get('episode_title', ''),
                'guest': insight.get('guest_name', '')
            })

    return {
        'topic_counts': dict(topic_counts.most_common()),
        'topic_episodes': {k: v for k, v in topic_episodes.items()}
    }


def find_consensus_patterns(all_insights, min_episodes=5, top_n=15):
    """
    Find themes discussed across multiple episodes.
    Uses Gemini-assigned topics and picks relevant example insights.
    """
    # Group insights by their assigned topics
    topic_insights = defaultdict(list)
    
    for data in all_insights:
        topics = [normalize_topic(t) for t in data.get('topics', [])]
        
        for insight in data.get('key_insights', []):
            for topic in topics:
                topic_insights[topic].append({
                    'text': insight['insight'],
                    'quote': insight.get('quote', ''),
                    'importance': insight.get('importance', 'medium'),
                    'episode_id': data['episode_id'],
                    'episode_title': data.get('episode_title', ''),
                    'guest': data.get('guest_name', ''),
                    'all_topics': topics
                })

    # Build consensus groups from topics with enough episodes
    consensus_groups = []
    
    for topic, insights in topic_insights.items():
        unique_episodes = set(i['episode_id'] for i in insights)
        unique_guests = set(i['guest'] for i in insights)
        
        if len(unique_episodes) < min_episodes:
            continue
        
        # Pick the best examples: prefer high importance, with quotes, unique guests
        seen_guests = set()
        best_examples = []
        
        # Sort by importance
        importance_rank = {'high': 3, 'medium': 2, 'low': 1}
        sorted_insights = sorted(insights, key=lambda x: importance_rank.get(x['importance'], 0), reverse=True)
        
        for ins in sorted_insights:
            if ins['guest'] in seen_guests:
                continue
            # Skip generic/bad insights
            if len(ins['text']) < 20:
                continue
            seen_guests.add(ins['guest'])
            best_examples.append(ins)
            if len(best_examples) >= 5:
                break
        
        consensus_groups.append({
            'theme': topic,
            'count': len(insights),
            'episode_count': len(unique_episodes),
            'insights': best_examples,
            'guests': sorted([g for g in unique_guests if g])[:20]
        })

    # Sort by episode count
    consensus_groups.sort(key=lambda x: x['episode_count'], reverse=True)
    
    return consensus_groups[:top_n]


def extract_actionable_advice(all_insights):
    """Collect all actionable advice across episodes."""
    all_advice = []

    for data in all_insights:
        for advice in data.get('actionable_advice', []):
            all_advice.append({
                'advice': advice.get('advice', ''),
                'how_to': advice.get('how_to', ''),
                'episode_id': data['episode_id'],
                'episode_title': data.get('episode_title', ''),
                'guest': data.get('guest_name', ''),
                'topics': data.get('topics', [])
            })

    return all_advice


def find_contrarian_views(all_insights):
    """Collect all contrarian or surprising claims."""
    contrarian = []

    for data in all_insights:
        for claim in data.get('contrarian_claims', []):
            contrarian.append({
                'claim': claim,
                'episode_id': data['episode_id'],
                'episode_title': data.get('episode_title', ''),
                'guest': data.get('guest_name', '')
            })

    return contrarian


def analyze_guest_expertise(all_insights):
    """Categorize guests by expertise area."""
    expertise_map = defaultdict(list)

    for data in all_insights:
        expertise_map[data.get('expertise_area', 'Unknown')].append({
            'guest': data.get('guest_name', ''),
            'episode_id': data['episode_id'],
            'episode_title': data.get('episode_title', '')
        })

    return dict(expertise_map)


def generate_top_insights(all_insights, top_n=50):
    """Generate a ranked list of top insights across all episodes."""
    all_insights_list = []

    for data in all_insights:
        for insight in data.get('key_insights', []):
            all_insights_list.append({
                'insight': insight['insight'],
                'quote': insight.get('quote', ''),
                'importance': insight.get('importance', 'medium'),
                'episode_id': data['episode_id'],
                'episode_title': data.get('episode_title', ''),
                'guest': data.get('guest_name', ''),
                'topics': data.get('topics', [])
            })

    # Sort by importance
    importance_rank = {'high': 3, 'medium': 2, 'low': 1}
    all_insights_list.sort(
        key=lambda x: importance_rank.get(x['importance'], 0),
        reverse=True
    )

    return all_insights_list[:top_n]


def run_analysis():
    """Run all analyses and save results."""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading insights...")
    all_insights = load_all_insights()
    print(f"Loaded {len(all_insights)} episodes")

    print("\nAnalyzing topics...")
    topic_analysis = analyze_topics(all_insights)
    with open(ANALYSIS_DIR / "topics.json", 'w') as f:
        json.dump(topic_analysis, f, indent=2)
    print(f"  Found {len(topic_analysis['topic_counts'])} unique topics")

    print("\nFinding consensus patterns...")
    consensus = find_consensus_patterns(all_insights, min_episodes=5)
    with open(ANALYSIS_DIR / "consensus.json", 'w') as f:
        json.dump(consensus, f, indent=2)
    print(f"  Found {len(consensus)} consensus themes")
    for c in consensus[:5]:
        print(f"    {c['theme']}: {c['episode_count']} episodes, {c['count']} mentions")

    print("\nCollecting actionable advice...")
    advice = extract_actionable_advice(all_insights)
    with open(ANALYSIS_DIR / "advice.json", 'w') as f:
        json.dump(advice, f, indent=2)
    print(f"  Collected {len(advice)} actionable items")

    print("\nCollecting contrarian views...")
    contrarian = find_contrarian_views(all_insights)
    with open(ANALYSIS_DIR / "contrarian.json", 'w') as f:
        json.dump(contrarian, f, indent=2)
    print(f"  Found {len(contrarian)} contrarian claims")

    print("\nAnalyzing guest expertise...")
    expertise = analyze_guest_expertise(all_insights)
    with open(ANALYSIS_DIR / "expertise.json", 'w') as f:
        json.dump(expertise, f, indent=2)
    print(f"  Categorized {len(expertise)} expertise areas")

    print("\nGenerating top insights...")
    top_insights = generate_top_insights(all_insights, top_n=50)
    with open(ANALYSIS_DIR / "top_insights.json", 'w') as f:
        json.dump(top_insights, f, indent=2)
    print(f"  Selected top {len(top_insights)} insights")

    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    run_analysis()
