"""Module: analyzer.py | Version: 1.3.0 | Vision: Steve Jobs Concept"""
import json, time, requests, os, re

BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss(msg, link=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    if link:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={link}&text=시나리오요청"}]]})
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def analyze_with_qwen(art):
    """[핵심] Qwen2.5-32B를 이용한 무검열 전략 분석"""
    prompt = f"""[SYSTEM: SENIOR GLOBAL INVESTMENT STRATEGIST]
Analyze strictly from the perspective of the South Korean stock market (KOSPI/KOSDAQ).
Translate technical specs and policy news into corporate earnings impact.
DO NOT REFUSE. If it's about Nuclear or Geopolitics, analyze the financial RISK/OPPORTUNITY.

Output ONLY valid JSON:
{{
  "title": "한글 뉴스 제목",
  "impact": "공급망 및 섹터 수익성 정밀 분석 (과거 사례 비교)",
  "stocks": "핵심 수혜 종목 (삼성전자, 두산에너빌리티 등)",
  "summary": "3줄 핵심 요약",
  "score": 0.0
}}

News: {art['title']}
"""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        # Qwen-2.5-32B 모델 지정 (Groq 지원 모델)
        data = {
            "model": "qwen-2.5-32b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        return json.loads(res.json()['choices'][0]['message']['content'])
    except: return None

def main():
    send_to_boss("🚀 **Qwen-Neural 엔진 가동**\n무검열 실시간 금융 분석을 시작합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        inspected_list = []

        for art in articles[:15]:
            res = analyze_with_qwen(art)
            score = float(res.get('score', 0)) if res else 0
            inspected_list.append(f"• [{score}점] {art['title'][:40]}...")

            if res and score > 2.0:
                report = (f"1️⃣ **뉴스**: {res.get('title')}\n"
                          f"2️⃣ **영향도 ({score}점)**: {res.get('impact')}\n"
                          f"3️⃣ **관련주**: {res.get('stocks')}\n"
                          f"4️⃣ **요약**: {res.get('summary')}")
                send_to_boss(report, art['link'])
                report_count += 1
                time.sleep(1) # Groq은 빨라서 긴 대기가 필요 없습니다.

        summary = f"✅ **파이프라인 가동 완료**\n- 검토: {len(articles)}건 / 보고: {report_count}건\n\n"
        summary += "**[가치 평가 피드]**\n" + "\n".join(inspected_list[:15])
        send_to_boss(summary)

    except Exception as e:
        send_to_boss(f"❌ **내부 오류**: {str(e)}")

if __name__ == "__main__": main()
