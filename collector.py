"""Module: collector.py | Version: 0.1.9 | Updated: 2026-01-11"""
import feedparser, json, os, urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser

# [핵심] 수집 키워드: 반도체, 원전, 메타, 북한, 금리, 인플레이션
Q = urllib.parse.quote('Nvidia OR "Semi-conductor" OR "Nuclear Power" OR "Meta" OR "North Korea" OR "Interest Rate"')
FEEDS = {"GoogleNews": f"https://news.google.com/rss/search?q={Q}&hl=en-US&gl=US&ceid=US:en"}

def collect():
    print("🌐 [Ver 0.1.9] 글로벌 밸류체인 48h 속보 수집 개시...")
    all_articles = []
    limit = datetime.now(timezone.utc) - timedelta(hours=48)

    for name, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            try:
                pub_date = parser.parse(entry.get('published', ''))
                if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date >= limit: # 보스 지시: 48시간 엄수
                    all_articles.append({
                        "source": name, "title": entry.get('title', ''),
                        "link": entry.get('link', ''), "published_at": entry.get('published', ''),
                        "summary": entry.get('summary', '')[:500]
                    })
            except: continue
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"articles": all_articles}, f, ensure_ascii=False, indent=4)
    print(f"✅ 필터링 완료: 총 {len(all_articles)}건 저장.")

if __name__ == "__main__": collect()
