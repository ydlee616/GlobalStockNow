import json
import time
import requests
import os
import sys
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

# ==========================================
# 0. 텔레그램 전송 헬퍼
# ==========================================
def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=5)
    except: pass

# ==========================================
# 1. Flash 모델 강제 찾기 (속도 위반 방지)
# ==========================================
def find_flash_model():
    if not GOOGLE_API_KEY: return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return "models/gemini-1.5-flash"

        data = response.json()
        models = data.get('models', [])
        
        # 🔥 무조건 Flash 모델만 찾습니다 (Pro 금지)
        for m in models:
            name = m.get('name', '')
            if 'gemini-1.5-flash' in name:
                print(f"✅ Safe Model Selected: {name}")
                return name
        
        return "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

CURRENT_MODEL_NAME = find_flash_model()

# ==========================================
# 2. Gemini API 호출 (안전 운전 모드)
# ==========================================
def call_gemini_safe(prompt):
    if not GOOGLE_API_KEY: return None

    url = f"https://generativelanguage.googleapis.com/v1beta/{CURRENT_MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # JSON 모드 강제
    full_prompt = prompt + "\n\nOutput strictly valid JSON array."
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json"}
    }

    # 재시도 로직 (Max 5회)
    for attempt in range(5):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            
            elif response.status_code == 429:
                # 🚨 속도 위반 시 60초 대기 (패널티 박스)
                print(f"⏳ 429 Quota Error. Cooling down for 60s... (Attempt {attempt+1})")
                time.sleep(60)
                continue
            
            else:
                print(f"❌ Error {response.status_code}: {response.text[:100]}")
                time.sleep(5)
                continue

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(10)
            continue
            
    return None

# ==========================================
# 3. 뉴스 분석 (소량 배치 + 긴 휴식)
# ==========================================
def analyze_news_batch(articles):
    results = []
    # 🔥 배치 사이즈를 3개로 축소 (한 입 크기 줄임)
    batch_size = 3
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Safe Mode: {CURRENT_MODEL_NAME})...")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}/{len(articles)//batch_size + 1}...")
        
        prompt = f"""
        Analyze these news. Return JSON list.
        fields: title(Korean), summary(Korean), score(float), related_stocks(list).
        
        Data: {json.dumps(batch, ensure_ascii=False)}
        """

        response_text = call_gemini_safe(prompt)
        
        if response_text:
            try:
                data = json.loads(response_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict): 
                    results.extend(data.get('articles', [data]))
            except: pass
        
        # 🔥 배치 하나 끝날 때마다 15초 강제 휴식 (RPM 조절)
        print("   ☕ Resting 15s...")
        time.sleep(15)

    return results

# ==========================================
# 4. 저장 및 전송
# ==========================================
def save_and_notify(data):
    # 결과 저장
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"reports": data}, f, ensure_ascii=False, indent=4)
    
    if not TELEGRAM_BOT_TOKEN: return

    # 분석 데이터 0건이면 알림
    if not data:
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 데이터 없음 (여전히 Quota 제한 중일 수 있음)")
        return

    # 중요 뉴스 필터링
    top_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    top_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = top_news[:5]

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(모델: {CURRENT_MODEL_NAME})\n\n"
    
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
            data = json.load(f)
            # 최대 15개까지만 분석 (안전하게 자름)
            articles = data.get('articles', [])[:15]
            
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
    else:
        print(f"❌ 파일 없음")
