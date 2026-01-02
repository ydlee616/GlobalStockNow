#!/usr/bin/env python3
# GlobalStockNow News Collector v0.2 (2026.1.3)
# 강화된 키워드 필터링

import feedparser
from datetime import datetime, timedelta
import json
import re

# 강화된 주식 관련 키워드 (대소문자 무시)
STOCK_KEYWORDS = [
    'nvidia', 'amd', 'intel', 'tsmc', 'samsung', 'sk hynix', 'semiconductor', 'chip',
    'fed', 'federal reserve', 'interest rate', 'powell', 'rate cut', 'rate hike',
    'tesla', 'electric vehicle', 'ev sales', 'cybertruck',
    'apple', 'iphone', 'aapl', 'microsoft', 'msft', 'amazon', 'meta', 'google stock',
    'oil price', 'brent', 'wti', 'opec',
    'trade war', 'tariff', 'china stock',
    'bitcoin', 'crypto', 'ethereum', 'btc'
]

def is_stock_related(text):
    text_lower = text.lower()
    # 링크에 google.com 포함된 것은 제외 (Google News 특성)
    if 'news.google.com' in text_lower:
        return False
    # 키워드 매칭 (단어 경계 고려)
    for keyword in STOCK_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            return True
    return False

def collect_breaking_news(max_hours=6, max_items=20):
    print(f"속보 수집 시작 (최근 {max_hours}시간, 최대 {max_items}개)")

    rss_feeds = [
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en',  # World
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en',  # Business
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en'   # Technology
    ]

    all_news = []
    cutoff_time = datetime.utcnow() - timedelta(hours=max_hours)

    for feed_url in rss_feeds:
        feed = feedparser.parse(feed_url)
        print(f"{feed_url}에서 {len(feed.entries)}개 기사 확인")

        for entry in feed.entries:
            if len(all_news) >= max_items * 3:
                break

            pub_time = entry.get('published_parsed')
            if not pub_time:
                continue
            pub_dt = datetime(*pub_time[:6])
            if pub_dt < cutoff_time:
                continue

            title = entry.title
            summary = entry.get('summary', '') or ''
            content = title + ' ' + summary

            if is_stock_related(content):
                all_news.append({
                    'title': title,
                    'link': entry.link,
                    'published': pub_dt.strftime('%Y-%m-%d %H:%M UTC'),
                    'summary': summary[:200]
                })

    # 중복 제거
    seen_titles = set()
    unique_news = []
    for item in all_news:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            unique_news.append(item)

    final_news = unique_news[:max_items]

    print(f"최종 {len(final_news)}개 주식 관련 속보 수집 완료")

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, indent=2, ensure_ascii=False)

    print("breaking_news.json 저장 완료")

if __name__ == "__main__":
    collect_breaking_news()
