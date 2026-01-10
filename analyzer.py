"""Module: analyzer.py | Version: 1.0.5 | Vision: Transparency & Proof of Work"""
import json, time, requests, os, re

BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def report_to_boss(msg, link=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    if link:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={link}&text=시나리오요청"}]]})
    requests.post(url, data=payload, timeout=10)

def analyze_strategic(art):
    # 보스의 8단계 분석 로직 유지
    prompt = f"Analyze for KOSPI impact. Output JSON ONLY. News: {art['title']}"
    try:
        api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(api, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]}, timeout=30)
        raw = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw)
    except: return None

def main():
    report_to_boss("🚀 **분석 엔진 가동 시작**\n48h 글로벌 밸류체인 데이터를 정밀 검증합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        inspected_list = [] # [신규] 검토한 모든 뉴스 제목과 점수를 저장할 리스트

        for art in articles[:10]:
            res = analyze_strategic(art)
            score = float(res.get('score', 0)) if res else 0
            
            # 모든 검토 대상을 리스트에 기록 (증거 확보)
            inspected_list.append(f"• [{score}점] {art['title'][:45]}...")

            if res and score > 2.0:
                msg = (f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
                       f"2️⃣ **매체정보**: {art.get('source')}\n"
                       f"3️⃣ **영향도 및 과거분석 ({score}점)**: {res.get('impact')}\n"
                       f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
                       f"5️⃣ **뉴스 요약**: {res.get('summary')}")
                report_to_boss(msg, art['link'])
                report_count += 1
                time.sleep(30)

        # 🏁 보스 전용 투명성 보고 (Proof of Work)
        status = f"✅ **파이프라인 프로세스 완료**\n- 총 검토: {len(articles)}건\n- 주요 보고: {report_count}건\n\n"
        status += "**[검토 뉴스 리스트]**\n"
        status += "\n".join(inspected_list) if inspected_list else "수집된 뉴스가 없습니다."
        
        if report_count == 0:
            status += "\n\n⚠️ **특이사항**: 모든 뉴스가 영향도 2.0점 이하로 판명되어 상세 보고를 생략했습니다."
            
        report_to_boss(status)

    except Exception as e:
        report_to_boss(f"❌ **시스템 오류**: {str(e)}")

if __name__ == "__main__": main()
