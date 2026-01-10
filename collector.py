import feedparser
import json
import os
from datetime import datetime

# ==========================================
# [Ver 0.1.1] 글로벌 정예 뉴스 소스 (국내 매체 배제)
# ==========================================
RSS_FEEDS = {
    "Bloomberg_Markets": "https://www.bloomberg.com/feeds/bview/main.rss",
    "NYTimes_Business": "https://rss.nytimes.com/services/xml/rss/nt/Business.xml",
    "CNN_Business": "http://rss.cnn.com/rss/money_latest.rss",
    "Reuters_Finance": "https://www.reutersagency.com/feed/?best-sectors=business-finance&post_type=best",
    "GoogleNews_Global": "https://news.google.com/rss/search?q=global+economy+stock+market&hl=en-US&gl=US&ceid=US:en",
    "Nikkei_Asia_Japan": "https://asia.nikkei.com/rss/feed/nar",
    "CCTV_English_China": "https://english.cctv.com/data/rss/index.xml",
    "NDTV_Profit_India": "https://feeds.feedburner.com/ndtvprofit-latest",
    "Antara_Indonesia": "https://en.antaranews.com/rss/business.xml"
}

def collect_global_news():
    print(f"🌐 [GlobalStockNow Ver 0.1.1] 수집 가동: {datetime.now()}")
    all_articles = []

    for source_name, url in RSS_FEEDS.items():
        try:
            print(f"   📡 Connecting to {source_name}...")
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                all_articles.append({
                    "source": source_name,
                    "title": entry.get('title', ''),
                    "link": entry.get('link', ''),
                    "published_at": entry.get('published', ''),
                    "summary": entry.get('summary', '')[:500]
                })
        except Exception as e:
            print(f"   ❌ {source_name} 실패: {e}")

    output = {"collected_at": str(datetime.now()), "count": len(all_articles), "articles": all_articles}
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"✅ 수집 완료: 총 {len(all_articles)}건 확보.")

if __name__ == "__main__":
    collect_global_news()
