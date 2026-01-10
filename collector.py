"""Module: collector.py | Version: 1.2.0 | Focus: Multi-Query Deep Search"""
import feedparser, json, os, urllib.parse
from datetime import datetime, timedelta, timezone
from dateutil import parser

# [전략적 탐색 쿼리] 보스가 짚어낸 핵심 키워드 리스트
SEARCH_QUERIES = [
    'Nvidia G-Sync Pulsar impact',
    'Meta nuclear energy agreement AI',
    'Intel Panther Lake TOPS AI PC',
    'AMD Ryzen AI Max Plus',
    'CES 2026 Semiconductor supply chain'
]

def collect():
    print(f"🌍 [Ver 1.2.0] {len(SEARCH_QUERIES)}개의 핵심 타겟 웹 탐색 시작...")
    all_articles = []
    limit = datetime.now(timezone.utc) - timedelta(hours=48)

    for query in SEARCH_QUERIES:
        q_encoded = urllib.parse.quote(query)
        # 구글 뉴스 검색 엔진을 통한 실시간 웹 데이터 래핑
        search_url = f"https://news.google.com/rss/search?q={q_encoded}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(search_url)
        
        print(f"🔍 '{query}' 검색 중: {len(feed.entries)}건 발견")
        for entry in feed.entries[:15]: # 각 쿼리당 상위 15건 집중 분석
            try:
                pub_date = parser.parse(entry.get('published', ''))
                if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date >= limit:
                    all_articles.append({
                        "source": "WebSearch", "title": entry.get('title', ''),
                        "link": entry.get('link', ''), "published_at": entry.get('published', ''),
                        "summary": entry.get('summary', '')[:600]
                    })
            except: continue
    
    # 중복 제거 및 저장
    unique_articles = {a['link']: a for a in all_articles}.values()
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump({"articles": list(unique_articles)}, f, ensure_ascii=False, indent=4)
    print(f"✅ 탐색 완료: 총 {len(unique_articles)}건의 유효 기사 확보.")

if __name__ == "__main__": collect()
