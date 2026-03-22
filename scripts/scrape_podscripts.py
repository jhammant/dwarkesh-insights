#!/usr/bin/env python3
"""
Scraper for The Dwarkesh Podcast transcripts from podscripts.co
Gets all 805 episodes with full transcripts.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path
from typing import List, Dict
import argparse

BASE_URL = "https://podscripts.co"
PODCAST_URL = f"{BASE_URL}/podcasts/dwarkesh-podcast/"

def get_episode_links(page: int = 1) -> tuple[List[str], bool]:
    """
    Get episode links from a pagination page.
    Returns (list of episode slugs, has_next_page)
    """
    url = PODCAST_URL if page == 1 else f"{PODCAST_URL}?page={page}"
    print(f"Fetching episode list from page {page}: {url}")

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all episode links
    episode_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('/podcasts/dwarkesh-podcast/') and href != '/podcasts/dwarkesh-podcast/':
            slug = href.split('/')[-1]
            if slug and slug not in episode_links:
                episode_links.append(slug)

    # Check if there's a next page
    has_next = False
    for link in soup.find_all('a', href=True):
        if f'page={page + 1}' in link['href'] or 'next' in link.text.lower():
            has_next = True
            break

    # Alternative: check if we got any episodes (if not, probably no more pages)
    if not episode_links:
        has_next = False

    print(f"Found {len(episode_links)} episodes on page {page}")
    return episode_links, has_next


def scrape_transcript(slug: str) -> Dict:
    """
    Scrape a single episode transcript from podscripts.co
    """
    url = f"{PODCAST_URL}{slug}"
    print(f"Scraping: {slug}")

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract title
    title_elem = soup.find('h1')
    title = title_elem.text.strip() if title_elem else slug

    # Try to extract guest name from title
    # Common pattern: "Guest Name: Episode Title" or "Guest Name - Episode Title"
    guest = "Unknown"
    if ':' in title:
        guest = title.split(':')[0].strip()
    elif ' - ' in title:
        guest = title.split(' - ')[0].strip()

    # Extract transcript text
    # The transcript is usually in a specific container or multiple paragraphs
    transcript_parts = []

    # Try to find transcript container (common class names)
    transcript_container = soup.find('div', class_=re.compile(r'transcript|content|episode-content', re.I))

    if transcript_container:
        # Get all text from paragraphs
        for p in transcript_container.find_all(['p', 'div'], recursive=True):
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Skip very short lines
                transcript_parts.append(text)
    else:
        # Fallback: get all paragraphs from the main content
        main_content = soup.find('main') or soup.find('article') or soup.body
        if main_content:
            for p in main_content.find_all('p'):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    transcript_parts.append(text)

    transcript_text = '\n\n'.join(transcript_parts)

    # If we didn't get much text, try a more aggressive approach
    if len(transcript_text) < 500:
        all_text = soup.get_text(separator='\n', strip=True)
        transcript_text = all_text

    return {
        'slug': slug,
        'title': title,
        'guest': guest,
        'transcript_text': transcript_text,
        'url': url,
        'word_count': len(transcript_text.split())
    }


def save_transcript(episode_data: Dict, output_dir: Path):
    """Save individual transcript as JSON"""
    output_file = output_dir / f"{episode_data['slug']}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(episode_data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Scrape Dwarkesh transcripts from podscripts.co')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of episodes to scrape')
    parser.add_argument('--start-page', type=int, default=1, help='Starting page number')
    parser.add_argument('--delay', type=float, default=1.5, help='Delay between requests (seconds)')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path('data/transcripts')
    output_dir.mkdir(parents=True, exist_ok=True)

    all_episodes = []
    page = args.start_page
    total_scraped = 0

    print(f"Starting scrape from page {page}...")
    print(f"Delay between requests: {args.delay}s")
    if args.limit:
        print(f"Limit: {args.limit} episodes")

    # First, collect all episode slugs
    all_slugs = []
    while True:
        try:
            slugs, has_next = get_episode_links(page)
            all_slugs.extend(slugs)
            print(f"Total episodes found so far: {len(all_slugs)}")

            if not has_next or (args.limit and len(all_slugs) >= args.limit):
                break

            page += 1
            time.sleep(args.delay)

        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

    print(f"\nFound {len(all_slugs)} total episodes")

    if args.limit:
        all_slugs = all_slugs[:args.limit]
        print(f"Limited to {len(all_slugs)} episodes")

    # Now scrape each episode
    for i, slug in enumerate(all_slugs, 1):
        try:
            episode_data = scrape_transcript(slug)
            save_transcript(episode_data, output_dir)
            all_episodes.append(episode_data)

            print(f"[{i}/{len(all_slugs)}] Scraped: {episode_data['title']} ({episode_data['word_count']} words)")

            total_scraped += 1

            # Respectful delay
            if i < len(all_slugs):
                time.sleep(args.delay)

        except Exception as e:
            if "429" in str(e):
                print(f"Rate limited on {slug}, waiting 30s...")
                time.sleep(30)
                # Retry once
                try:
                    episode_data = scrape_transcript(slug)
                    save_transcript(episode_data, output_dir)
                    all_episodes.append(episode_data)
                    print(f"[{i}/{len(all_slugs)}] Scraped (retry): {episode_data['title']} ({episode_data['word_count']} words)")
                    total_scraped += 1
                except Exception as e2:
                    print(f"Retry failed for {slug}: {e2}")
                    time.sleep(60)  # Extra long wait after double failure
            else:
                print(f"Error scraping {slug}: {e}")
            continue

    # Save summary
    summary = {
        'total_episodes': len(all_episodes),
        'episodes': [
            {
                'slug': ep['slug'],
                'title': ep['title'],
                'guest': ep['guest'],
                'word_count': ep['word_count'],
                'url': ep['url']
            }
            for ep in all_episodes
        ]
    }

    summary_file = output_dir / '_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Scraping complete!")
    print(f"Total episodes scraped: {total_scraped}")
    print(f"Saved to: {output_dir}")
    print(f"Summary saved to: {summary_file}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
