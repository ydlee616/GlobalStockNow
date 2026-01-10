import feedparser
import json
import os
from datetime import datetime

# ==========================================
# [Ver 0.1.1] 글로벌 정예 뉴스 소스 (국내 매체 배제)
# ==========================================
RSS_FEEDS = {
    # 미국/글로벌 (핵심 매크로 소스)
    "Bloomberg_Markets": "https://www.bloomberg.com/feeds/bview/main.rss",
    "NYTimes_Business": "https://rss.nytimes.com/services/xml/rss/nt/Business.xml",
    "CNN_Business": "http://rss.cnn.com/rss/money_latest.rss",
    "Reuters_Finance": "https://www.reutersagency.com/feed/?best-sectors=business-finance&post_type=best",
    "GoogleNews_Global": "https://news.google.com/rss/search?q=global+economy+stock+market&hl=en-US&gl=US&ceid=US:en",
    
    # 아시아/신흥국 (지역별 영향력 매체)
    "Nikkei_Asia_Japan": "https://asia.nikkei.com/rss/feed/nar",
    "CCTV_English_China": "https://english.cctv.com/data/rss/index.xml",
    "NDTV_Profit_India": "https://feeds.feedburner.com/ndtvprofit-latest",
    "Antara_Indonesia": "https://en.antaranews.com/rss/business.xml"
}

def collect_pure_global_news():
    print(f"🌐 [GlobalStockNow Ver 0.1.1] 글로벌 수집 가동: {datetime.now()}")
    all_articles = []

    for source_name, url in RSS_FEEDS.items():
        try:
            print(f"   📡 Connecting to {source_name}...")
            feed = feedparser.parse(url)
            
            # 각 소스별 최신 10개 뉴스를 수집합니다.
            for entry in feed.entries[:10]:
                # [보스 지침 반영] 키워드 필터링을 하지 않고 모든 뉴스를 수집합니다.
                # 이를 통해 전쟁, 납치 등 핵심 매크로 뉴스의 누락을 방지합니다.
                
                article = {
                    "source": source_name,
                    "title": entry.get('title', ''),
                    "link": entry.get('link', ''),
                    "published_at": entry.get('published', ''),
                    "summary": entry.get('summary', '')[:500] # 분석용 텍스트 확보
                }
                all_articles.append(article)
        except Exception as e:
            print(f"   ❌ {source_name} 연결 실패: {e}")

    # 수집 결과 저장 (분석기가 읽을 파일)
    output = {
        "collected_at": str(datetime.now()),
        "count": len(all_articles),
        "articles": all_articles
    }
    
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 수집 완료: 총 {len(all_articles)}건의 글로벌 뉴스 확보.")

if __name__ == "__main__":
    collect_pure_global_news()
