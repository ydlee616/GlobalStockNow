#!/usr/bin/env python3
# GlobalStockNow Collector v4.0 - 직접 사이트 크롤링 + X 실시간 (Google News 우회, 2026.1.9)

import json
import requests
from bs4 import BeautifulSoup
import subprocess
import datetime
import time

# 주요 뉴스 사이트 (CES 2026 집중)
NEWS_SITES = [
    ("https://www.engadget.com/tag/ces-2026/", "Engadget CES"),
    ("https://www.theverge.com/ces", "The Verge CES"),
    ("https://www.cnbc.com/ces/", "CNBC CES"),
    ("https://techcrunch.com/tag/ces-2026/", "TechCrunch CES"),
    ("https://www.cnet.com/ces/", "CNET CES"),
    ("https://www.tomshardware.com/tag/ces-2026", "Tom's Hardware"),
    ("https://www.androidcentral.com/ces", "Android Central")
]

# X 쿼리 (CES + 한국 기업)
X_QUERY = "#CES2026 (Samsung OR LG OR Hyundai OR \"SK Hynix\" OR HBM OR OLED OR robot OR Atlas OR CLOiD OR \"Micro RGB\") lang:en OR lang:ko"

def collect_from_sites():
    print("주요 뉴스 사이트 직접 크롤링 시작...")
    news_list = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for url, source in NEWS_SITES:
        try:
            response = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 사이트별 기사 링크/제목 추출 (간단 패턴)
            articles = soup.find_all('a', href=True)
            for a in articles[:30]:
                link = a['href']
                if not link.startswith('http'):
                    link = 'https://' + url.split('/')[2] + link
                title = a.get_text(strip=True)
                if len(title) > 20 and any(kw.lower() in title.lower
