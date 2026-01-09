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
# 1. 사용 가능한 모델 자동 찾기 (404 방지)
# ==========================================
def find_working_model():
    if not GOOGLE_API_KEY: return None

    print("🔍 Searching for available models...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ 모델 목록 조회 실패: {response.status_code}")
            return "models/gemini-pro" # 비상시 기본값

        data = response.json()
        models = data.get('models', [])
        
        # 우선순위 1: Flash (빠름)
        for m in models:
            if 'gemini-1.5-flash' in m['name']:
                print(f"✅ Selected Flash Model: {m['name']}")
                return (m['name'], 5) # (모델명, 휴식시간 5초)
        
        # 우선순위 2: Pro (느리지만 성능 좋음)
        for m in models:
            if 'gemini-1.5-pro' in m['name']:
                print(f"✅ Selected Pro Model: {m['name']}")
                return (m['name'], 35) # (모델명, 휴식시간 35초 - 429 방지)
        
        # 우선순위 3: 구형 Pro
        for m in models:
            if 'gemini-pro' in m['name']:
                print(f"✅ Selected Standard Model: {m['name']}")
                return (m['name'], 35)

        # 못 찾으면 기본값
        return ("models/gemini-1.5-flash", 5)

    except Exception as e:
        print(f"❌ 모델 탐색 중 에러: {e}")
        return ("models/gemini-1.5-flash", 5)

# 전역 변수로 모델과 휴식 시간 확정
SELECTED_MODEL_NAME, SLEEP_TIME = find_working_model()

# ==========================================
# 2. Gemini API 호출 (Raw String 방식)
# ==========================================
def call_gemini_dynamic(prompt):
    if not GOOGLE_API_KEY: return None

    # 확정된 모델 이름 사용
    url = f"https://generativelanguage.googleapis.com/v1beta/{SELECTED_MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    full_prompt = prompt + "\n\n[SYSTEM]: Output strictly a valid JSON list. No Markdown."

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.4}
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                text = response.json()['candidates'][0]['content']['parts'][0]['text']
                # 마크다운 제거
                clean_text = re.sub(r'```json|```', '', text).strip()
                return clean_text
            
            elif response.status_code == 404:
                print(f"❌ 404 Error: 모델을 찾을 수 없음 ({SELECTED_MODEL_NAME})")
                return None

            elif response.status_code == 429:
                print(f"⏳ 429 Quota Limit. 대기 중... ({attempt+1}/3)")
                time.sleep(SLEEP_TIME + 10) # 지정된 시간보다 10초 더 대기
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
# 3. 뉴스 분석 (가변 속도 적용)
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5 
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Model: {SELECTED_MODEL_NAME})...")
    
    # 35개 전부 분석 시도
    target_articles = articles[:35]

    for i in range(0, len(target_articles), batch_size):
        batch = target_articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        Analyze these news items for stock market impact.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirements]:
        Return a JSON LIST of objects:
        - title (Korean)
        - summary (Korean)
        - score (Float 0-10)
        - related_stocks (List)
        """

        response_text = call_gemini_dynamic(prompt)
        
        if response_text:
            try:
                data = json.loads(response_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict): 
                    if 'articles' in data: results.extend(data['articles'])
                    else: results.append(data)
            except: 
                print("⚠️ JSON Parsing Failed")
        
        # 🔥 모델에 따라 계산된 휴식 시간 적용
        print(f"   ☕ Cooling down {SLEEP_TIME}s...")
        time.sleep(SLEEP_TIME)

    return results

# ==========================================
# 4. 저장 및 알림
# ==========================================
def save_and_notify(data):
    output_data = {"analyzed_at": str(datetime.now()), "run_number": RUN_NUMBER, "reports": data}
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")

    if not TELEGRAM_BOT_TOKEN: return

    if not data:
        # 실패 시 로그 전송
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 실패: {SELECTED_MODEL_NAME} 응답 없음")
        return

    top_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    top_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = top_news[:5]

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(모델: {SELECTED_MODEL_NAME})\n\n"
    
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
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
            # 데이터가 없을 때는 조용히 종료하거나 로그만 남김
            # send_telegram_msg(f"📭 [GlobalStockNow #{RUN_NUMBER}] 수집된 뉴스 없음") 
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
