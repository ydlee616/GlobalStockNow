"""Module: analyzer.py | Version: 1.2.0 | Vision: Financial Value Mapping"""
import json, time, requests, os, re

BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss(msg, link=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    if link:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={link}&text=시나리오요청"}]]})
    requests.post(url, data=payload, timeout=10)

def analyze_web_intelligence(art):
    """[핵심] 기술 스펙을 한국 증시 수혜주로 치환하는 하드닝 프롬프트"""
    prompt = f"""[SYSTEM: SENIOR SUPPLY CHAIN ANALYST]
As an expert in the S.Korean stock market, analyze this Global Tech news.
- Nvidia Tech (Pulsar/G-Sync) -> Map to Samsung/Hynix Display Driver & HBM demand.
- BigTech Nuclear -> Map to Korean Power Grid/Nuclear sectors.
Evaluate the 'Alpha' opportunity. Assign 0 only for non-tech/non-financial junk.

Output JSON:
{{
  "title": "한글 제목", "media": "매체",
  "impact": "한국 공급망 및 섹터별 수익성 정밀 분석 (과거사례 대조)",
  "stocks": "관련 핵심 수혜 종목 (삼성전자, 두산에너빌리티 등)",
  "summary": "3줄 요약", "score": 1.0
}}

News: {art['title']} - {art.get('summary', '')}
"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety}, timeout=30)
        raw = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw)
    except: return None

def main():
    send_to_boss("🚀 **능동형 웹 탐색 및 분석 가동**\nCES 2026의 핵심 시그널을 끝까지 추적합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        inspected_list = []

        for art in articles[:20]: # 분석 범위를 넓혀 대어 포착 확률 상승
            res = analyze_web_intelligence(art)
            score = float(res.get('score', 0)) if res else 0
            inspected_list.append(f"• [{score}점] {art['title'][:40]}...")

            if res and score > 2.0:
                report = (f"1️⃣ **뉴스**: {res.get('title')}\n"
                          f"2️⃣ **영향도 ({score}점)**: {res.get('impact')}\n"
                          f"3️⃣ **관련주**: {res.get('stocks')}\n"
                          f"4️⃣ **요약**: {res.get('summary')}")
                send_to_boss(report, art['link'])
                report_count += 1
                time.sleep(15) # 처리 속도 조절

        summary = f"✅ **파이프라인 가동 완료**\n- 검토: {len(articles)}건 / 보고: {report_count}건\n\n"
        summary += "**[실시간 가치 평가 피드]**\n" + "\n".join(inspected_list[:15])
        send_to_boss(summary)

    except Exception as e:
        send_to_boss(f"❌ **내부 오류**: {str(e)}")

if __name__ == "__main__": main()
