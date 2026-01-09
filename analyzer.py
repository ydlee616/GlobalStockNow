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

IMPACT_THRESHOLD = 2.0
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=5)
    except: pass

# ==========================================
# 1. Gemini API 호출 (Pro 모델 + 35초 딜레이)
# ==========================================
def call_gemini_safe_mode(prompt):
    if not GOOGLE_API_KEY: return None

    # 🔥 [핵심 1] 1.5-flash(404오류) 대신, 확실한 'gemini-pro' 사용
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    full_prompt = prompt + "\n\n[SYSTEM]: Output strictly a valid JSON list. No Markdown."

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        # 🔥 [핵심 2] 뉴스 분석 거부 방지 (안전장치 해제)
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.4}
    }

    # 재시도 로직
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                text = response.json()['candidates'][0]['content']['parts'][0]['text']
                # 마크다운 제거 후 반환
                return re.sub(r'```json|```', '', text).strip()
            
            elif response.status_code == 429:
                # 429(속도제한) 발생 시 40초 대기
                print(f"⏳ 과속 감지(429). 40초 대기... ({attempt+1}/3)")
                time.sleep(40)
                continue
            
            else:
                print(f"❌ API Error {response.status_code}: {response.text[:100]}")
                return None

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(5)
            continue
            
    return None

# ==========================================
# 2. 뉴스 분석 (배치 처리)
# ==========================================
def analyze_news_batch(articles):
    results = []
    # 한 번에 4개씩 처리
    batch_size = 4
    
    # 35개 뉴스 -> 약 9번 요청
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Model: gemini-pro / Mode: Slow)...")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        You are a financial analyst. Analyze these news items.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirements]:
        Return a JSON LIST of objects:
        - title (Korean)
        - summary (Korean)
        - score (Float 0-10)
        - related_stocks (List)
        """

        response_text = call_gemini_safe_mode(prompt)
        
        if response_text:
            try:
                data = json.loads(response_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict): 
                    if 'articles' in data: results.extend(data['articles'])
                    else: results.append(data)
            except: 
                print("⚠️ JSON Parsing Failed (Skipping batch)")
        
        # 🔥 [핵심 3] 무료 등급 한계 극복을 위한 강제 휴식 (35초)
        # 답답하시더라도 이 시간을 지켜야 429 에러가 안 납니다.
        print("   ☕ Cooling down 35s...")
        time.sleep(35)

    return results

# ==========================================
# 3. 저장 및 알림
# ==========================================
def save_and_notify(data):
    output_data = {"analyzed_at": str(datetime.now()), "run_number": RUN_NUMBER, "reports": data}
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")

    if not TELEGRAM_BOT_TOKEN: return

    if not data:
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 실패: 결과 없음")
        return

    top_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    top_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = top_news[:5]

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(안전모드 분석완료)\n\n"
    
    if not top_news:
        msg += "특이사항 없음 (중요 뉴스 없음)"
    else:
        for item in top_news:
            score = item.get('score', 0)
            icon = "🔥" if score >= 7.0 else "⚡"
            msg += f"{icon} **{item.get('title')}** ({score}점)\n"
            msg += f"└ {item.get('summary')}\n"
            msg += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            if isinstance(raw_data, list): articles = raw_data
            else: articles = raw_data.get('articles', [])
            
        if articles:
            # 최대 35개 모두 분석 시도
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
