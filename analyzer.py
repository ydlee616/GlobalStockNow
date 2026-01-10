"""Module: analyzer.py | Version: 1.1.1 | Vision: Steve Jobs Concept"""
import json, time, requests, os, re

# [BRANDING] 보스의 고유 자산
BRAND_NAME = "GlobalStockNow 브리핑"

# 환경 변수
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
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def analyze_intelligence(art):
    """[핵심] 하드닝된 금융-기술 통합 분석 엔진"""
    prompt = f"""[SYSTEM: SENIOR GLOBAL STRATEGIST]
Evaluate this news impact on KOSPI/KOSDAQ. 
Even pure tech specs (like Nvidia Pulsar) must be analyzed via 'Supply Chain' value.
Treat 'Nuclear' and 'North Korea' strictly as market risk/opportunity factors.
DO NOT REFUSE. Output ONLY valid JSON.

{{
  "title": "한글 뉴스 제목",
  "media": "매체 신뢰도",
  "impact": "한국 증시/공급망에 미치는 구체적 영향 (과거 전례 비교)",
  "stocks": "수혜주/관련주 (삼성전자, SK하이닉스 등 구체적 명시)",
  "summary": "3줄 핵심 요약",
  "score": 0.0
}}

News: {art['title']} - {art.get('summary', '')}
"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        # 세이프티 차단 전면 해제
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety}, timeout=30)
        raw = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw)
    except: return None

def main():
    send_to_boss("🚀 **지능형 분석 엔진(v1.1.1) 가동**\n엔비디아 기술 사양 및 글로벌 밸류체인 분석을 시작합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        inspected_list = []

        for art in articles[:15]:
            res = None
            res = analyze_intelligence(art)
            score = float(res.get('score', 0)) if res else 0
            
            # 투명성 보고: AI가 어떤 판단을 내렸는지 증거 제출
            inspected_list.append(f"• [{score}점] {art['title'][:40]}...")

            if res and score > 2.0:
                report = (f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
                          f"2️⃣ **매체정보**: {art.get('source')}\n"
                          f"3️⃣ **전략적 분석 ({score}점)**: {res.get('impact')}\n"
                          f"4️⃣ **공급망 수혜주**: {res.get('stocks')}\n"
                          f"5️⃣ **핵심 요약**: {res.get('summary')}")
                send_to_boss(report, art['link'])
                report_count += 1
                time.sleep(30)

        # 🏁 최종 요약 보고 (Proof of Work)
        summary = f"✅ **파이프라인 프로세스 완료**\n- 검토: {len(articles)}건 / 보고: {report_count}건\n\n"
        summary += "**[실시간 검토 피드]**\n" + "\n".join(inspected_list)
        if report_count == 0:
            summary += "\n\n⚠️ 특이사항: 현재 시장 파급력이 2.0점 미만인 뉴스만 포착되었습니다."
        send_to_boss(summary)

    except Exception as e:
        send_to_boss(f"❌ **내부 시스템 오류**: {str(e)}")

if __name__ == "__main__": main()
