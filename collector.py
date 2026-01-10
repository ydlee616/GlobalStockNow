"""Module: collector.py | Version: 0.1.4 | Updated: 2026-01-10"""
import feedparser, json, os, urllib.parse
from datetime import datetime

Q_DEF = urllib.parse.quote('KF-21 OR "Nuclear Submarine" OR "K-Defense" OR "North Korea"')
Q_TEC = urllib.parse.quote('Apple OR Meta OR "Smart Glasses" OR "AR Glasses" OR "AI Data Center"')
Q_ENE = urllib.parse.quote('"Nuclear Power" OR SMR OR "Solar Power"')

RSS_FEEDS = {
    "GNews_Defense": f"https://news.google.com/rss/search?q={Q_DEF}&hl=en-US&gl=US&ceid=US:en",
    "GNews_BigTech": f"https://news.google.com/rss/search?q={Q_TEC}&hl=en-US&gl=US&ceid=US:en",
    "GNews_Energy": f"https://news.google.com/rss/search?q={Q_ENE}&hl=en-US&gl=US&ceid=US:en",
    "Bloomberg": "https://www.bloomberg.com/feeds/bview/main.rss",
    "Nikkei": "https://asia.nikkei.com/rss/feed/nar"
}

def collect():
    print("🌐 [Ver 0.1.4] 고순도 뉴스 수집 중...")
    all_articles = []
    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]: # 소스당 8개로 정예화
                link = entry.get('link', '')
                if any(dom in link.lower() for dom in ['yna.co.kr', 'chosun.com']): continue
                all_articles.append({
                    "id": entry.get('id', link),
                    "source": name, "title": entry.get('title', ''), "link": link,
                    "published_at": entry.get('published', ''), "summary": entry.get('summary', '')[:500]
                })
        except: pass
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"collected_at": str(datetime.now()), "articles": all_articles}, f, ensure_ascii=False, indent=4)
    print(f"✅ {len(all_articles)}건 수집 완료.")

if __name__ == "__main__": collect()
