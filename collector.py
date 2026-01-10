"""Module: collector.py | Version: 0.2.0 | Engineer: Guido Style"""
import feedparser, json, os, urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser

# [전략 키워드] 엔비디아 및 기술 세부 사양까지 포착하도록 키워드 최적화
KEYWORDS = 'Nvidia OR "G-Sync" OR "Pulsar" OR "Meta Nuclear" OR "AI Power" OR "HBM3E" OR "K-Defense"'
Q = urllib.parse.quote(KEYWORDS)
FEEDS = {"GNews": f"https://news.google.com/rss/search?q={Q}&hl=en-US&gl=US&ceid=US:en"}

def collect():
    print("🌐 [Ver 0.2.0] 글로벌 테크/안보 밸류체인 데이터 수집...")
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
                        "summary": entry.get('summary', '')[:600]
                    })
            except: continue
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"articles": all_articles}, f, ensure_ascii=False, indent=4)
    print(f"✅ 수집 완료: 총 {len(all_articles)}건 정제.")

if __name__ == "__main__": collect()
