#!/usr/bin/env python3
# GlobalStockNow Collector v3.2 - RSS + X 실시간 병행 + 키워드 통일 (2026.1.8)
# RSS와 X 키워드 동일 적용, CES 기간 자동 #CES2026 추가

import feedparser
import json
import subprocess
import datetime
import sys

# RSS와 X에 공통으로 사용하는 키워드 목록 (모두 소문자로 비교)
COMMON_KEYWORDS = [
    # 한국 기업
    'samsung', 'lg', 'hyundai', 'kia', 'sk hynix', 'posco', 'kakao', 'naver', 'coupang',
    # 글로벌 주요 기업 (한국 영향 큼)
    'nvidia', 'tesla', 'apple', 'microsoft', 'google', 'amazon', 'meta', 'intel', 'amd',
    'qualcomm', 'tsmc', 'asml', 'arm', 'broadcom',
    # 기술 키워드
    'ces', 'ces 2026', 'micro rgb', 'oled', 'qd-oled', 'hbm', 'dram', 'nand', 'foundry',
    'ai', 'artificial intelligence', 'robot', 'humanoid', 'atlas', 'cloid', 'vision ai',
    'ev', 'battery', 'semiconductor', 'chip', 'supply chain', 'tariff', 'trade war',
    'earnings', 'guidance', 'revenue', 'profit', 'fed', 'interest rate'
]

# CES 기간 자동 감지 (2026년 1월 1일 ~ 1월 31일)
today = datetime.date.today()
is_ces_period = datetime.date(2026, 1, 1) <= today <= datetime.date(2026, 1, 31)

# X 쿼리 동적 생성
ces_hashtags = " OR #CES2026 OR #CES" if is_ces_period else ""
X_QUERY = f"({' OR '.join([kw for kw in COMMON_KEYWORDS if not kw.startswith('#')])}){ces_hashtags} lang:en OR lang:ko"

def collect_from_rss():
    print("Google News RSS 수집 시작...")
    feeds = [
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB",  # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB",  # Technology
        "https://news.google.com/rss/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx1YlRZU0FtVnVLQUFQAQ",          # World
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    ]
    
    news_list = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            print(f"  {url} → {len(feed.entries)}개 항목 확인")
            for entry in feed.entries:
                title = entry.get('title', '')
                summary = entry.get('summary', '') or ''
                content = (title + " " + summary).lower()
                
                if any(kw.lower() in content for kw in COMMON_KEYWORDS):
                    news_list.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get('published', datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")),
                        "summary": summary[:500],
                        "source": "Google News RSS"
                    })
        except Exception as e:
            print(f"RSS 피드 오류: {e}")
    
    return news_list

def collect_from_x():
    print(f"X(Twitter) 실시간 수집 시작... 쿼리: {X_QUERY}")
    try:
        result = subprocess.check_output([
            "snscrape", "--jsonl", "--max-results", "40", "twitter-search", X_QUERY
        ], stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
        
        posts = []
        for line in result.splitlines():
            if not line.strip():
                continue
            try:
                post = json.loads(line)
                posts.append({
                    "title": f"[X] @{post['user']['username']}: {post['rawContent'][:150]}...",
                    "link": post['url'],
                    "published": post['date'],
                    "summary": post['rawContent'],
                    "source": "X (Twitter)"
                })
            except json.JSONDecodeError:
                continue
        
        print(f"  X에서 {len(posts)}개 포스트 수집")
        return posts
    except subprocess.CalledProcessError as e:
        print("snscrape 실행 실패 (설치 안 됨 또는 오류)")
        return []
    except Exception as e:
        print(f"X 수집 오류: {e}")
        return []

def collect_news():
    print("=== 글로벌스톡나우 속보 수집 시작 ===")
    
    rss_news = collect_from_rss()
    x_news = collect_from_x()
    
    # 중복 제거 (link 기준)
    all_news = rss_news + x_news
    seen_links = set()
    unique_news = []
    for item in all_news:
        if item['link'] not in seen_links:
            seen_links.add(item['link'])
            unique_news.append(item)
    
    # 최신순 정렬
    unique_news.sort(key=lambda x: x['published'], reverse=True)
    
    # 최대 40개 제한
    final_news = unique_news[:40]
    
    # 파일 저장
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, indent=2, ensure_ascii=False)
    
    print(f"최종 수집 완료: 총 {len(final_news)}개 뉴스")
    print(f"  - RSS: {len(rss_news)}개")
    print(f"  - X 실시간: {len(x_news)}개")
    print("=== 수집 완료 ===\n")

if __name__ == "__main__":
    collect_news()
