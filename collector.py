"""
Module: collector.py | Version: 0.1.3 | Updated: 2026-01-10
"""
import feedparser, json, os, urllib.parse
from datetime import datetime

# 전략 키워드 (방산, 빅테크, 에너지, 지정학 리스크)
Q_DEF = urllib.parse.quote('KF-21 OR "Nuclear Submarine" OR "K-Defense" OR "North Korea"')
Q_TEC = urllib.parse.quote('Apple OR Meta OR "Smart Glasses" OR "AR Glasses" OR "AI Data Center"')
Q_ENE = urllib.parse.quote('"Nuclear Power" OR SMR OR "Solar Power"')
Q_CRI = urllib.parse.quote('Earthquake OR "Natural Disaster" OR "Geopolitical Risk"')

RSS_FEEDS = {
    "Bloomberg_Markets": "https://www.bloomberg.com/feeds/bview/main.rss",
    "NYTimes_Biz": "https://rss.nytimes.com/services/xml/rss/nt/Business.xml",
    "Reuters_Finance": "https://www.reutersagency.com/feed/?best-sectors=business-finance&post_type=best",
    "GNews_K_Defense": f"https://news.google.com/rss/search?q={Q_DEF}&hl=en-US&gl=US&ceid=US:en",
    "GNews_BigTech": f"https://news.google.com/rss/search?q={Q_TEC}&hl=en-US&gl=US&ceid=US:en",
    "GNews_Energy": f"https://news.google.com/rss/search?q={Q_ENE}&hl=en-US&gl=US&ceid=US:en",
    "GNews_Crisis": f"https://news.google.com/rss/search?q={Q_CRI}&hl=en-US&gl=US&ceid=US:en",
    "Nikkei_Asia": "https://asia.nikkei.com/rss/feed/nar"
}

def collect():
    print(f"🌐 [Ver 0.1.3] 글로벌 수집 시작...")
    all_articles = []
    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                link = entry.get('link', '')
                # 국내 매체 배제
                if any(dom in link.lower() for dom in ['yna.co.kr', 'chosun.com', 'hankyung.com']): continue
                all_articles.append({
                    "source": name, "title": entry.get('title', ''), "link": link,
                    "published_at": entry.get('published', ''), "summary": entry.get('summary', '')[:500]
                })
        except: pass
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"collected_at": str(datetime.now()), "articles": all_articles}, f, ensure_ascii=False, indent=4)
    print(f"✅ 수집 완료: {len(all_articles)}건")

if __name__ == "__main__": collect()
