#!/usr/bin/env python3
# GlobalStockNow News Collector v0.4 - 필터 완화 버전

import feedparser
import json
from datetime import datetime, timedelta
import re

KEYWORDS = [
    'nvidia', 'amd', 'intel', 'tsmc', 'samsung', 'sk hynix', 'semiconductor', 'chip',
    'fed', 'federal reserve', 'interest', 'rate', 'powell', 'fomc',
    'tesla', 'ev', 'battery', 'cybertruck',
    'apple', 'iphone', 'aapl', 'microsoft', 'msft', 'amazon', 'meta',
    'oil', 'opec', 'energy',
    'bitcoin', 'crypto', 'btc', 'eth',
    'trade', 'tariff', 'china stock', 'hkex'
]

def collect_news():
    print("속보 수집 시작")

    feeds = [
        "https://news.google.com/rss/topics/CAAqJQgKIh9DQkFTRVFvSUwyMHZNSEJ5TVhBU0FtVnVLQUFQAQ?hl=en-US&gl=US&ceid=US:en",  # US Top
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkF
