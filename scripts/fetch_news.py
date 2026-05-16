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

# News sources configuration - 使用更宽松的查询
SOURCES = {
    "AP": {"name": "美联社", "queries": ["site:apnews.com", "site:ap.org"]},
    "Reuters": {"name": "路透社", "queries": ["site:reuters.com"]},
    "AFP": {"name": "法新社", "queries": ["site:afp.com"]},
    "WSJ": {"name": "华尔街日报", "queries": ["site:wsj.com"]},
    "Bloomberg": {"name": "彭博社", "queries": ["site:bloomberg.com"]},
}

# China-related keywords (case-insensitive)
CHINA_KEYWORDS = [
    "china", "chinese", "beijing", "shanghai", "shenzhen", "guangzhou",
    "taiwan", "hong kong", "hongkong", "ccp", "pla",
    "xinjiang", "tibet", "macau", "macao", "中国", "北京", "上海",
    "台湾", "香港", "深圳", "广州", "新疆", "西藏",
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

def get_rss_urls(source_key: str) -> list:
    """Generate multiple Google News RSS URLs for a source."""
    urls = []
    queries = SOURCES[source_key]["queries"]
    
    for query in queries:
        # 尝试多个时间范围和地区
        configs = [
            {"when": "7d", "hl": "en", "gl": "US", "ceid": "US:en"},
            {"when": "3d", "hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"},
            {"when": "1d", "hl": "en", "gl": "GB", "ceid": "GB:en"},
        ]
        
        for config in configs:
            encoded_query = urllib.parse.quote(f"when:{config['when']} {query}")
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl={config['hl']}&gl={config['gl']}&ceid={config['ceid']}"
            urls.append(url)
    
    return urls

def parse_rss(xml_content: str, source_key: str) -> list:
    """Parse RSS XML and extract news items."""
    items = []
    try:
        root = ET.fromstring(xml_content)
        channel = root.find("channel")
        if channel is None:
            print(f"  ⚠️  No channel found in RSS")
            return items

        item_count = 0
        for item in channel.findall("item"):
            item_count += 1
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
        
        print(f"  📰 Found {item_count} items in RSS feed")
        
    except ET.ParseError as e:
        print(f"  ❌ XML parse error: {e}")
    except Exception as e:
        print(f"  ❌ Error parsing RSS: {e}")

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
    """Fetch news from a single source with multiple fallback URLs."""
    print(f"\n{'='*60}")
    print(f"Fetching: {SOURCES[source_key]['name']} ({source_key})")
    print(f"{'='*60}")
    
    all_items = []
    urls = get_rss_urls(source_key)
    
    for idx, url in enumerate(urls, 1):
        print(f"\n🔍 Attempt {idx}/{len(urls)}")
        print(f"URL: {url[:100]}...")
        
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                xml_content = response.read().decode("utf-8")
                print(f"  ✅ Response received ({len(xml_content)} bytes)")
                
                # 调试：保存 XML 内容
                if not all_items and len(xml_content) < 5000:
                    print(f"  📝 XML Preview (first 500 chars):\n{xml_content[:500]}")
                
                items = parse_rss(xml_content, source_key)
                all_items.extend(items)
                
                if items:
                    print(f"  ✅ Successfully parsed {len(items)} articles")
                    # 如果已经获取到足够的新闻，可以提前停止
                    if len(all_items) >= 20:
                        print(f"  ℹ️  Reached 20+ articles, stopping further attempts")
                        break
                else:
                    print(f"  ⚠️  No articles found in this feed")
                    
        except urllib.error.HTTPError as e:
            print(f"  ❌ HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            print(f"  ❌ URL Error: {e.reason}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # 去重（基于标题）
    seen_titles = set()
    unique_items = []
    for item in all_items:
        if item["title"] not in seen_titles:
            seen_titles.add(item["title"])
            unique_items.append(item)
    
    print(f"\n📊 Total unique articles for {source_key}: {len(unique_items)}")
    return unique_items

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
    print(f"✅ Timeline saved to {timeline_path}")

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
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
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
            margin-bottom: 80px;
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
            padding: 15px 35px;
            border-radius: 50px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        .time-icon {
            font-size: 1.5em;
            margin-right: 10px;
        }
        .time-label {
            font-size: 1.4em;
            font-weight: bold;
            color: #667eea;
        }
        .time-text {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        .stats-text {
            font-size: 0.85em;
            color: #999;
            margin-top: 3px;
        }
        .news-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 20px;
            padding: 0 20px;
        }
        .news-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            position: relative;
            border-left: 4px solid transparent;
        }
        .news-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }
        .news-card.china-related {
            border-left-color: #ef4444;
            background: linear-gradient(to right, #fef2f2 0%, white 20px);
        }
        .news-source {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 14px;
            border-radius: 15px;
            font-size: 0.75em;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .china-flag {
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 1.3em;
            opacity: 0.8;
        }
        .news-title {
            font-size: 1.05em;
            line-height: 1.65;
            color: #1a202c;
            margin-bottom: 12px;
            font-weight: 500;
            padding-right: 30px;
        }
        .news-title a {
            color: #1a202c;
            text-decoration: none;
            transition: color 0.3s;
        }
        .news-title a:hover {
            color: #667eea;
        }
        .news-time {
            font-size: 0.82em;
            color: #9ca3af;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .news-time::before {
            content: '🕐';
            font-size: 0.9em;
        }
        .collapse-section {
            margin-top: 30px;
        }
        .toggle-btn {
            display: block;
            margin: 0 auto;
            background: white;
            color: #667eea;
            border: 2px solid rgba(255,255,255,0.3);
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 0.95em;
            font-weight: 600;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .toggle-btn:hover {
            background: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }
        .collapsed {
            display: none;
        }
        .stats {
            text-align: center;
            color: white;
            margin-top: 60px;
            font-size: 0.9em;
            opacity: 0.9;
            line-height: 1.8;
        }
        .stats p {
            margin: 5px 0;
        }
        .empty-state {
            text-align: center;
            color: white;
            padding: 60px 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            margin: 20px;
        }
        .empty-state h2 {
            margin-bottom: 10px;
            font-size: 1.5em;
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
            .news-card {
                padding: 16px;
            }
            .china-flag {
                font-size: 1.1em;
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
    snapshots = timeline_data.get("snapshots", [])
    if not snapshots:
        html += """
            <div class="empty-state">
                <h2>⏳ 暂无新闻数据</h2>
                <p>等待 GitHub Actions 自动抓取最新国际新闻...</p>
            </div>
"""
    else:
        for idx, snapshot in enumerate(snapshots):
            slot_info = TIME_SLOTS.get(snapshot["time_slot"], {"label": "新闻快照", "icon": "📰"})
            news_list = snapshot.get("news", [])
            total = snapshot.get("total", 0)
            china_count = snapshot.get("china_related_count", 0)
            
            # 分割新闻：前10条默认显示，其余折叠
            visible_news = news_list[:10]
            collapsed_news = news_list[10:]
            
            html += f"""
            <div class="snapshot">
                <div class="snapshot-header">
                    <div class="time-badge">
                        <div>
                            <span class="time-icon">{slot_info["icon"]}</span>
                            <span class="time-label">{slot_info["label"]}</span>
                        </div>
                        <div class="time-text">{snapshot["fetch_time_display"]}</div>
                        <div class="stats-text">共 {total} 篇"""
            
            if china_count > 0:
                html += f" · 🇨🇳 中国相关 {china_count} 篇"
            
            html += """</div>
                    </div>
                </div>
"""
            
            if news_list:
                html += '<div class="news-grid">'
                
                # 显示前10条
                for news in visible_news:
                    china_class = "china-related" if news.get("is_china_related") else ""
                    china_flag = '<span class="china-flag">🇨🇳</span>' if news.get("is_china_related") else ""
                    
                    html += f"""
                    <div class="news-card {china_class}">
                        {china_flag}
                        <span class="news-source">{news["source"]}</span>
                        <div class="news-title">
                            <a href="{news["link"]}" target="_blank" rel="noopener noreferrer">{news["title"]}</a>
                        </div>
                        <div class="news-time">{news.get("pub_date", "")[:30]}</div>
                    </div>
"""
                
                html += '</div>'
                
                # 如果有更多新闻，添加折叠部分
                if collapsed_news:
                    collapse_id = f"collapse-{idx}"
                    html += f"""
                <div class="collapse-section">
                    <button class="toggle-btn" onclick="toggleCollapse('{collapse_id}', this)">
                        ▼ 查看更多 ({len(collapsed_news)} 篇)
                    </button>
                    <div id="{collapse_id}" class="news-grid collapsed" style="margin-top: 20px;">
"""
                    
                    for news in collapsed_news:
                        china_class = "china-related" if news.get("is_china_related") else ""
                        china_flag = '<span class="china-flag">🇨🇳</span>' if news.get("is_china_related") else ""
                        
                        html += f"""
                        <div class="news-card {china_class}">
                            {china_flag}
                            <span class="news-source">{news["source"]}</span>
                            <div class="news-title">
                                <a href="{news["link"]}" target="_blank" rel="noopener noreferrer">{news["title"]}</a>
                            </div>
                            <div class="news-time">{news.get("pub_date", "")[:30]}</div>
                        </div>
"""
                    
                    html += """
                    </div>
                </div>
"""
            else:
                html += '<div class="empty-state"><p>本时段暂无新闻</p></div>'
            
            html += '</div>'

    # Add footer stats
    total_snapshots = len(snapshots)
    total_articles = sum(s.get("total", 0) for s in snapshots)
    total_china = sum(s.get("china_related_count", 0) for s in snapshots)
    
    html += f"""
        </div>
        <div class="stats">
            <p><strong>📊 统计信息</strong></p>
            <p>时间快照: {total_snapshots} 个 · 累计文章: {total_articles} 篇 · 中国相关: {total_china} 篇</p>
            <p>数据来源: AP · Reuters · AFP · WSJ · Bloomberg</p>
            <p>最后更新: {timeline_data.get("last_update", "N/A")}</p>
        </div>
    </div>
    
    <script>
        function toggleCollapse(id, btn) {{
            const element = document.getElementById(id);
            const isCollapsed = element.classList.contains('collapsed');
            
            if (isCollapsed) {{
                element.classList.remove('collapsed');
                btn.innerHTML = '▲ 收起';
            }} else {{
                element.classList.add('collapsed');
                const count = element.querySelectorAll('.news-card').length;
                btn.innerHTML = `▼ 查看更多 (${{count}} 篇)`;
            }}
        }}
    </script>
</body>
</html>
"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ HTML page generated: index.html")
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
    
    print(f"\n{'='*60}")
    print(f"📊 总计抓取: {len(all_news)} 篇文章")
    print(f"{'='*60}")
    
    # Sort: China-related first, then by timestamp descending
    all_news.sort(key=lambda x: (-x["is_china_related"], -x["pub_timestamp"]))
    
    # Limit to top 50 articles per snapshot
    all_news = all_news[:50]
    
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
    print(f"   时间线快照: {len(timeline['snapshots'])} 个\n")

if __name__ == "__main__":
    main()
