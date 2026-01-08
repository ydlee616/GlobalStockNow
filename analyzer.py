#!/usr/bin/env python3
# GlobalStockNow Analyzer v5.1 (Final Stable)
# 작성일: 2026.01.09
# 기능: 수집된 속보를 Gemini Pro로 정밀 분석 (오류 방지 및 IT 강제 포함 로직 적용)

import json
import os
import datetime
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ---------------------------------------------------------
# [설정] API KEY
# ---------------------------------------------------------
API_KEY = "AIzaSyAZo0o_Sq6ojtLnbmJ5mjqCelKFuBw15dY"

# 보스가 지정한 '무조건 살려야 하는' 키워드 목록
TECH_KEYWORDS = [
    'CES', 'Laptop', 'Notebook', 'Wi-Fi', 'WiFi', 'AI', 'Robot', 
    'Humanoid', 'Display', 'OLED', 'HBM', 'Chip', 'Semiconductor', 
    'Battery', 'EV', 'Smart', 'Innovation', 'Samsung', 'LG', 'SK'
]

def load_news():
    """수집된 뉴스 파일(breaking_news.json)을 읽어옵니다."""
    filename = 'breaking_news.json'
    
    # 파일이 아예 없으면 빈 리스트 반환 (에러 방지)
    if not os.path.exists(filename):
        print(f"⚠️ '{filename}' 파일이 없습니다. 빈 리스트로 진행합니다.")
        return []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('articles', data) if isinstance(data, dict) else data
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")
        return []

def analyze_news_with_gemini(articles):
    """Gemini 1.5 Pro에게 뉴스를 분석시킵니다."""
    if not articles:
        return []

    print(f"[{datetime.datetime.now()}] 🧠 Gemini 1.5 Pro 분석 엔진 가동... (뉴스 {len(articles)}건)")
    
    genai.configure(api_key=API_KEY)
    
    # 모델 설정 (안정성: 1.5 Pro)
    model_name = 'gemini-1.5-pro-latest' 
    model = genai.GenerativeModel(model_name)

    # 뉴스 데이터를 텍스트로 변환
    news_content = json.dumps(articles, ensure_ascii=False)
    
    # 보스의 지시사항(프롬프트)을 AI에게 입력
    prompt = f"""
    You are the Chief Investment Strategist for 'Global Stock Now'.
    Analyze the following global news and identify its impact on the **South Korean Stock Market**.

    [INPUT NEWS DATA]
    {news_content}

    [MANDATORY RULES]
    1. **Tech & IT Focus**: If a news item contains keywords like {TECH_KEYWORDS}, you MUST include it in the output, even if the immediate impact is low (score 3-6).
    2. **Impact Score (0-10)**:
       - 10: Market crash/boom imminent.
       - 7-9: Strong impact on major Korean stocks (Samsung, LG, SK, etc.).
       - Below 7: Filter out ONLY IF it is NOT a Tech/IT news.
    3. **Logic**: Connect the dots. (e.g., Apple's new feature -> LG Innotek benefit?)
    4. **Language**: Output strictly in **KOREAN**.

    [OUTPUT FORMAT]
    Return a JSON list of objects.
    [
        {{
            "title": "Korean Title (Catchy)",
            "original_title": "Original English Title",
            "impact_score": 8.5,
            "related_stocks": ["Samsung Electronics", "LG Energy Solution"],
            "analysis": "Reason why this matters to Korea (2-3 sentences).",
            "is_tech_news": true/false
        }}
    ]
    """

    try:
        # 안전 설정 해제 (금융 분석이므로)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # JSON 정제
        raw_text = response.text
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]
            
        analyzed_data = json.loads(raw_text.strip())
        print(f"✅ 분석 완료: {len(analyzed_data)}개의 유의미한 리포트 생성")
        return analyzed_data

    except Exception as e:
        print(f"❌ Gemini 분석 중 오류 발생: {e}")
        return []

def save_result(analyzed_list):
    """결과를 파일로 저장합니다."""
    filename = "analyzed_news.json"
    
    final_data = {
        "analyzed_at": str(datetime.datetime.now()),
        "count": len(analyzed_list),
        "reports": analyzed_list
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print(f"💾 리포트 저장 완료: {filename}")

if __name__ == "__main__":
    # 1. 뉴스 로드
    raw_news = load_news()
    
    # 2. AI 분석 (데이터가 없어도 빈 리스트 처리)
    reports = []
    if raw_news:
        reports = analyze_news_with_gemini(raw_news)
    else:
        print("⚠️ 분석할 뉴스 데이터가 없습니다. 빈 리포트를 생성합니다.")

    # 3. 결과 무조건 저장 (파일 생성 보장)
    save_result(reports)
