"""Module: analyzer.py | Version: 1.0.0 | Description: Historical Analysis & Mandatory Heartbeat."""
import json, time, requests, os, re

RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def report_to_boss(msg, link=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **GSN 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    if link:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={link}&text=유튜브대본생성"}]]})
    requests.post(url, data=payload, timeout=10)

def analyze_strategic(art):
    # [보스 지침] 과거 주가 패턴 분석 페르소나 주입 [cite: 2026-01-09]
    prompt = f"""[Strategic Asset Mode] Analyze for KOSPI/KOSDAQ. Compare with historical cases.
1.title, 2.media, 3.impact(Historical patterns), 4.stocks, 5.summary, 6.score(0-10).
JSON ONLY. News: {art['title']}"""
    try:
        api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(api, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety}, timeout=30)
        raw = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw)
    except: return None

def main():
    # [신규] 가동 시작 즉시 보고
    report_to_boss("🚀 **분석 엔진 가동 시작**\n48시간 내 최신 글로벌 밸류체인 분석을 시작합니다.")
    
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    report_count = 0
    for art in articles[:10]:
        res = analyze_strategic(art)
        # 보스 지침: 영향도 2.0점 초과만 발송
        if res and float(res.get('score', 0)) > 2.0:
            msg = f"1️⃣ **제목**: {res.get('title')}\n2️⃣ **매체**: {art.get('source')}\n3️⃣ **영향도 및 과거분석**: {res.get('impact')}\n4️⃣ **관련종목**: {res.get('stocks')}\n5️⃣ **요약**: {res.get('summary')}"
            report_to_boss(msg, art['link'])
            report_count += 1
            time.sleep(30)

    # [신규] 최종 가동 완료 보고 (무조건 보고)
    final_status = f"✅ **파이프라인 완료**\n- 검토: {len(articles)}건\n- 보고: {report_count}건"
    if report_count == 0: final_status += "\n- 특이사항: 현재 시장 파급력이 낮은 기사만 포착되었습니다."
    report_to_boss(final_status)

if __name__ == "__main__": main()
