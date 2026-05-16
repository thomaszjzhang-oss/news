#!/usr/bin/env python3
"""
Fetch news from AP, Reuters, AFP, WSJ, Bloomberg via Google News RSS.
China-related news are prioritized.
Timeline version: Stores snapshots at different times of day.
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone, timedelta
from html import unescape
import os

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

# Time slot configuration (Beijing Time)
TIME_SLOTS = {
    "morning": {"label": "早间简报", "time": "08:00", "icon": "🌅"},
    "afternoon": {"label": "午间快讯", "time": "14:00", "icon": "☀️"},
    "evening": {"label": "晚间综述", "time": "20:00", "icon": "🌙"},
}

def get_time_slot(hour: int) -> str:
    """Determine time slot based on hour (Beijing Time)."""
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    else:
        return "evening"

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

def load_timeline() -> dict:
    """Load existing timeline data."""
    timeline_path = "timeline.json"
    if os.path.exists(timeline_path):
        try:
            with open(timeline_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading timeline: {e}")
    return {"snapshots": []}

def save_timeline(timeline_data: dict):
    """Save timeline data."""
    timeline_path = "timeline.json"
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, ensure_ascii=False, indent=2)
    print(f"Timeline saved to {timeline_path}")

def generate_html(timeline_data: dict):
    """Generate HTML page for timeline display."""
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>国际新闻时间线</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .timeline {
            position: relative;
            padding: 20px 0;
        }
        .timeline::before {
            content: '';
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            width: 4px;
            height: 100%;
            background: rgba(255,255,255,0.3);
            top: 0;
        }
        .snapshot {
            margin-bottom: 60px;
            position: relative;
        }
        .snapshot-header {
            text-align: center;
            margin-bottom: 30px;
            position: relative;
            z-index: 10;
        }
        .time-badge {
            display: inline-block;
            background: white;
            padding: 15px 30px;
            border-radius: 50px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .time-icon {
            font-size: 1.5em;
            margin-right: 10px;
        }
        .time-label {
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
        }
        .time-text {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        .news-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            padding: 0 20px;
        }
        .news-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            position: relative;
        }
        .news-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .news-card.china-related {
            border-left: 4px solid #f56565;
        }
        .news-source {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75em;
            margin-bottom: 10px;
        }
        .china-badge {
            display: inline-block;
            background: #f56565;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.7em;
            margin-left: 8px;
        }
        .news-title {
            font-size: 1.05em;
            line-height: 1.6;
            color: #2d3748;
            margin-bottom: 12px;
        }
        .news-title a {
            color: #2d3748;
            text-decoration: none;
            transition: color 0.3s;
        }
        .news-title a:hover {
            color: #667eea;
        }
        .news-time {
            font-size: 0.85em;
            color: #a0aec0;
        }
        .stats {
            text-align: center;
            color: white;
            margin-top: 40px;
            font-size: 0.9em;
            opacity: 0.8;
        }
        @media (max-width: 768px) {
            .news-grid {
                grid-template-columns: 1fr;
            }
            h1 {
                font-size: 1.8em;
            }
            .timeline::before {
                left: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📰 国际新闻时间线</h1>
        <div class="timeline">
"""

    # Add snapshots
    for snapshot in timeline_data.get("snapshots", []):
        slot_info = TIME_SLOTS.get(snapshot["time_slot"], {"label": "新闻快照", "icon": "📰"})
        
        html += f"""
            <div class="snapshot">
                <div class="snapshot-header">
                    <div class="time-badge">
                        <div>
                            <span class="time-icon">{slot_info["icon"]}</span>
                            <span class="time-label">{slot_info["label"]}</span>
                        </div>
                        <div class="time-text">{snapshot["fetch_time_display"]}</div>
                    </div>
                </div>
                <div class="news-grid">
"""
        
        for news in snapshot.get("news", []):
            china_class = "china-related" if news.get("is_china_related") else ""
            china_badge = '<span class="china-badge">中国相关</span>' if news.get("is_china_related") else ""
            
            html += f"""
                    <div class="news-card {china_class}">
                        <div>
                            <span class="news-source">{news["source"]}</span>
                            {china_badge}
                        </div>
                        <div class="news-title">
                            <a href="{news["link"]}" target="_blank">{news["title"]}</a>
                        </div>
                        <div class="news-time">{news.get("pub_date", "")}</div>
                    </div>
"""
        
        html += """
                </div>
            </div>
"""

    # Add footer stats
    total_snapshots = len(timeline_data.get("snapshots", []))
    html += f"""
        </div>
        <div class="stats">
            <p>共 {total_snapshots} 个时间快照 | 数据来源：AP, Reuters, AFP, WSJ, Bloomberg</p>
            <p>最后更新：{timeline_data.get("last_update", "")}</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML page generated: index.html")

def main():
    """Main function to fetch news and update timeline."""
    # Get current time in Beijing timezone (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(beijing_tz)
    now_utc = datetime.now(timezone.utc)
    
    # Determine time slot
    time_slot = get_time_slot(now_beijing.hour)
    slot_info = TIME_SLOTS[time_slot]
    
    print(f"\n{'='*60}")
    print(f"{slot_info['icon']} {slot_info['label']} - {now_beijing.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"{'='*60}\n")
    
    # Fetch news
    all_news = []
    for source_key in SOURCES:
        news_items = fetch_news(source_key)
        all_news.extend(news_items)
        print(f"  Found {len(news_items)} articles")
    
    # Sort: China-related first, then by timestamp descending
    all_news.sort(key=lambda x: (-x["is_china_related"], -x["pub_timestamp"]))
    
    # Limit to top 30 articles per snapshot
    all_news = all_news[:30]
    
    china_count = sum(1 for n in all_news if n["is_china_related"])
    
    # Create snapshot
    snapshot = {
        "fetch_time": now_utc.isoformat(),
        "fetch_time_display": now_beijing.strftime("%Y年%m月%d日 %H:%M"),
        "time_slot": time_slot,
        "time_slot_label": slot_info["label"],
        "total": len(all_news),
        "china_related_count": china_count,
        "news": all_news,
    }
    
    # Load existing timeline
    timeline = load_timeline()
    
    # Add new snapshot at the beginning
    timeline["snapshots"].insert(0, snapshot)
    
    # Keep only last 14 days (3 snapshots per day = 42 snapshots)
    timeline["snapshots"] = timeline["snapshots"][:42]
    
    # Update metadata
    timeline["last_update"] = now_beijing.strftime("%Y年%m月%d日 %H:%M")
    timeline["total_snapshots"] = len(timeline["snapshots"])
    
    # Save timeline
    save_timeline(timeline)
    
    # Generate HTML
    generate_html(timeline)
    
    print(f"\n✅ 完成！")
    print(f"   本次抓取: {len(all_news)} 篇文章 (中国相关: {china_count} 篇)")
    print(f"   时间线快照: {len(timeline['snapshots'])} 个")

if __name__ == "__main__":
    main()
