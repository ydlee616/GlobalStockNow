"""Module: analyzer.py | Version: 0.6.7 | Updated: 2026-01-11"""
import json, time, requests, os, re

RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss(report, url):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + report, "parse_mode": "Markdown"}
    payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={url}&text=시나리오요청"}]]})
    requests.post(api_url, data=payload, timeout=10)

def analyze_logic(art):
    # 보스의 8단계 분석 페르소나 주입
    prompt = f"당신은 헤지펀드 이사입니다. 과거 전례와 비교하여 한국 증시 영향을 분석하세요.\nJSON 규격: title, media, impact, stocks, summary, score\n뉴스: {art['title']}"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]}, timeout=30)
        return json.loads(re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip())
    except: return None

def main():
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    for art in articles[:10]: # 이미 48시간 필터가 완료된 데이터들
        res = analyze_logic(art)
        # 보스 지침: 영향도 2.0점 이하(무의미한 뉴스)는 발송하지 않음
        if res and res.get('score', 0) > 2.0:
            report = f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n2️⃣ **매체정보**: {art.get('source')}\n3️⃣ **영향도 및 과거분석 ({res.get('score')}점)**: {res.get('impact')}\n4️⃣ **주가 영향 종목**: {res.get('stocks')}\n5️⃣ **뉴스 요약**: {res.get('summary')}"
            send_to_boss(report, art['link'])
            time.sleep(30)

if __name__ == "__main__": main()
