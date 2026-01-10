"""Module: analyzer.py | Version: 1.3.3 | Focus: Solving API Error 400"""
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

def analyze_with_groq(art):
    """[Fix] Groq API의 까다로운 JSON 모드 조건을 완벽 충족"""
    # [중요] 'json' 단어를 명시적으로 포함하여 400 에러를 원천 봉쇄합니다.
    prompt = f"""Analyze the stock market impact of this news and return the result strictly in JSON format.
NEWS: {art['title']}
Field requirements: title, impact, stocks, summary, score(0-10)."""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        # [Update] 가장 성공률이 높은 범용 모델 ID로 교체
        data = {
            "model": "llama-3.3-70b-versatile", 
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        
        if res.status_code != 200:
            return {"error": f"API {res.status_code}"}
            
        return json.loads(res.json()['choices'][0]['message']['content'])
    except Exception as e:
        return {"error": "Parsing Error"}

def main():
    send_to_boss("🚀 **무결점 통신 엔진(v1.3.3) 가동**\n에러 400을 격파하고 진짜 수익 정보를 가져옵니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        inspected_list = []

        for art in articles[:15]:
            res = analyze_with_groq(art)
            
            if res and "error" in res:
                inspected_list.append(f"• [⚠] {res['error']} | {art['title'][:20]}...")
                continue

            score = float(res.get('score', 0)) if res else 0
            inspected_list.append(f"• [{score}점] {art['title'][:40]}...")

            if res and score > 2.0:
                report = (f"1️⃣ **뉴스**: {res.get('title')}\n"
                          f"2️⃣ **전략분석 ({score}점)**: {res.get('impact')}\n"
                          f"3️⃣ **관련주**: {res.get('stocks')}\n"
                          f"4️⃣ **요약**: {res.get('summary')}")
                send_to_boss(report, art['link'])
                report_count += 1
                time.sleep(1)

        summary = f"✅ **파이프라인 가동 완료**\n- 검토: {len(articles)}건 / 보고: {report_count}건\n\n"
        summary += "**[실시간 가치 평가 피드]**\n" + "\n".join(inspected_list[:15])
        send_to_boss(summary)

    except Exception as e:
        send_to_boss(f"❌ **시스템 오류**: {str(e)}")

if __name__ == "__main__": main()
