import json
import time
import requests
import os
import re  # 정규표현식 모듈 추가
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
# 0. 헬퍼 함수 (텔레그램 & JSON 청소)
# ==========================================
def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=5)
    except: pass

def clean_json_text(text):
    """AI가 마크다운(```json ... ```)을 포함해도 순수 JSON만 추출"""
    if not text: return None
    
    # 1. 마크다운 코드 블록 제거
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # 2. 앞뒤 공백 제거
    text = text.strip()
    
    # 3. 리스트의 시작([)과 끝(])을 찾아 그 사이만 추출 (잡설 제거)
    start = text.find('[')
    end = text.rfind(']')
    
    if start != -1 and end != -1:
        text = text[start:end+1]
    
    return text

# ==========================================
# 1. Gemini API 호출
# ==========================================
def call_gemini_flash(prompt):
    if not GOOGLE_API_KEY: return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # 프롬프트 강화: 한국 주식 시장 관점 주입
    full_prompt = prompt + "\n\nCRITICAL: Analyze based on KOSPI/KOSDAQ impact. Output valid JSON array only."
    
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.3,  # 창의성 낮추고 정확도 높임
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                return clean_json_text(raw_text) # 청소 후 반환
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
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Total: {len(articles)} articles)...")

    # 최신 뉴스 20개만 집중 분석 (속도 및 쿼터 관리)
    target_articles = articles[:20]

    for i in range(0, len(target_articles), batch_size):
        batch = target_articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        Role: Senior Financial Analyst for Korean Stock Market.
        Task: Analyze these news items and predict impact on KOSPI/KOSDAQ stocks.
        Input: {json.dumps(batch, ensure_ascii=False)}
        
        Output JSON List format:
        [
            {{
                "title": "Korean Title (One line, Impactful)",
                "summary": "Korean Summary (Focus on stock market impact)",
                "score": 8.5 (Float 0-10),
                "related_stocks": ["Samsung Electronics", "SK Hynix"]
            }}
        ]
        """

        cleaned_text = call_gemini_flash(prompt)
        
        if cleaned_text:
            try:
                data = json.loads(cleaned_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict) and 'articles' in data: results.extend(data['articles'])
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON Parsing Failed: {e}")
                # 디버깅을 위해 실패한 텍스트 일부 출력
                print(f"   Raw text fragment: {cleaned_text[:100]}...")
        
        time.sleep(3) # Flash 모델 쿨다운

    return results

# ==========================================
# 3. 저장 및 알림
# ==========================================
def save_and_notify(data):
    # 날짜별 폴더링 없이 루트에 저장 (덮어쓰기)
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! {len(data)}건 저장.")

    if not TELEGRAM_BOT_TOKEN: return

    # 점수 필터링 (높은 점수순)
    important_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = important_news[:5] # 상위 5개만 전송

    if not top_news:
        send_telegram_msg(f"📉 [GlobalStockNow #{RUN_NUMBER}] 분석 완료: 특이사항 없음 (기준 점수 미달)")
        return

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n\n"
    for item in top_news:
        score = item.get('score', 0)
        icon = "🚨" if score >= 8.0 else "🔥" if score >= 6.0 else "⚡"
        
        msg += f"{icon} **{item.get('title')}** ({score}점)\n"
        msg += f"└ {item.get('summary')}\n"
        msg += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
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
