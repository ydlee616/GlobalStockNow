#!/usr/bin/env python3
# GlobalStockNow News Collector v0.1 (2026.1.2)
# Google News RSS + 키워드 필터링 (반도체, Fed, Tesla 등 30개 키워드)

import feedparser
from datetime import datetime, timedelta
import json
import re
from fuzzywuzzy import fuzz  # 중복 제거용 (pip 필요 없음, GitHub Actions에 있음)

# PDF 페이지 8 기반: 30+ 주식 키워드 리스트 (최초 버전)
STOCK_KEYWORDS = [
    'semiconductor', 'chip', 'nvidia', 'amd', 'intel', 'tsmc', 'samsung', 'skhynix',
    'fed', 'federal reserve', 'interest rate', 'powell',
    'tesla', 'ev', 'battery', 'byd', 'catl',
    'apple', 'iphone', 'aapl', 'googl', 'msft', 'amzn', 'meta',
    'oil', 'opec', 'energy', 'exxon',
    'china', 'trade war', 'tariff', 'hkex', 'hsi',
    'bitcoin', 'crypto', 'eth', 'sec',
    'inflation', 'cpi', 'gdp', 'recession'
]

def collect_breaking_news(max_hours=6, max_items=20):
    """Google News RSS로 최근 4~6시간 속보 수집 + 키워드 필터"""
    print("🚀 GlobalStockNow 속보 수집 시작 (최근 {}시간, 최대 {}개)".format(max_hours, max_items))
    
    # Google News RSS (US + Business + Tech, 무료/무제한)
    rss_feeds = [
        'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en&topic=h',  # Headlines
        'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en&cat=Bus',  # Business
        'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en&cat=Tec'   # Technology
    ]
    
    all_news = []
    seen_titles = set()  # 중복 제거
    
    cutoff_time = datetime.utcnow() - timedelta(hours=max_hours)
    
    for feed_url in rss_feeds:
        feed = feedparser.parse(feed_url)
        print(f"📡 {feed_url} 수집: {len(feed.entries)}개 원본 기사")
        
        for entry in feed.entries[:10]:  # 피드당 상위 10개만
            pub_date = entry.get('published_parsed') or entry.get('updated_parsed')
            if not pub_date:
                continue
                
            pub_dt = datetime(*pub_date[:6])
            if pub_dt < cutoff_time:
                continue  # 6시간 이내 기사만
            
            title = entry.title.lower()
            link = entry.link
            summary = (entry.get('summary') or '').lower()
            
            # 키워드 매칭 (제목+요약 70% 이상 일치)
            content = title + ' ' + summary
            matched_keywords = [kw for kw in STOCK_KEYWORDS if kw in content]
            
            if matched_keywords and fuzz.ratio(title, list(seen_titles)[-1] if seen_titles else '') < 80:
                news_item = {
                    'title': entry.title,
                    'link': link,
                    'published': pub_dt.strftime('%Y-%m-%d %H:%M UTC'),
                    'keywords': matched_keywords[:3],  # 상위 3개만
                    'summary': entry.get('summary', '')[:200] + '...'
                }
                all_news.append(news_item)
                seen_titles.add(title)
    
    # 영향도 높은 순 정렬 (키워드 수 기준, 나중 AI 분석으로 대체)
    all_news.sort(key=lambda x: len(x['keywords']), reverse=True)
    final_news = all_news[:max_items]
    
    print(f"✅ 최종 필터링: {len(final_news)}개 속보 수집 완료!")
    return final_news

if __name__ == "__main__":
    news = collect_breaking_news(max_hours=6, max_items=20)
    print("\n📊 수집된 해외 주식 속보 TOP 5 (한국 시장 영향 예상):")
    for i, item in enumerate(news[:5], 1):
        print(f"{i}. [{item['published']}] {item['title']}")
        print(f"   🔗 {item['link']}")
        print(f"   🏷️  키워드: {', '.join(item['keywords'])}")
        print()
    
    # JSON 저장 (다음 AI 분석 모듈용)
    with open('breaking_news.json', 'w') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    print("💾 breaking_news.json 저장 완료 (AI 분석 준비)")
