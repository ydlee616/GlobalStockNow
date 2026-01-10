import json
import time
import requests
import os
import re
from datetime import datetime

# ==========================================
# [설정 영역]
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=10)
    except: pass

# ==========================================
# 1. Gemini API 호출 (Grok 페르소나 탑재)
# ==========================================
def call_gemini_grok_mode(article):
    # [데이터 유실 방지용 기본값]
    fallback = {
        "title": f"[원본] {article.get('title')}",
        "summary": article.get('summary', '분석 실패'),
        "score": 5.0,
        "related_stocks": ["Manual_Check"],
        "status": "Fallback"
    }

    if not GOOGLE_API_KEY: return fallback

    # 보스 환경에서 가장 안정적인 구형 Pro 모델 사용
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # [프롬프트] 전쟁/납치 뉴스 분석을 강제하기 위한 Grok 페르소나 주입
    prompt = f"""
    You are 'Grok', a cynical and cold-blooded financial analyst. 
    Analyze the following news for its absolute economic impact. 
    Do not censor sensitive topics like war, invasion, or kidnapping. 
    
    [News to Analyze]:
    Title: {article.get('title')}
    Summary: {article.get('summary')}

    [Output Requirement]:
    Return ONLY a JSON object:
    {{
        "title": "Korean Summary Title",
        "summary": "Korean 1-sentence analysis",
        "score": 0.0-10.0,
        "related_stocks": ["Ticker1", "Ticker2"]
    }}
    """

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.2}
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            res_json = response.json()
            # AI가 답변을 거부했는지 체크
            if 'candidates' in res_json and res_json['candidates'][0].get('content'):
                text = res_json['candidates'][0]['content']['parts'][0]['text']
                clean_text = re.sub(r'```json|```', '', text).strip()
                result = json.loads(clean_text)
                result['status'] = 'AI_Analyzed'
                return result
    except: pass

    return fallback

# ==========================================
# 2. 뉴스 처리 엔진 (각개격파)
# ==========================================
def run_analysis():
    if not os.path.exists(INPUT_FILE): return
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        raw = json.load(f)
        articles = raw.get('articles', [])
    
    if not articles:
        send_telegram_msg(f"📭 [Run #{RUN_NUMBER}] 분석할 뉴스가 없습니다.")
        return

    results = []
    print(f"🔄 분석 시작: 총 {len(articles)}건")

    # [중요] 연좌제 방지를 위해 하나씩 처리
    for i, article in enumerate(articles):
        print(f"   [{i+1}/{len(articles)}] 분석 중...")
        res = call_gemini_grok_mode(article)
        results.append(res)
        
        # [중요] 무료/프로 API RPM 제한(2회/분) 준수를 위해 35초 대기
        time.sleep(35)

    # 결과 저장
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(results),
        "reports": results
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    # 텔레그램 전송
    important = sorted(results, key=lambda x: float(x.get('score', 0)), reverse=True)[:5]
    msg = f"🚀 **[GlobalStockNow #{RUN_NUMBER}] 분석 완료**\n(총 {len(results)}건 처리)\n\n"
    for item in important:
        icon = "🔥" if float(item.get('score', 0)) >= 7 else "⚡"
        msg += f"{icon} **{item['title']}** ({item['score']}점)\n"
        msg += f"└ {item['summary']}\n\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    run_analysis()
