"""Module: collector.py | Version: 0.2.2 | Engineer: Guido Style"""
import feedparser, json, os, urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser

# [전략 쿼리] 특징주, 정부 정책, CES 핵심 테마를 모두 포함
SEARCH_QUERIES = [
    'Nvidia Pulsar Blackwell impact',
    'Meta Nuclear Energy AI Data Center',
    'Trump Robot Industry Policy',
    'US Market Featured Stocks breaking',
    'South Korea Semiconductor Supply Chain'
]

def collect():
    print("🌍 [Ver 1.3.0] 글로벌 금융-테크 웹 심층 탐색 시작...")
    all_articles = []
    limit = datetime.now(timezone.utc) - timedelta(hours=48)

    for query in SEARCH_QUERIES:
        q_encoded = urllib.parse.quote(query)
        search_url = f"https://news.google.com/rss/search?q={q_encoded}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(search_url)
        
        for entry in feed.entries[:12]: 
            try:
                pub_date = parser.parse(entry.get('published', ''))
                if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date >= limit:
                    all_articles.append({
                        "source": "GlobalIntelligence", "title": entry.get('title', ''),
                        "link": entry.get('link', ''), "published_at": entry.get('published', ''),
                        "summary": entry.get('summary', '')[:600]
                    })
            except: continue
    
    unique_articles = {a['link']: a for a in all_articles}.values()
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"articles": list(unique_articles)}, f, ensure_ascii=False, indent=4)
    print(f"✅ 탐색 완료: 총 {len(unique_articles)}건 확보.")

if __name__ == "__main__": collect()
