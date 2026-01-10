"""Module: collector.py | Version: 0.1.5 | Updated: 2026-01-11"""
import feedparser, json, os, urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser # 날짜 파싱 라이브러리 활용

Q_DEF = urllib.parse.quote('KF-21 OR "Nuclear Submarine" OR "K-Defense" OR "North Korea"')
Q_TEC = urllib.parse.quote('Apple OR Meta OR "Nuclear Power" OR "AI Data Center"')

RSS_FEEDS = {
    "GNews_Defense": f"https://news.google.com/rss/search?q={Q_DEF}&hl=en-US&gl=US&ceid=US:en",
    "GNews_BigTech": f"https://news.google.com/rss/search?q={Q_TEC}&hl=en-US&gl=US&ceid=US:en",
    "Bloomberg": "https://www.bloomberg.com/feeds/bview/main.rss"
}

def collect():
    print("🌐 [Ver 0.1.5] 48시간 이내 속보만 엄선 수집 중...")
    all_articles = []
    # [핵심] 수집 기준 시간 설정: 현재부터 48시간 전
    now = datetime.now(timezone.utc)
    limit = now - timedelta(hours=48)

    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                pub_at = entry.get('published', '')
                try:
                    # 날짜 파싱 및 타임존 보정
                    pub_date = parser.parse(pub_at)
                    if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
                    
                    # [필터 적용] 48시간 이내 기사만 리스트에 추가
                    if pub_date >= limit:
                        all_articles.append({
                            "source": name,
                            "title": entry.get('title', ''),
                            "link": entry.get('link', ''),
                            "published_at": pub_at,
                            "summary": entry.get('summary', '')[:500]
                        })
                except: continue
        except: pass
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"collected_at": str(now), "articles": all_articles}, f, ensure_ascii=False, indent=4)
    print(f"✅ 필터링 완료: 총 {len(all_articles)}건의 속보 저장.")

if __name__ == "__main__": collect()
