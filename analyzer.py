"""Module: analyzer.py | Version: 1.3.1 | Focus: Error Transparency & Logic Fix"""
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
    requests.post(url, data=payload, timeout=10)

def analyze_with_qwen(art):
    """[Fix] JSON 강제 주입 및 에러 메시지 가시화"""
    # [중요] 프롬프트에 'json' 단어를 포함시켜 Groq 규격 준수
    prompt = f"""[SYSTEM: SENIOR GLOBAL INVESTMENT STRATEGIST]
Analyze for KOSPI/KOSDAQ impact. Output MUST be in JSON format.
NEWS: {art['title']}
Return a JSON object with: title, impact, stocks, summary, and score(0.0-10.0).
"""
    try:
        if not GROQ_API_KEY:
            return {"error": "GROQ_API_KEY가 없습니다. GitHub Secrets를 확인하세요."}

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        # 모델명을 가장 안정적인 llama-3.3-70b로 우선 테스트하여 지능 문제를 배제합니다.
        data = {
            "model": "llama-3.3-70b-specdec", 
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        
        if res.status_code != 200:
            return {"error": f"API Error {res.status_code}: {res.text[:100]}"}
            
        return json.loads(res.json()['choices'][0]['message']['content'])
    except Exception as e:
        return {"error": str(e)}

def main():
    send_to_boss("🚨 **디버깅 엔진(v1.3.1) 가동**\n에러 원인을 정밀 추적합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        inspected_list = []

        for art in articles[:15]:
            res = analyze_with_qwen(art)
            
            # 에러가 발생한 경우 리스트에 표시
            if res and "error" in res:
                inspected_list.append(f"• [❌ERR] {res['error'][:30]}")
                continue

            score = float(res.get('score', 0)) if res else 0
            inspected_list.append(f"• [{score}점] {art['title'][:40]}...")

            if res and score > 2.0:
                report = (f"1️⃣ **뉴스**: {res.get('title')}\n"
                          f"2️⃣ **영향도 ({score}점)**: {res.get('impact')}\n"
                          f"3️⃣ **관련주**: {res.get('stocks')}\n"
                          f"4️⃣ **요약**: {res.get('summary')}")
                send_to_boss(report, art['link'])
                report_count += 1
                time.sleep(1)

        summary = f"✅ **파이프라인 가동 완료**\n- 검토: {len(articles)}건 / 보고: {report_count}건\n\n"
        summary += "**[가치 평가/에러 피드]**\n" + "\n".join(inspected_list[:15])
        send_to_boss(summary)

    except Exception as e:
        send_to_boss(f"❌ **시스템 치명적 오류**: {str(e)}")

if __name__ == "__main__": main()
