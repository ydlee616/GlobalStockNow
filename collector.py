"""Module: collector.py | Version: 0.1.7 | Engineer: Guido Style"""
import feedparser, json, os, urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser

# 시장 주도 섹터 키워드
Q = urllib.parse.quote('Nvidia OR "Semi-conductor" OR "Nuclear Power" OR "Meta" OR "North Korea" OR "Interest Rate"')
FEEDS = {"GNews": f"https://news.google.com/rss/search?q={Q}&hl=en-US&gl=US&ceid=US:en"}

def collect():
    print("🌐 [Ver 0.1.7] 48시간 이내 글로벌 속보 선별 수집...")
    all_articles = []
    limit = datetime.now(timezone.utc) - timedelta(hours=48)

    for name, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            try:
                pub_date = parser.parse(entry.get('published', ''))
                if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date >= limit: # 48시간 필터 적용
                    all_articles.append({
                        "source": name, "title": entry.get('title', ''),
                        "link": entry.get('link', ''), "published_at": entry.get('published', ''),
                        "summary": entry.get('summary', '')[:500]
                    })
            except: continue
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"articles": all_articles}, f, ensure_ascii=False, indent=4)
    print(f"✅ 수집 완료: 총 {len(all_articles)}건 저장.")

if __name__ == "__main__": collect()
