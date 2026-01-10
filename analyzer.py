"""
Module: analyzer.py | Version: 0.6.6 | Updated: 2026-01-11
Description: Adjusted to 48h filter. Mandatory 5-step report with Historical Analysis.
"""
import json, time, requests, os, re
from datetime import datetime, timedelta, timezone
from dateutil import parser

RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_telegram(report, url=None):
    if not TELEGRAM_BOT_TOKEN: return
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + report, "parse_mode": "Markdown"}
    if url:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={url}&text=시나리오요청"}]]})
    requests.post(api_url, data=payload, timeout=10)

def analyze_core(art):
    # [보스 지침] 8단계 내부 로직을 수행하고 5단계로 출력
    prompt = f"""당신은 한국 시장 특화 헤지펀드 리서치 디렉터입니다. 
다음 뉴스를 정밀 분석하십시오. 안보 이슈는 방산주/환율 관점에서 '과거 유사 사례의 주가 변동폭'을 반드시 포함해야 합니다.

[필수 JSON 키]:
1. title: 뉴스 타이틀
2. media: 매체 정보
3. impact: 영향도 및 과거 전례 대비 주가 패턴 분석 (상세히)
4. stocks: 주가 영향 종목 (테마/섹터)
5. summary: 3줄 요약
6. score: 0.0 ~ 10.0

뉴스: {art['title']} - {re.sub(r'<.*?>', '', art.get('summary', ''))}
"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.2}}, timeout=30)
        raw = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw)
    except: return None

def main():
    if not os.path.exists('breaking_news.json'): return
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    # [보스 지시] 24시간에서 48시간으로 기준 조정
    now = datetime.now(timezone.utc)
    limit = now - timedelta(hours=48)
    
    count = 0
    for art in articles[:15]:
        try:
            pub_date = parser.parse(art.get('published_at', '2000-01-01'))
            if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            # 48시간 이내 뉴스만 통과 (과거 2018년 뉴스 등 배제)
            if pub_date < limit or "2018" in art.get('published_at', ''): continue
            
            res = analyze_core(art)
            # 영향도 2.0 이하 뉴스는 발송하지 않음 (보스 지침)
            if not res or res.get('score', 0) <= 2.0: continue
            
            # 보스 요청 5단계 규격 복구
            report = f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
            report += f"2️⃣ **매체정보**: {art.get('source')} ({res.get('media')})\n"
            report += f"3️⃣ **영향도 및 과거분석 ({res.get('score')}점)**: {res.get('impact')}\n"
            report += f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
            report += f"5️⃣ **뉴스 요약**: {res.get('summary')}"
            
            send_to_telegram(report, art['link'])
            count += 1
            time.sleep(30)
        except: continue

    if count == 0:
        send_to_telegram("현재 글로벌 시장에서 한국 증시에 파급력을 줄 만한 유효 속보(2.0점 초과)가 없습니다.")

if __name__ == "__main__":
    main()
