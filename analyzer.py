import json
import time
import requests
import os
import google.generativeai as genai
from datetime import datetime

# ==========================================
# [설정 영역]
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

# 영향도 기준 (3.0점)
IMPACT_THRESHOLD = 3.0

INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

# Gemini 설정 (JSON 강제 모드 활성화)
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    # 🔥 핵심 변경: AI가 무조건 JSON만 뱉도록 설정
    generation_config = {
        "temperature": 1,
        "response_mime_type": "application/json",
    }
    model = genai.GenerativeModel('gemini-1.5-flash', generation_config=generation_config)
else:
    print("❌ Error: GOOGLE_API_KEY가 없습니다.")

# ==========================================
# 1. 뉴스 분석 함수 (JSON Mode)
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작... (기준: {IMPACT_THRESHOLD}점)")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        # 프롬프트: JSON 스키마를 명확히 제시
        prompt = f"""
        You are a stock market analyst. 
        Analyze these news articles. Even minor news should be scored.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirement]:
        Output a JSON List of objects. 
        Key fields:
        - title (Korean)
        - summary (Korean, 1 sentence)
        - score (Float 0.0-10.0)
        - related_stocks (List of strings)
        """

        try:
            response = model.generate_content(prompt)
            
            # 🔥 디버깅용 로그 (혹시 실패하면 로그에서 확인 가능)
            # print(f"DEBUG Response: {response.text[:100]}...") 

            # JSON 모드이므로 바로 로드 가능
            batch_result = json.loads(response.text)
            
            # 리스트인지 단일 객체인지 확인 후 병합
            if isinstance(batch_result, list):
                results.extend(batch_result)
            elif isinstance(batch_result, dict):
                # 가끔 최상위 키로 감싸는 경우가 있음
                if 'articles' in batch_result:
                    results.extend(batch_result['articles'])
                else:
                    results.append(batch_result)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠️ Error in batch {i}: {e}")
            # 에러 발생 시 원본 텍스트 출력하여 디버깅 도움
            try:
                print(f"Fail context: {response.text}")
            except:
                pass
            continue

    return results

# ==========================================
# 2. 결과 저장 함수
# ==========================================
def save_results(data):
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨. (Run #{RUN_NUMBER})")
    return output_data

# ==========================================
# 3. 텔레그램 전송 함수
# ==========================================
def send_telegram_report(analyzed_data):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    reports = analyzed_data.get('reports', [])
    
    # 점수 필터링
    important_news = [
        r for r in reports 
        if float(r.get('score', 0)) >= IMPACT_THRESHOLD
    ]
    
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = important_news[:5]

    # [케이스 1] 분석된 중요 뉴스가 없을 때
    if not top_news:
        message = f"📢 **[GlobalStockNow AI 브리핑 (#{RUN_NUMBER})]**\n\n"
        message += f"특이사항 없음 (모든 뉴스 점수 {IMPACT_THRESHOLD} 미만)\n"
        message += f"확인된 뉴스: {len(reports)}건"
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
        return

    # [케이스 2] 중요 뉴스가 있을 때
    print(f"🚀 중요 뉴스 {len(top_news)}건 전송 시작...")
    
    message = f"📢 **[GlobalStockNow AI 브리핑 (#{RUN_NUMBER})]**\n"
    message += f"기준: 영향도 {IMPACT_THRESHOLD} 이상\n\n"
    
    for item in top_news:
        score = item.get('score', 0)
        # 이모지 로직
        icon = "🔥" if score >= 8.0 else "⚡" if score >= 5.0 else "👀"
        
        message += f"{icon} **{item.get('title', '제목 없음')}** (점수: {score})\n"
        message += f"└ {item.get('summary', '요약 없음')}\n"
        message += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
    # 텔레그램 메시지 길이 제한 방지 (4096자)
    if len(message) > 4000:
        message = message[:4000] + "\n...(내용 잘림)..."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    requests.post(url, data=payload)

# ==========================================
# 메인 실행부
# ==========================================
if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            articles = raw_data.get('articles', [])
            
        if articles:
            results = analyze_news_batch(articles)
            final_data = save_results(results)
            send_telegram_report(final_data)
        else:
            print("📭 뉴스 데이터가 비어 있습니다.")
    else:
        print(f"❌ {INPUT_FILE} 파일을 찾을 수 없습니다.")
