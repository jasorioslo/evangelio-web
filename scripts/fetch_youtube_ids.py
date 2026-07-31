#!/usr/bin/env python3
"""
Fetch evangelio video IDs from the "Evangelio Para Hoy" YouTube channel RSS feed
and update src/data/youtube-videos.json.

Designed to run in the GitHub Action daily-rebuild.yml before the empty commit.
Uses only Python stdlib (no pip install needed).

Usage:
    python3 scripts/fetch_youtube_ids.py
"""

import json
import re
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree

CHANNEL_ID = "UC9I4DOs2sjfWqFmz9zF_jPQ"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
JSON_PATH = Path(__file__).resolve().parent.parent / "src" / "data" / "youtube-videos.json"

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

DATE_RE = re.compile(
    r"(\d{1,2})\s+de\s+("
    + "|".join(MONTHS.keys())
    + r")",
    re.IGNORECASE,
)


def parse_content_date(title, published_str):
    """
    Extract YYYY-MM-DD from a title like
    "Evangelio de hoy Viernes 31 de Julio ..." using the published date for the year.

    The video is published at ~8pm Mexico time the evening BEFORE the content date,
    so in UTC the published date already equals the content date for typical publish times.
    We still use the title's day/month (authoritative) and just take the year from the
    published timestamp, with year-boundary correction when necessary.
    """
    match = DATE_RE.search(title)
    if not match:
        return None

    day = int(match.group(1))
    month = MONTHS[match.group(2).lower()]

    pub_date = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
    year = pub_date.year

    if month == 1 and pub_date.month == 12:
        year = pub_date.year + 1
    elif month == 12 and pub_date.month == 1:
        year = pub_date.year - 1

    return f"{year:04d}-{month:02d}-{day:02d}"


def fetch_rss():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return ElementTree.fromstring(data)


def main():
    if JSON_PATH.exists():
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            videos = json.load(f)
    else:
        videos = {}

    old_json = json.dumps(videos, sort_keys=True, indent=2)

    print(f"Fetching RSS feed from {RSS_URL}")
    root = fetch_rss()

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    added = 0
    skipped = 0

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        video_id_el = entry.find("yt:videoId", ns)
        published_el = entry.find("atom:published", ns)
        if title_el is None or video_id_el is None or published_el is None:
            skipped += 1
            continue

        title = title_el.text or ""
        video_id = video_id_el.text or ""
        published = published_el.text or ""

        if "evangelio de hoy" not in title.lower():
            skipped += 1
            continue

        content_date = parse_content_date(title, published)
        if not content_date:
            print(f"WARN: Could not parse date from: {title}")
            skipped += 1
            continue

        if content_date not in videos:
            videos[content_date] = video_id
            short_title = title[:60] + ("..." if len(title) > 60 else "")
            print(f"  + {content_date} -> {video_id} ({short_title})")
            added += 1
        else:
            existing = videos[content_date]
            if existing != video_id:
                videos[content_date] = video_id
                print(f"  ~ {content_date}: {existing} -> {video_id}")
                added += 1
            else:
                print(f"  = {content_date} already {video_id}")

    sorted_videos = dict(sorted(videos.items()))
    new_json = json.dumps(sorted_videos, sort_keys=True, indent=2)

    if old_json != new_json:
        JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted_videos, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"\nUpdated: {added} added/changed, {skipped} skipped, {len(sorted_videos)} total")
        return 0
    else:
        print(f"\nNo changes: {added} added, {skipped} skipped, {len(sorted_videos)} total")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())