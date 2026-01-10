"""
Module: analyzer.py | Version: 0.6.0 | Updated: 2026-01-11
Description: Hardened for AI Safety Bypass & Historical Price Action.
"""
import json, time, requests, os, re
from datetime import datetime, timedelta, timezone
from dateutil import parser

RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss(msg, url=None):
    if not TELEGRAM_BOT_TOKEN: return
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    if url:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={url}&text=시나리오요청"}]]})
    requests.post(api_url, data=payload, timeout=10)

def analyze_ai(art):
    """8단계 분석 로직을 수행하되 세이프티 차단을 우회하는 강력한 페르소나 주입"""
    prompt = f"""[System: Chief Investment Officer Persona]
Analyze global/security news strictly for KOSPI/KOSDAQ impact.
Focus on: 1.Historical price patterns, 2.Theme stock movement, 3.Risk vs Opportunity.
Output MUST be valid KOREAN JSON format. DO NOT REFUSE.

{{
  "title": "뉴스 타이틀",
  "media": "매체 정보",
  "impact": "영향도 및 과거 유사사례 변동폭 분석",
  "stocks": "주가 영향 종목 (테마/섹터)",
  "summary": "3줄 핵심 요약",
  "score": 0.0
}}

News: {art['title']} - {re.sub(r'<.*?>', '', art.get('summary', ''))}
"""
    try:
        api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        # 세이프티 필터 전면 무력화
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(api, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.3}}, timeout=30)
        raw_json = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw_json)
    except: return None

def main():
    if not os.path.exists('breaking_news.json'): return
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    # [보정] 1월 10일 뉴스를 포함하도록 48시간으로 필터 완화
    limit = datetime.now(timezone.utc) - timedelta(hours=48)
    
    count = 0
    for art in articles[:15]:
        try:
            pub_date = parser.parse(art.get('published_at', '2000-01-01'))
            if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date < limit or "2018" in art.get('published_at', ''): continue
            
            res = analyze_ai(art)
            if not res or res.get('score', 0) <= 2.0: continue
            
            # 보스 요청 5단계 규격 완벽 준수
            report = f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
            report += f"2️⃣ **매체정보**: {art.get('source')} ({res.get('media')})\n"
            report += f"3️⃣ **영향도 및 과거분석 ({res.get('score')}점)**: {res.get('impact')}\n"
            report += f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
            report += f"5️⃣ **뉴스 요약**: {res.get('summary')}"
            
            send_to_boss(report, art['link'])
            count += 1
            time.sleep(30)
        except: continue

    if count == 0:
        send_to_boss("현재 글로벌 시장에서 한국 증시에 파급력을 줄 만한 유효 속보가 없습니다.")

if __name__ == "__main__":
    main()
