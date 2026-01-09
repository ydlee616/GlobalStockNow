#!/usr/bin/env python3
# GlobalStockNow Collector v6.1 (Anti-Block & Fallback Edition)
import json
import datetime
import time
import random
from duckduckgo_search import DDGS

SEARCH_KEYWORDS = [
    "Samsung Electronics stock news",
    "SK Hynix HBM market share",
    "Global AI semiconductor trends",
    "NVIDIA vs competitors news",
    "Tesla EV sales impact Korea",
    "US Fed interest rate decision effect",
    "CES 2026 Samsung LG news"
]

def collect_news_from_ddg():
    print(f"[{datetime.datetime.now()}] 🦆 DuckDuckGo 검색 엔진 가동 (안전 모드)...")
    
    all_news = []
    seen_urls = set()

    with DDGS() as ddgs:
        for keyword in SEARCH_KEYWORDS:
            try:
                print(f"   🔎 검색 시도: '{keyword}'...")
                
                # 1차 시도: 지난 24시간(d) 뉴스 검색
                results = list(ddgs.news(keywords=keyword, region="wt-wt", safesearch="off", timelimit="d", max_results=5))
                
                # 2차 시도: 결과가 없으면 지난 1주일(w)로 범위 확장 (Fallback)
                if not results:
                    print(f"      👉 오늘 뉴스가 없어 '지난 주' 범위로 확장합니다.")
                    time.sleep(2) # 잠시 대기
                    results = list(ddgs.news(keywords=keyword, region="wt-wt", safesearch="off", timelimit="w", max_results=3))

                if results:
                    count = 0
                    for r in results:
                        if r['url'] in seen_urls: continue
                        seen_urls.add(r['url'])
                        
                        news_item = {
                            "source": r.get('source', 'Unknown'),
                            "title": r.get('title', ''),
                            "link": r.get('url', ''),
                            "published_at": r.get('date', str(datetime.datetime.now())),
                            "summary": r.get('body', '')
                        }
                        all_news.append(news_item)
                        count += 1
                    print(f"      ✅ {count}건 수집 완료")
                else:
                    print(f"      ❌ 확장 검색에도 결과 없음")

                # 🔥 핵심: 봇 차단 방지를 위한 랜덤 대기 (3~6초)
                wait_time = random.uniform(3, 6)
                print(f"      💤 {wait_time:.1f}초 대기...")
                time.sleep(wait_time)

            except Exception as e:
                print(f"   ⚠️ 오류 발생: {e}")
                time.sleep(5)

    print(f"✅ 총 {len(all_news)}개의 뉴스를 확보했습니다.")
    return all_news

def save_to_json(news_list):
    filename = "breaking_news.json"
    data = {
        "collected_at": str(datetime.datetime.now()),
        "count": len(news_list),
        "articles": news_list
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"💾 저장 완료: {filename}")

if __name__ == "__main__":
    articles = collect_news_from_ddg()
    save_to_json(articles)
