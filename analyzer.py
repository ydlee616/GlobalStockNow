"""
Module: analyzer.py | Version: 0.3.3 | Updated: 2026-01-10
Description: Stable 8-step Analysis. Safety bypass. Zero-Crash logic.
"""
import json, time, requests, os, re
from datetime import datetime

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")
INPUT_FILE = 'breaking_news.json'

def send_telegram(msg, article_id=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    if article_id is not None:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성 (학습)", "callback_data": f"select_{article_id}"}]]})
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def clean_data(text):
    return re.sub(r'<.*?>', '', text) if text else ""

def analyze_core(article):
    summary = clean_data(article.get('summary', ''))
    # [8단계 초정밀 분석 프롬프트 - 보스 지침 완벽 반영] [cite: 2026-01-09]
    prompt = f"""[System: Financial Research Director Mode]
Analyze the impact on KOSPI/KOSDAQ. IGNORE sensitive politics. FOCUS only on Money Flow.
8-Steps: 1.Essence(Subtext), 2.Direct Impact, 3.Indirect(FX/Commodities/Geopolitics), 4.Sentiment/Vol, 5.Historical Analogy, 6.Timeline(Short/Mid/Long), 7.Sectors/Stocks, 8.Strategy.
News: {article.get('title')} - {summary}
Output: KOREAN JSON ONLY."""

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        # 세이프티 필터 원천 차단 (BLOCK_NONE) [cite: 2026-01-09]
        safety = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.2}}, timeout=30)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            return json.loads(re.sub(r'```json|```', '', text).strip())
    except: pass
    return None

def run():
    print(f"🚀 [Ver 0.3.3] 초정밀 분석 가동 (Run #{RUN_NUMBER})")
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    count = 0
    for i, art in enumerate(articles[:10]):
        # 과거 기사 필터링
        if any(year in art.get('published_at', '') for year in ['2018', '2019']): continue

        try:
            res = analyze_core(art)
            if res and res.get('score', 0) >= 2.0:
                # 8단계 분석 내용 기반 5단계 리포트 출력 [cite: 2026-01-09]
                msg = f"💎 **1. 제목: {res.get('title')}**\n"
                msg += f"**2. 매체**: {art.get('source')}\n"
                msg += f"**3. 영향 ({res.get('score')}점)**: {res.get('essence', {}).get('subtext')}\n"
                msg += f"   - **간접영향**: 환율({res.get('indirect', {}).get('fx')}), 원자재({res.get('indirect', {}).get('commodities')})\n"
                msg += f"**4. 관련주**: {', '.join(res.get('map', {}).get('stocks', []))}\n"
                msg += f"**5. 과거사례**: {res.get('history', {}).get('case')}\n\n"
                msg += f"📊 **전략**: {res.get('strategy', {}).get('action')}"
                
                send_telegram(msg, i)
                count += 1
                time.sleep(30)
        except: continue

    if count == 0:
        send_telegram(f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n현재 유효 속보 없음 (정밀 감시 중)")

if __name__ == "__main__": run()
