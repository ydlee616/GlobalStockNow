"""Module: analyzer.py | Version: 1.0.7 | Vision: Steve Jobs Style"""
import json, time, requests, os, re

# [BRANDING] 절대 불변의 명칭
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
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={link}&text=유튜브시나리오"}]]})
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def analyze_core(art):
    prompt = f"Analyze for KOSPI impact. Output JSON ONLY. News: {art['title']}"
    try:
        api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(api, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]}, timeout=30)
        raw = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw)
    except: return None

def main():
    send_to_boss("🚀 **분석 엔진 가동 시작**\n48h 글로벌 데이터를 정밀 검증합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        inspected_list = []

        for art in articles[:12]:
            res = None # [Fix] NameError 방지
            res = analyze_core(art)
            score = float(res.get('score', 0)) if res else 0
            
            # 투명성 보고를 위한 리스트업
            inspected_list.append(f"• [{score}점] {art['title'][:40]}...")

            if res and score > 2.0:
                report = (f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
                          f"2️⃣ **매체정보**: {art.get('source')}\n"
                          f"3️⃣ **영향도 ({score}점)**: {res.get('impact')}\n"
                          f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
                          f"5️⃣ **뉴스 요약**: {res.get('summary')}")
                send_to_boss(report, art['link'])
                report_count += 1
                time.sleep(30)

        # 🏁 보스 전용 투명성 보고서 발송
        summary = f"✅ **파이프라인 프로세스 완료**\n- 검토: {len(articles)}건 / 보고: {report_count}건\n\n"
        summary += "**[검토 뉴스 리스트]**\n" + "\n".join(inspected_list)
        if report_count == 0:
            summary += "\n\n⚠️ 특이사항: 고영향도(2.0점 초과) 속보가 발견되지 않았습니다."
        send_to_boss(summary)

    except Exception as e:
        send_to_boss(f"❌ **내부 오류**: {str(e)}")

if __name__ == "__main__": main()
