#!/usr/bin/env python3
"""
Fetch news from AP, Reuters, AFP, WSJ, Bloomberg via Google News RSS.
China-related news are prioritized.
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone
from html import unescape

# News sources configuration
SOURCES = {
    "AP": {"name": "美联社", "query": "source:ap.org"},
    "Reuters": {"name": "路透社", "query": "source:reuters.com"},
    "AFP": {"name": "法新社", "query": "source:afp.com"},
    "WSJ": {"name": "华尔街日报", "query": "source:wsj.com"},
    "Bloomberg": {"name": "彭博社", "query": "source:bloomberg.com"},
}

# China-related keywords (case-insensitive)
CHINA_KEYWORDS = [
    "china", "chinese", "beijing", "shanghai", "shenzhen", "guangzhou",
    "taiwan", "hong kong", "hongkong", "xi jinping", "ccp", "pla",
    "xinjiang", "tibet", "macau", "macao", "中国", "北京", "上海",
    "台湾", "香港", "习近平", "深圳", "广州", "新疆", "西藏",
]

def get_rss_url(source_key: str) -> str:
    """Generate Google News RSS URL for a source."""
    source_query = SOURCES[source_key]["query"]
    query = f"when:24h+{source_query}"
    return f"https://news.google.com/rss/search?q={query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"

def parse_rss(xml_content: str, source_key: str) -> list:
    """Parse RSS XML and extract news items."""
    items = []
    try:
        root = ET.fromstring(xml_content)
        channel = root.find("channel")
        if channel is None:
            return items

        for item in channel.findall("item"):
            title_elem = item.find("title")
            link_elem = item.find("link")
            pub_date_elem = item.find("pubDate")
            source_elem = item.find("source")

            title = unescape(title_elem.text) if title_elem is not None and title_elem.text else "无标题"
            link = link_elem.text if link_elem is not None and link_elem.text else ""
            pub_date = pub_date_elem.text if pub_date_elem is not None and pub_date_elem.text else ""
            original_source = source_elem.text if source_elem is not None and source_elem.text else ""

            # Clean title (remove source suffix like " - Reuters")
            title = re.sub(r'\s*-\s*[^\-]+$', '', title).strip()

            # Parse publication date
            pub_timestamp = parse_pub_date(pub_date)

            # Check if China-related
            is_china_related = check_china_related(title)

            items.append({
                "title": title,
                "link": link,
                "source": SOURCES[source_key]["name"],
                "source_key": source_key,
                "original_source": original_source,
                "pub_date": pub_date,
                "pub_timestamp": pub_timestamp,
                "is_china_related": is_china_related,
            })
    except ET.ParseError as e:
        print(f"XML parse error for {source_key}: {e}")
    except Exception as e:
        print(f"Error parsing RSS for {source_key}: {e}")

    return items

def parse_pub_date(pub_date: str) -> int:
    """Parse RFC 2822 date string to Unix timestamp."""
    try:
        # Try common RSS date formats
        for fmt in [
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
        ]:
            try:
                dt = datetime.strptime(pub_date, fmt)
                return int(dt.timestamp())
            except ValueError:
                continue
        # Fallback: try parsing with timezone
        if "+" in pub_date or "-" in pub_date[-6:]:
            pub_date_clean = pub_date[:-6].strip()
            try:
                dt = datetime.strptime(pub_date_clean, "%a, %d %b %Y %H:%M:%S")
                return int(dt.timestamp())
            except ValueError:
                pass
    except Exception:
        pass
    return 0

def check_china_related(title: str) -> bool:
    """Check if title contains China-related keywords."""
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in CHINA_KEYWORDS)

def fetch_news(source_key: str) -> list:
    """Fetch news from a single source."""
    url = get_rss_url(source_key)
    print(f"Fetching: {SOURCES[source_key]['name']} ({source_key})")

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            xml_content = response.read().decode("utf-8")
            return parse_rss(xml_content, source_key)
    except Exception as e:
        print(f"Error fetching {source_key}: {e}")
        return []

def main():
    """Main function to fetch all news and save to JSON."""
    all_news = []
    fetch_time = datetime.now(timezone.utc).isoformat()

    for source_key in SOURCES:
        news_items = fetch_news(source_key)
        all_news.extend(news_items)
        print(f"  Found {len(news_items)} articles")

    # Sort: China-related first, then by timestamp descending
    all_news.sort(key=lambda x: (-x["is_china_related"], -x["pub_timestamp"]))

    # Limit to top 50 articles
    all_news = all_news[:50]

    output = {
        "fetch_time": fetch_time,
        "total": len(all_news),
        "china_related_count": sum(1 for n in all_news if n["is_china_related"]),
        "news": all_news,
    }

    # Write to JSON file
    output_path = "news.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(all_news)} articles saved to {output_path}")
    print(f"China-related: {output['china_related_count']} articles")

if __name__ == "__main__":
    main()
