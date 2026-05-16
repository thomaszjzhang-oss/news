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
