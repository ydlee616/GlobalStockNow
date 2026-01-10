"""
Project: GlobalStockNow
Module: collector.py
Version: 0.1.2
Updated: 2026-01-10
Description: Strategic news collection with domain exclusion and global keyword targeting.
"""
import feedparser, json, os, urllib.parse
from datetime import datetime

# 전략 키워드 조합 (영문)
QUERY_DEFENSE = urllib.parse.quote('KF-21 OR "Nuclear Submarine" OR "K-Defense" OR "South Korea weapons" OR "North Korea"')
QUERY_TECH = urllib.parse.quote('Apple OR Meta OR "Smart Glasses" OR "AR Glasses" OR "AI Data Center"')
QUERY_ENERGY = urllib.parse.quote('"Nuclear Power" OR SMR OR "Small Modular Reactor" OR "Solar Power"')
QUERY_CRISIS = urllib.parse.quote('Earthquake OR "Natural Disaster" OR "Climate Change" OR "Geopolitical Risk"')

RSS_FEEDS = {
    "Bloomberg_Markets": "https://www.bloomberg.com/feeds/bview/main.rss",
    "NYTimes_Biz": "https://rss.nytimes.com/services/xml/rss/nt/Business.xml",
    "CNN_Biz": "http://rss.cnn.com/rss/money_latest.rss",
    "Reuters_Finance": "https://www.reutersagency.com/feed/?best-sectors=business-finance&post_type=best",
    "GNews_K_Defense": f"https://news.google.com/rss/search?q={QUERY_DEFENSE}&hl=en-US&gl=US&ceid=US:en",
    "GNews_BigTech": f"https://news.google.com/rss/search?q={QUERY_TECH}&hl=en-US&gl=US&ceid=US:en",
    "GNews_Energy": f"https://news.google.com/rss/search?q={QUERY_ENERGY}&hl=en-US&gl=US&ceid=US:en",
    "GNews_Macro_Risk": f"https://news.google.com/rss/search?q={QUERY_CRISIS}&hl=en-US&gl=US&ceid=US:en",
    "Nikkei_Asia": "https://asia.nikkei.com/rss/feed/nar",
    "CCTV_English": "https://english.cctv.com/data/rss/index.xml",
    "NDTV_Profit": "https://feeds.feedburner.com/ndtvprofit-latest",
    "Antara_Indo": "https://en.antaranews.com/rss/business.xml"
}

def collect_strategic_news():
    print(f"🌐 [Ver 0.1.2] 글로벌 수집 가동: {datetime.now()}")
    all_articles = []
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                link = entry.get('link', '')
                # 국내 매체 도메인 배제
                if any(dom in link.lower() for dom in ['yna.co.kr', 'koreaherald.com', 'koreatimes.co.kr', 'chosun.com', 'hankyung.com', 'joins.com']):
                    continue
                all_articles.append({
                    "source": source_name, "title": entry.get('title', ''), "link": link,
                    "published_at": entry.get('published', ''), "summary": entry.get('summary', '')[:500]
                })
        except: pass
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"collected_at": str(datetime.now()), "articles": all_articles}, f, ensure_ascii=False, indent=4)
    print(f"✅ 수집 완료: {len(all_articles)}건")

if __name__ == "__main__":
    collect_strategic_news()
