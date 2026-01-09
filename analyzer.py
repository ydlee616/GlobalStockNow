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
# 1. 사용 가능한 모델 및 속도 자동 감지 (핵심)
# ==========================================
def get_optimal_model_and_delay():
    if not GOOGLE_API_KEY: return None, 0

    print("🔍 Checking available AI models for your API Key...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            
            # 1순위: Gemini 1.5 Flash (빠름, 5초 휴식)
            for m in models:
                if 'gemini-1.5-flash' in m:
                    print(f"✅ Found Fast Model: {m}")
                    return m, 5
            
            # 2순위: Gemini 1.5 Pro (느림, 35초 휴식)
            for m in models:
                if 'gemini-1.5-pro' in m:
                    print(f"✅ Found High-Performance Model: {m}")
                    return m, 35
            
            # 3순위: Gemini Pro Legacy (느림, 35초 휴식)
            for m in models:
                if 'gemini-pro' in m:
                    print(f"✅ Found Legacy Model: {m}")
                    return m, 35
                    
        print("⚠️ Model list check failed. Fallback to 'gemini-pro'.")
    except Exception as e:
        print(f"⚠️ Connection error during model check: {e}")

    # 안전하게 기본값은 Pro + 35초 (404 방지보다는 429 방지가 나음)
    return "models/gemini-pro", 35

# 모델과 딜레이 확정
SELECTED_MODEL, BATCH_DELAY = get_optimal_model_and_delay()

# ==========================================
# 2. Gemini API 호출
# ==========================================
def call_gemini(prompt):
    if not GOOGLE_API_KEY or not SELECTED_MODEL: return None

    url = f"https://generativelanguage.googleapis.com/v1beta/{SELECTED_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # JSON 강제 출력 프롬프트
    full_prompt = prompt + "\n\n[SYSTEM]: Output strictly a valid JSON list. No Markdown, no explanation."

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        # 안전장치 해제 (뉴스 분석 거부 방지)
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.3}
    }

    # 재시도 로직
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                text = response.json()['candidates'][0]['content']['parts'][0]['text']
                # 마크다운 코드블록 제거
                clean_text = re.sub(r'```json|```', '', text).strip()
                return clean_text
            
            elif response.status_code == 429:
                print(f"⏳ Quota Exceeded (429). Cooling down {BATCH_DELAY + 10}s... ({attempt+1}/3)")
                time.sleep(BATCH_DELAY + 10) # 지정된 딜레이보다 조금 더 쉼
                continue
            
            elif response.status_code == 404:
                print(f"❌ Critical Error: Model {SELECTED_MODEL} not found (404).")
                return None
            
            else:
                print(f"❌ API Error {response.status_code}: {response.text[:100]}")
                time.sleep(5)
                continue

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(5)
            continue
            
    return None

# ==========================================
# 3. 뉴스 분석 (배치 처리)
# ==========================================
def analyze_news_batch(articles):
    results = []
    # 한 번에 4개씩 처리
    batch_size = 4
    
    print(f"🔄 [Run #{RUN_NUMBER}] Analysis Started using {SELECTED_MODEL} (Delay: {BATCH_DELAY}s)...")

    # 최대 34개 뉴스 처리
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}/{len(articles)//batch_size + 1}...")
        
        prompt = f"""
        Analyze the following financial news articles.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirement]:
        Return a JSON LIST of objects with these exact keys:
        - title (Korean summary)
        - summary (Korean 1 sentence)
        - score (Float 0.0-10.0 impact score)
        - related_stocks (List of strings)
        """

        response_text = call_gemini(prompt)
        
        if response_text:
            try:
                data = json.loads(response_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict): 
                    if 'articles' in data: results.extend(data['articles'])
                    else: results.append(data)
            except: 
                print("⚠️ JSON Parsing Failed for this batch.")
        
        # 🔥 동적으로 설정된 딜레이만큼 휴식
        print(f"   ☕ Resting {BATCH_DELAY}s...")
        time.sleep(BATCH_DELAY)

    return results

# ==========================================
# 4. 저장 및 알림
# ==========================================
def save_and_notify(data):
    # 결과 저장
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Analysis Complete! Total {len(data)} reports saved.")

    if not TELEGRAM_BOT_TOKEN: return

    if not data:
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 실패: 결과 데이터 없음 ({SELECTED_MODEL})")
        return

    # 중요 뉴스 필터링
    top_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    top_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = top_news[:5] # 상위 5개만 전송

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(모델: {SELECTED_MODEL})\n\n"
    
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
            # JSON 구조 호환성 처리
            if isinstance(raw_data, list): articles = raw_data
            else: articles = raw_data.get('articles', [])
            
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 No news data found.")
            # 데이터가 없을 때는 조용히 종료 (이전 단계에서 수집 실패 알림이 갔을 것임)
    else:
        print(f"❌ Input file {INPUT_FILE} not found.")
