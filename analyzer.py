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

# 영향도 기준 (2.0점 이상이면 전송)
IMPACT_THRESHOLD = 2.0
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

# ==========================================
# 0. 텔레그램 전송 헬퍼 함수
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
# 1. Gemini API 직접 호출 함수 (라이브러리 미사용)
# ==========================================
def call_gemini_raw(prompt):
    if not GOOGLE_API_KEY:
        print("❌ FATAL: API Key Missing")
        return None

    # Gemini 1.5 Flash 엔드포인트 (직접 호출)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    # JSON 강제 출력을 위한 프롬프트 보강
    full_prompt = prompt + "\n\nIMPORTANT: Output ONLY valid JSON array. No markdown code blocks."
    
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 1.0,
            "responseMimeType": "application/json"  # JSON 모드 강제
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            error_msg = f"API Error {response.status_code}: {response.text}"
            print(f"❌ {error_msg}")
            # 에러 발생 시 텔레그램으로 알림
            send_telegram_msg(f"⚠️ [Error #{RUN_NUMBER}] 구글 API 호출 실패:\n{response.text[:200]}")
            return None

        # 응답 파싱
        result_json = response.json()
        text_content = result_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        return text_content

    except Exception as e:
        print(f"❌ 통신 오류: {e}")
        return None

# ==========================================
# 2. 뉴스 분석 함수
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Raw API Mode)...")
    
    # 시작 알림 (테스트용)
    # send_telegram_msg(f"🎬 [Run #{RUN_NUMBER}] 분석 시작... (데이터: {len(articles)}건)")

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
                continue
        
        time.sleep(1) # API 부하 조절

    return results

# ==========================================
# 3. 결과 저장 및 전송
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
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return

    important_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = important_news[:5]

    if len(data) == 0:
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석된 데이터가 없습니다. (Raw API 오류 확인 필요)")
        return

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(기준: {IMPACT_THRESHOLD}점 이상)\n\n"
    
    if not top_news:
        msg += "특이사항 없음 (중요 뉴스 없음)"
    else:
        for item in top_news:
            score = item.get('score', 0)
            icon = "🔥" if score >= 7.0 else "⚡"
            msg += f"{icon} **{item.get('title')}** ({score}점)\n"
            msg += f"└ {item.get('summary')}\n"
            msg += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
    # 메시지 전송
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
            send_telegram_msg(f"📭 [GlobalStockNow #{RUN_NUMBER}] 수집된 뉴스 데이터가 없습니다.")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
        send_telegram_msg(f"❌ [GlobalStockNow #{RUN_NUMBER}] 데이터 파일이 없습니다.")
