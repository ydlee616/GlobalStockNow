import json
import time
import requests
import os
import re  # 정규표현식 모듈 (필수)
from datetime import datetime

# ==========================================
# [설정 영역]
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

# 영향도 기준 (2.0점 이상이면 전송)
IMPACT_THRESHOLD = 2.0
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

# ==========================================
# 0. 헬퍼 함수
# ==========================================
def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=5)
    except: pass

def clean_json_text(text):
    """
    AI가 마크다운(```json ... ```)이나 잡설을 포함해도 
    순수 JSON 리스트([...])만 강력하게 추출하는 함수
    """
    if not text: return None
    
    # 1. 마크다운 코드 블록 제거 (```json, ```)
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # 2. 리스트의 시작([)과 끝(])을 찾아 그 사이만 추출
    # (AI가 앞뒤로 "Here is the JSON:" 같은 말을 붙여도 무시함)
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        return match.group(0)
    
    return text.strip()

# ==========================================
# 1. Gemini API 호출
# ==========================================
def call_gemini_flash(prompt):
    if not GOOGLE_API_KEY: return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # 프롬프트: JSON 포맷 강제
    full_prompt = prompt + "\n\nCRITICAL: Return ONLY a valid JSON array. No Markdown. No explanations."
    
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,  # 창의성 낮춤 (포맷 준수율 높임)
            "responseMimeType": "application/json"
        }
    }

    # 재시도 로직
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                # 🔥 여기서 클리닝 함수 호출
                return clean_json_text(raw_text)
            elif response.status_code == 429:
                print(f"⏳ Quota Limit. 10s wait... ({attempt+1}/3)")
                time.sleep(10)
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
# 2. 뉴스 분석 실행
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5 # 배치 사이즈
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Total: {len(articles)} articles)...")

    # 최신 뉴스 25개만 집중 분석
    target_articles = articles[:25]

    for i in range(0, len(target_articles), batch_size):
        batch = target_articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        Role: Senior Financial Analyst for Korean Stock Market (KOSPI/KOSDAQ).
        Task: Analyze these global news items and predict impact on Korean stocks.
        
        Input News:
        {json.dumps(batch, ensure_ascii=False)}
        
        Requirements:
        1. Identify related Korean stocks (e.g., Samsung Electronics, SK Hynix, LG Energy Solution).
        2. Assign an 'impact score' (0.0 - 10.0). High score for earnings surprises or direct supply chain news.
        3. Write a sharp, 1-sentence summary in Korean.
        
        Output JSON Format:
        [
            {{
                "title": "Korean Title",
                "summary": "Korean Summary",
                "score": 9.5,
                "related_stocks": ["StockName1", "StockName2"]
            }}
        ]
        """

        cleaned_text = call_gemini_flash(prompt)
        
        if cleaned_text:
            try:
                data = json.loads(cleaned_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict) and 'articles' in data: results.extend(data['articles'])
                print(f"      ✅ Batch {i//batch_size + 1} success: {len(data)} items analyzed.")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON Parsing Failed in batch {i}: {e}")
                # 디버깅용: 실패한 텍스트 일부 출력
                print(f"   [Debug] Failed Text Start: {cleaned_text[:50]}...")
        else:
            print("   ⚠️ No response from AI")
        
        time.sleep(4) # Flash 모델 쿨다운

    return results

# ==========================================
# 3. 저장 및 알림
# ==========================================
def save_and_notify(data):
    # 파일 저장
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장.")

    if not TELEGRAM_BOT_TOKEN: return

    # 점수 필터링 및 정렬
    important_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = important_news[:7] # 상위 7개 전송

    if not top_news:
        send_telegram_msg(f"📉 [GlobalStockNow #{RUN_NUMBER}] 분석 완료: 중요 뉴스 없음 (기준 {IMPACT_THRESHOLD}점 미달)")
        return

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n\n"
    for item in top_news:
        score = item.get('score', 0)
        # 아이콘 설정
        if score >= 8.5: icon = "🚨(강력매수)"
        elif score >= 7.0: icon = "🔥(호재)"
        else: icon = "⚡(관심)"
        
        msg += f"{icon} **{item.get('title')}** ({score}점)\n"
        msg += f"└ {item.get('summary')}\n"
        msg += f"└ 관련주: `{', '.join(item.get('related_stocks', []))}`\n\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            try:
                raw_data = json.load(f)
                articles = raw_data.get('articles', [])
            except:
                articles = []
        
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
            send_telegram_msg(f"⚠️ [GlobalStockNow #{RUN_NUMBER}] 수집된 뉴스가 0건입니다.")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
