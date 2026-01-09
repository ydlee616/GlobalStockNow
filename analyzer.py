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
# 1. 사용 가능한 모델 자동 찾기
# ==========================================
def get_best_model():
    if not GOOGLE_API_KEY: return None, 0
    
    print("🔍 [System] Checking available models...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            models = [m['name'] for m in response.json().get('models', [])]
            
            # 우선순위: 1.5 Flash (빠름) -> 1.5 Pro (성능) -> 1.0 Pro (호환성)
            for m in models:
                if 'gemini-1.5-flash' in m: return m, 5  # 5초 휴식
            for m in models:
                if 'gemini-1.5-pro' in m: return m, 40   # 40초 휴식
            for m in models:
                if 'gemini-pro' in m: return m, 40       # 40초 휴식
                
    except: pass
    
    # 실패 시 안전한 기본값 (gemini-pro + 40초)
    print("⚠️ [System] Model check failed. Using fallback: models/gemini-pro")
    return "models/gemini-pro", 40

SELECTED_MODEL, BATCH_DELAY = get_best_model()

# ==========================================
# 2. Gemini API 호출 (핵심 엔진)
# ==========================================
def call_gemini(prompt):
    if not GOOGLE_API_KEY or not SELECTED_MODEL: return None

    url = f"https://generativelanguage.googleapis.com/v1beta/{SELECTED_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # JSON 포맷 강제 + 안전장치 해제
    full_prompt = prompt + "\n\n[SYSTEM]: Output strictly a valid JSON list. No Markdown."
    
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.3}
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                try:
                    text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    clean_text = re.sub(r'```json|```', '', text).strip()
                    # 유효성 검사
                    json.loads(clean_text)
                    return clean_text
                except:
                    # 블락되었거나 JSON이 깨진 경우
                    return None
            
            elif response.status_code == 429:
                print(f"⏳ Rate Limit (429). Waiting {BATCH_DELAY+10}s...")
                time.sleep(BATCH_DELAY + 10)
                continue
            else:
                print(f"❌ API Error {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(5)
            continue
            
    return None

# ==========================================
# 3. 스마트 분할 분석 (Adaptive Batching)
# ==========================================
def analyze_smartly(articles):
    results = []
    # 기본 배치 사이즈 5
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] Analysis Started (Model: {SELECTED_MODEL})...")
    print(f"   Target: {len(articles)} articles. Strategy: Batch -> Individual Fallback")

    i = 0
    while i < len(articles):
        batch = articles[i : i + batch_size]
        print(f"   Processing Batch {i//batch_size + 1} ({len(batch)} items)...")
        
        prompt = f"""
        Analyze these news articles.
        [Articles]: {json.dumps(batch, ensure_ascii=False)}
        [Requirement]: Return a JSON LIST of objects: title, summary, score, related_stocks.
        """
        
        # 1차 시도: 묶음 처리
        response = call_gemini(prompt)
        success = False
        
        if response:
            try:
                data = json.loads(response)
                if isinstance(data, list) and len(data) > 0:
                    results.extend(data)
                    success = True
                    print(f"   ✅ Batch Success! (+{len(data)} items)")
            except: pass
        
        # 2차 시도: 실패 시 낱개 처리 (Rescue Mode)
        if not success:
            print("   ⚠️ Batch Failed/Blocked. Switching to Rescue Mode (1-by-1)...")
            for article in batch:
                print(f"      Running Rescue for: {article.get('title')[:20]}...")
                single_prompt = f"""
                Analyze this ONE news article.
                [Article]: {json.dumps([article], ensure_ascii=False)}
                [Requirement]: Return a JSON LIST of objects: title, summary, score, related_stocks.
                """
                res = call_gemini(single_prompt)
                if res:
                    try:
                        d = json.loads(res)
                        if isinstance(d, list): results.extend(d)
                        elif isinstance(d, dict): results.append(d)
                        print("      ✅ Rescued!")
                    except: print("      ❌ Failed.")
                
                # 낱개 처리 시에도 짧은 휴식
                time.sleep(5) 

        # 다음 배치로 넘어가기 전 휴식
        print(f"   ☕ Resting {BATCH_DELAY}s...")
        time.sleep(BATCH_DELAY)
        i += batch_size

    return results

# ==========================================
# 4. 저장 및 알림
# ==========================================
def save_and_notify(data):
    # 빈 결과라도 저장 (파일 덮어쓰기 방지)
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Final Count: {len(data)} reports saved.")

    if not TELEGRAM_BOT_TOKEN: return

    if not data:
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 실패. (모든 뉴스가 거부됨)")
        return

    top_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    top_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = top_news[:5]

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(분석 성공: {len(data)}건)\n\n"
    
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
            results = analyze_smartly(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
