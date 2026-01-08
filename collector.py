#!/usr/bin/env python3
# GlobalStockNow Collector v6.0 (DuckDuckGo Search Edition)
# 작성일: 2026.01.09
# 기능: AI 의존 없이 검색엔진에서 직접 최신 뉴스 링크를 긁어옴 (수집 실패율 0% 도전)

import json
import datetime
import time
from duckduckgo_search import DDGS

# ---------------------------------------------------------
# [설정] 검색할 키워드 리스트 (영어/한국어 혼합)
# ---------------------------------------------------------
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
    print(f"[{datetime.datetime.now()}] 🦆 DuckDuckGo 검색 엔진 가동...")
    
    all_news = []
    seen_urls = set() # 중복 제거용

    # 객체 생성 방식을 최신 라이브러리에 맞춤
    with DDGS() as ddgs:
        for keyword in SEARCH_KEYWORDS:
            try:
                print(f"   🔎 검색 중: '{keyword}'...")
                # timelimit='d': 지난 1일(24시간) 이내 뉴스만 검색
                # max_results=5: 키워드당 5개씩만
                results = ddgs.news(keywords=keyword, region="wt-wt", safesearch="off", timelimit="d", max_results=5)
                
                if results:
                    for r in results:
                        # 중복 기사 제거
                        if r['url'] in seen_urls:
                            continue
                        
                        seen_urls.add(r['url'])
                        
                        # 데이터 표준화
                        news_item = {
                            "source": r.get('source', 'Unknown'),
                            "title": r.get('title', ''),
                            "link": r.get('url', ''),
                            "published_at": r.get('date', str(datetime.datetime.now())),
                            "summary": r.get('body', '')  # 검색 결과의 짧은 요약
                        }
                        all_news.append(news_item)
                else:
                    print(f"      -> '{keyword}' 관련 최신 뉴스 없음")
                    
            except Exception as e:
                print(f"   ⚠️ 키워드 '{keyword}' 검색 중 오류: {e}")
                time.sleep(1) # 차단 방지용 잠시 대기

    print(f"✅ 총 {len(all_news)}개의 최신 속보를 확보했습니다.")
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
    print(f"💾 저장 완료: {filename} ({len(news_list)}건)")

if __name__ == "__main__":
    # 1. 뉴스 강제 수집
    articles = collect_news_from_ddg()
    
    # 2. 결과 저장 (없으면 빈 리스트라도 저장)
    if not articles:
        print("⚠️ 검색 결과가 없습니다. (검색어 조정 필요)")
        articles = []
        
    save_to_json(articles)
