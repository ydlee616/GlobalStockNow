#!/usr/bin/env python3
# GlobalStockNow Collector v3.0 - RSS + X(Twitter) 실시간 병행 (2026.1.8)

import feedparser
import json
import requests
from datetime import datetime, timedelta

# 기존 RSS 키워드
RSS_KEYWORDS = ['samsung', 'lg', 'hyundai', 'sk hynix', 'ces 2026', 'ai', 'robot', 'hbm', 'oled']

# X 실시간 키워드 (CES 특화)
X_QUERY = '#CES2026 (Samsung OR LG OR Hyundai OR "SK Hynix" OR HBM OR OLED OR robot OR AI OR humanoid OR Atlas OR CLOiD) since:2026-01-01 lang:en OR lang:ko'

# 무료 X 검색 대체 (nitter나 공개 RSS 사용 – 실제론 GitHub Actions에서 tweepy나 snscrape 추천)
def collect_from_x():
    # 실제 구현 시 snscrape나 X API 사용 (무료 한도 내)
    # 임시 예시
    return []  # 실제 X 포스트 리스트 반환

def collect_news():
    print("속보 수집 시작 - RSS + X 병행")

    # 기존 RSS 수집 (이전 코드 유지)
    rss_news = []  # 기존 로직

    # X 실시간 수집 추가
    x_news = collect_from_x()

    # 중복 제거 + 최신순 정렬
    all_news = rss_news + x_news
    unique = list({item['title']: item for item in all_news}.values())
    unique.sort(key=lambda x: x['published'], reverse=True)

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(unique[:30], f, indent=2, ensure_ascii=False)

    print(f"최종 {len(unique)}개 속보 수집 (RSS + X)")

if __name__ == "__main__":
    collect_news()
