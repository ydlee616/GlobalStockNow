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
# 1. Gemini API 호출 (무조건 응답 받기)
# ==========================================
def analyze_article_robust(article):
    if not GOOGLE_API_KEY: return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # [프롬프트] JSON을 요청하되, 실패해도 괜찮음
    prompt = f"""
    Analyze this news for stock market impact.
    [News]: {article.get('title')}
    
    [Output Format]:
    JSON format with keys: title, summary, score, related_stocks.
    If you cannot output JSON, just write the summary and score in plain text.
    """

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.1}
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            text = response.json()['candidates'][0]['content']['parts'][0]['text']
            
            # 1. JSON 파싱 시도
            try:
                clean_text = re.sub(r'```json|```', '', text).strip()
                return json.loads(clean_text)
            except:
                # 2. JSON 실패 시 -> 강제로 텍스트를 담아서 반환 (Raw Fallback)
                # 이 부분이 추가되어 데이터 유실을 막습니다.
                print(f"⚠️ JSON 파싱 실패 -> 텍스트 원본 저장: {article.get('title')[:10]}...")
                return {
                    "title": article.get('title'),
                    "summary": f"[형식오류 원본] {text[:200]}...", # 원본 내용 저장
                    "score": 5.0, # 기본값
                    "related_stocks": ["CHECK_RAW"]
                }
        elif response.status_code == 429:
            print("⏳ 429 Quota. Sleeping 30s...")
            time.sleep(30)
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

# ==========================================
# 2. 전체 뉴스 분석
# ==========================================
def analyze_all_news(articles):
    results = []
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (총 {len(articles)}건)...")
    
    for i, article in enumerate(articles):
        # API 제한 고려 (1분 2회) -> 32초 휴식
        res = analyze_article_robust(article)
        if res:
            results.append(res)
            print(f"   ✅ [{i+1}] Success")
        else:
            print(f"   ❌ [{i+1}] Failed")
            
        time.sleep(32) # 안전 휴식

    return results

# ==========================================
# 3. 저장 및 알림
# ==========================================
def save_and_notify(data):
    # 빈 파일 방지용
    if not data: data = []
        
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 저장 완료: {len(data)}건")

    if not TELEGRAM_BOT_TOKEN: return

    # 분석 결과가 없어도 수집된 뉴스가 0건이었는지 구분해서 알림
    if len(data) == 0:
        # 파일이 비어있는지 체크 (입력 데이터 문제)
        if os.path.exists(INPUT_FILE):
            with open(INPUT_FILE, 'r') as f:
                input_cnt = len(json.load(f).get('articles', []))
            if input_cnt == 0:
                send_telegram_msg(f"📭 [GlobalStockNow #{RUN_NUMBER}] 수집된 새 뉴스가 없습니다. (정상)")
                return

        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 실패 (입력은 있었으나 결과 0건)")
        return

    # 결과 전송
    msg = f"🚀 **[GlobalStockNow 결과 (#{RUN_NUMBER})]**\n(성공: {len(data)}건)\n\n"
    for item in data[:5]:
        msg += f"🔥 {item.get('title')}\n"
        msg += f"└ {item.get('summary')}\n\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            articles = raw_data.get('articles', []) if isinstance(raw_data, dict) else raw_data
            
        if articles:
            # 테스트를 위해 5개만 우선 실행 (시간 절약)
            # 34개 다 하려면 시간이 너무 걸려 테스트가 힘듭니다.
            # 성공하면 나중에 제한을 푸세요.
            results = analyze_all_news(articles[:5])
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
            # 입력 파일이 비어있으면 텔레그램으로 알려줌
            save_and_notify([]) 
    else:
        print(f"❌ 파일 없음")
