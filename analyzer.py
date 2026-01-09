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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ 텔레그램 전송 실패: {e}")

# ==========================================
# 1. 모델 자동 찾기
# ==========================================
def find_best_model():
    if not GOOGLE_API_KEY:
        print("❌ FATAL: API Key Missing")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return "models/gemini-1.5-flash"

        data = response.json()
        models = data.get('models', [])
        
        # 1.5 Flash를 최우선으로 찾음 (속도/비용 최적)
        for m in models:
            name = m.get('name', '')
            if 'gemini-1.5-flash' in name and 'latest' in name: return name
        for m in models:
            name = m.get('name', '')
            if 'gemini-1.5-flash' in name: return name
        
        # 없으면 Pro 모델 찾음
        for m in models:
            name = m.get('name', '')
            if 'gemini-1.5-pro' in name: return name
        for m in models:
            name = m.get('name', '')
            if 'gemini-pro' in name: return name

        return "models/gemini-1.5-flash"

    except Exception as e:
        print(f"❌ 모델 탐색 에러: {e}")
        return "models/gemini-1.5-flash"

CURRENT_MODEL_NAME = find_best_model()

# ==========================================
# 2. Gemini API 호출 (재시도 로직 포함)
# ==========================================
def call_gemini_raw(prompt):
    if not GOOGLE_API_KEY or not CURRENT_MODEL_NAME:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/{CURRENT_MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    full_prompt = prompt + "\n\nIMPORTANT: Output ONLY valid JSON array. No markdown code blocks."
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json"}
    }

    # 🔥 [핵심] 재시도 로직 (Max 3회)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            # 성공 (200)
            if response.status_code == 200:
                result_json = response.json()
                try:
                    return result_json['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    return None
            
            # 속도 위반 (429) -> 잠시 대기 후 재시도
            elif response.status_code == 429:
                wait_time = 20 * (attempt + 1) # 20초, 40초, 60초 늘려가며 대기
                print(f"⏳ Quota Exceeded (429). Waiting {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue # 다음 루프로 재시도
            
            # 기타 에러 -> 즉시 중단 말고 로그 찍고 종료
            else:
                print(f"❌ API Error {response.status_code}: {response.text[:100]}")
                return None

        except Exception as e:
            print(f"❌ 통신 오류: {e}")
            time.sleep(5)
            continue
            
    print("❌ 모든 재시도 실패.")
    return None

# ==========================================
# 3. 뉴스 분석 루프 (배치 간격 증가)
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Model: {CURRENT_MODEL_NAME})...")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        You are a financial analyst. Analyze these news articles.
        Return a JSON LIST of objects.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Fields Required]:
        - title (Korean summary title)
        - summary (Korean 1 sentence)
        - score (Float 0.0-10.0 impact score)
        - related_stocks (List of strings)
        """

        response_text = call_gemini_raw(prompt)
        
        if response_text:
            try:
                batch_result = json.loads(response_text)
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                elif isinstance(batch_result, dict):
                    if 'articles' in batch_result:
                        results.extend(batch_result['articles'])
                    else:
                        results.append(batch_result)
            except json.JSONDecodeError:
                print("⚠️ JSON 파싱 실패")
        
        # 🔥 [핵심] 배치 사이 휴식 시간 대폭 증가 (Free Tier 보호)
        # 기존 1초 -> 10초로 변경
        print("   Cooling down for 10 seconds...")
        time.sleep(10)

    return results

# ==========================================
# 4. 저장 및 알림
# ==========================================
def save_and_notify(data):
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return

    if len(data) == 0:
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 데이터 0건. (Quota 확인 필요)")
        return

    important_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = important_news[:5]

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
            raw_data = json.load(f)
            articles = raw_data.get('articles', [])
            
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
