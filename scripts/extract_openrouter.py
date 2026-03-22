#!/usr/bin/env python3
"""
Universal podcast insight extractor using OpenRouter free models.
No rate limits, runs in parallel across podcasts.

Usage:
  python extract_openrouter.py --transcripts-dir data/transcripts --insights-dir data/insights
  python extract_openrouter.py --transcripts-dir data/transcripts --insights-dir data/insights --model meta-llama/llama-3.3-70b-instruct:free
"""

import json
import os
import sys
import time
import re
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# OpenRouter config
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
API_KEY_FILE = Path.home() / ".config" / "openrouter" / "config.json"

def load_openrouter_key():
    if API_KEY_FILE.exists():
        data = json.loads(API_KEY_FILE.read_text())
        return data.get("apiKey", "")
    return os.environ.get("OPENROUTER_API_KEY", "")

EXTRACTION_PROMPT = """Analyze this podcast transcript and extract structured insights. Return ONLY valid JSON, no markdown wrapping.

{{
  "guest_name": "Full name of the guest(s) (NOT the host)",
  "expertise_area": "Primary area of expertise",
  "episode_title": "Episode title as given",
  "key_insights": [
    {{"insight": "One sentence summary of key insight", "quote": "Best supporting quote (1-3 sentences, verbatim)", "importance": "high/medium/low"}}
  ],
  "topics": ["topic1", "topic2", "topic3"],
  "actionable_advice": [
    {{"advice": "Specific actionable recommendation", "how_to": "How to implement it"}}
  ],
  "contrarian_claims": [
    {{"claim": "Surprising or contrarian viewpoint expressed", "context": "Why this is contrarian or surprising"}}
  ]
}}

Rules:
- Extract 3-8 key insights, 2-5 advice items, and any contrarian claims
- Keep quotes SHORT (1-3 sentences max, verbatim from transcript)
- Topics should be specific (not generic like "science" — use "CRISPR gene editing" instead)
- If multiple guests, list all names comma-separated
- Return ONLY the JSON object, no explanation

TRANSCRIPT:
{transcript}"""


def call_openrouter(prompt, model=DEFAULT_MODEL, max_retries=3):
    """Call OpenRouter API with retries."""
    api_key = load_openrouter_key()
    headers = {
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/jhammant",
        "X-Title": "Podcast Insights Extractor"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4096
    }).encode("utf-8")

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                OPENROUTER_API_URL,
                data=payload,
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data["choices"][0]["message"]["content"].strip()

            # Clean markdown wrapping
            if content.startswith("```"):
                content = re.sub(r"^```\w*\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
                content = content.strip()

            return json.loads(content)

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited (429), waiting {wait}s... {body[:100]}")
                time.sleep(wait)
            elif e.code == 502 or e.code == 503:
                wait = 10 * (attempt + 1)
                print(f"  Server error ({e.code}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP {e.code}: {body[:200]}")
                return None
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return None
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return None

    return None


def extract_from_transcript(transcript_path, model=DEFAULT_MODEL, max_chars=60000):
    """Extract insights from a single transcript file."""
    with open(transcript_path) as f:
        data = json.load(f)

    # Handle different transcript formats
    if isinstance(data, dict):
        transcript_text = data.get("transcript", data.get("transcript_text", data.get("text", data.get("content", ""))))
        metadata = {k: v for k, v in data.items() if k not in ("transcript", "text", "content")}
    elif isinstance(data, str):
        transcript_text = data
        metadata = {}
    else:
        transcript_text = json.dumps(data)
        metadata = {}

    if not transcript_text or len(transcript_text) < 200:
        return None, "transcript too short"

    # Truncate for context window
    if len(transcript_text) > max_chars:
        transcript_text = transcript_text[:max_chars]

    prompt = EXTRACTION_PROMPT.format(transcript=transcript_text)
    result = call_openrouter(prompt, model=model)

    if result:
        # Merge metadata
        slug = transcript_path.stem
        result["episode_id"] = metadata.get("episode_id", metadata.get("slug", slug))
        result["episode_url"] = metadata.get("episode_url", metadata.get("url", ""))
        result["episode_title"] = result.get("episode_title", metadata.get("title", metadata.get("episode_title", "")))
        result["_extracted_by"] = model
        result["_extracted_at"] = datetime.utcnow().isoformat()

        # Use metadata guest name if Gemini's looks wrong
        meta_guest = metadata.get("guest", metadata.get("guest_name", ""))
        if meta_guest and (not result.get("guest_name") or result["guest_name"].lower() in ["unknown", "n/a", "not applicable", "the host"]):
            result["guest_name"] = meta_guest
            result["_name_source"] = "metadata"

    return result, None


def main():
    parser = argparse.ArgumentParser(description="Extract podcast insights via OpenRouter")
    parser.add_argument("--transcripts-dir", type=Path, required=True, help="Directory with transcript JSON files")
    parser.add_argument("--insights-dir", type=Path, required=True, help="Output directory for insight files")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenRouter model (default: {DEFAULT_MODEL})")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--batch", type=int, default=0, help="Max episodes to process (0=all)")
    parser.add_argument("--max-chars", type=int, default=60000, help="Max transcript chars to send")
    parser.add_argument("--resume", action="store_true", help="Skip already-extracted episodes")
    args = parser.parse_args()

    args.insights_dir.mkdir(parents=True, exist_ok=True)

    # Find transcript files
    transcript_files = sorted(args.transcripts_dir.glob("*.json"))
    total = len(transcript_files)

    # Skip already done
    if args.resume:
        existing = {f.stem for f in args.insights_dir.glob("*.json")}
        transcript_files = [f for f in transcript_files if f.stem not in existing]

    remaining = len(transcript_files)
    if args.batch > 0:
        transcript_files = transcript_files[:args.batch]

    print(f"Podcast Insight Extractor (OpenRouter)")
    print(f"  Model: {args.model}")
    print(f"  Total transcripts: {total}")
    print(f"  Already extracted: {total - remaining}")
    print(f"  To process: {len(transcript_files)}")
    print(f"  Delay: {args.delay}s")
    print()

    success = 0
    failed = 0

    for i, filepath in enumerate(transcript_files):
        slug = filepath.stem
        print(f"[{i+1}/{len(transcript_files)}] {slug}...", end=" ", flush=True)

        result, error = extract_from_transcript(filepath, model=args.model, max_chars=args.max_chars)

        if result:
            out_file = args.insights_dir / f"{slug}.json"
            with open(out_file, "w") as f:
                json.dump(result, f, indent=2)

            guest = result.get("guest_name", "?")
            n_insights = len(result.get("key_insights", []))
            print(f"✓ {guest} ({n_insights} insights)")
            success += 1
        else:
            print(f"✗ {error or 'extraction failed'}")
            failed += 1

        if args.delay > 0:
            time.sleep(args.delay)

        # Progress update every 50
        if (i + 1) % 50 == 0:
            print(f"\n--- Progress: {success} extracted, {failed} failed, {len(transcript_files) - i - 1} remaining ---\n")

    print(f"\n{'='*60}")
    print(f"Done! {success} extracted, {failed} failed")
    print(f"Output: {args.insights_dir}")


if __name__ == "__main__":
    main()
