import json
import time
import requests
import os
import re  # 정규표현식 모듈 추가 (핵심)
import google.generativeai as genai
from datetime import datetime

# ==========================================
# [설정 영역] GitHub Secrets & Env Variables
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

# 파일 경로
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

# Gemini 설정
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("❌ Error: GOOGLE_API_KEY가 설정되지 않았습니다.")

# ==========================================
# 1. 뉴스 분석 함수 (Regex 파싱 적용)
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] 총 {len(articles)}개의 기사를 {batch_size}개씩 나누어 분석 시작...")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        You are a professional stock market analyst.
        Analyze the following news articles and extract key insights for investors.
        
        [Input Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirement]:
        Return the result ONLY in valid JSON format (list of objects).
        Do not use markdown code blocks.
        Each object must have:
        - "title": A concise 1-line headline in Korean.
        - "summary": A 2-sentence summary in Korean.
        - "impact": "Positive", "Negative", or "Neutral".
        - "related_stocks": List of related stock tickers or company names.
        """

        try:
            response = model.generate_content(prompt)
            
            # [수정된 핵심 파트] 정규표현식으로 JSON 리스트([ ... ])만 강제로 추출
            match = re.search(r'\[.*\]', response.text, re.DOTALL)
            
            if match:
                clean_text = match.group()
                batch_result = json.loads(clean_text)
                
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
            else:
                print(f"⚠️ Batch {i}: JSON 패턴을 찾을 수 없음. 응답 원본: {response.text[:100]}...")

            time.sleep(1) # API 부하 방지
            
        except Exception as e:
            print(f"⚠️ Error in batch {i}: {e}")
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
    
    print(f"✅ 분석 완료! {OUTPUT_FILE} 저장됨. (Run #{RUN_NUMBER}, 총 {len(data)}건)")
    return output_data

# ==========================================
# 3. 텔레그램 전송 함수
# ==========================================
def send_telegram_report(analyzed_data):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 없어 전송을 건너뜁니다.")
        return

    # 데이터가 없으면 알림
    if not analyzed_data['reports']:
        print("📭 전송할 분석 데이터가 없습니다.")
        # 빈 메시지라도 보내서 확인하고 싶다면 아래 주석 해제
        # requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": f"⚠️ [Run #{RUN_NUMBER}] 분석된 데이터가 0건입니다. 로그를 확인하세요."})
        return

    print("🚀 텔레그램 전송 시작...")
    
    # 중요도 로직: 'Positive'나 'Negative'인 것을 먼저 보여줌
    reports = analyzed_data['reports']
    important_news = [r for r in reports if r.get('impact') in ['Positive', 'Negative']]
    other_news = [r for r in reports if r.get('impact') == 'Neutral']
    
    # 중요 뉴스 우선 정렬 + 최대 5개
    final_list = (important_news + other_news)[:5]
    
    message = f"📢 **[GlobalStockNow 분석 (#{RUN_NUMBER})]**\n"
    message += f"({analyzed_data['analyzed_at'][:16]})\n\n"
    
    for item in final_list:
        icon = "🔥" if item.get('impact') == 'Positive' else "🔻" if item.get('impact') == 'Negative' else "➖"
        title = item.get('title', '제목 없음')
        summary = item.get('summary', '요약 없음')
        stocks = ', '.join(item.get('related_stocks', []))
        
        message += f"{icon} **{title}**\n"
        message += f"└ {summary}\n"
        message += f"└ 관련주: {stocks}\n\n"
    
    message += f"👉 총 {analyzed_data['count']}건 분석 완료."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        requests.post(url, data=payload)
        print("✅ 텔레그램 메시지 전송 성공!")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

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
