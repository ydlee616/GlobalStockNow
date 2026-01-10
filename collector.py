"""Module: collector.py | Version: 0.1.9 | Concept: Guido Style"""
import feedparser, json, os, urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser

# [전략 키워드] 보스의 기획력을 담은 핵심 검색어
Q = urllib.parse.quote('Nvidia OR "Semi-conductor" OR "Nuclear Power" OR "Meta" OR "North Korea" OR "Interest Rate"')
FEEDS = {"GNews": f"https://news.google.com/rss/search?q={Q}&hl=en-US&gl=US&ceid=US:en"}

def collect():
    print("🌐 [Ver 0.1.9] 글로벌 밸류체인 48h 데이터 수집...")
    all_articles = []
    limit = datetime.now(timezone.utc) - timedelta(hours=48)

    for name, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:25]:
            try:
                pub_date = parser.parse(entry.get('published', ''))
                if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date >= limit:
                    all_articles.append({
                        "source": name, "title": entry.get('title', ''),
                        "link": entry.get('link', ''), "published_at": entry.get('published', ''),
                        "summary": entry.get('summary', '')[:500]
                    })
            except: continue
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"articles": all_articles}, f, ensure_ascii=False, indent=4)
    print(f"✅ 수집 완료: 총 {len(all_articles)}건 정제됨.")

if __name__ == "__main__": collect()
