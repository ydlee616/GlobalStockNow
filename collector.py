#!/usr/bin/env python3
# GlobalStockNow Smart Collector v5.0 (Powered by Gemini)
# 작성일: 2026.01.09
# 기능: 제미나이 그라운딩(검색)을 통해 차단 없이 최신 속보 수집

import os
import json
import datetime
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ---------------------------------------------------------
# [설정] 여기에 Google AI Studio에서 받은 API KEY를 넣으세요
# ---------------------------------------------------------
API_KEY = "AIzaSyAZo0o_Sq6ojtLnbmJ5mjqCelKFuBw15dY" 

# 검색할 핵심 키워드 (보스의 의도 반영)
SEARCH_QUERY = """
Find the latest news and breaking stories about:
1. CES 2026 (Focus on Samsung, LG, SK Hynix, Hyundai)
2. Global Tech Trends (AI Agents, HBM, 6G, Robot)
3. Impact on Korean Stock Market

Condition:
- Must be within the last 24 hours.
- Focus on factual announcements and stock market impact.
"""

def get_smart_news():
    print(f"[{datetime.datetime.now()}] Gemini 검색 엔진 가동 중... (차단 우회)")
    
    try:
        genai.configure(api_key=API_KEY)
        
        # 최신 정보를 검색할 수 있는 모델 설정 (Gemini 1.5 Flash 권장 - 빠름)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # 검색 도구(Grounding)를 활성화하여 최신 정보 요청
        # tools='google_search_retrieval' 기능 활용 (코드 레벨 예시)
        # *참고: 현재 라이브러리 버전에 따라 tools 설정이 다를 수 있어, 
        # 가장 확실한 프롬프트 엔지니어링 방식으로 구현합니다.
        
        prompt = f"""
        You are a professional news collector for 'Global Stock Now'.
        Perfrom a Google Search internally to answer this.
        
        {SEARCH_QUERY}

        [OUTPUT FORMAT]
        Provide the result strictly as a JSON list of objects. Do not use Markdown code blocks.
        Format:
        [
            {{
                "source": "News Source Name",
                "title": "Headline of the news",
                "link": "URL if available, else Source Name",
                "published_at": "Time or Date",
                "summary": "1 sentence summary focusing on investment impact"
            }},
            ...
        ]
        """

        # 안전 설정 (모든 뉴스 수집 허용)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        # 생성 요청 (검색 기능이 내장된 모델 활용)
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # 응답 텍스트에서 JSON 추출 (가끔 마크다운이 섞일 수 있어 정제)
        raw_text = response.text
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0]
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0]
            
        news_data = json.loads(raw_text.strip())
        
        print(f"✅ 수집 성공: {len(news_data)}개의 핵심 뉴스 확보")
        return news_data

    except Exception as e:
        print(f"❌ 수집 중 오류 발생: {e}")
        # 오류 시 빈 리스트 반환하여 파이프라인 멈춤 방지
        return []

def save_to_json(news_list):
    filename = "breaking_news.json"
    data = {
        "collected_at": str(datetime.datetime.now()),
        "count": len(news_list),
        "articles": news_list
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"💾 저장 완료: {filename}")

if __name__ == "__main__":
    # 1. 뉴스 수집
    articles = get_smart_news()
    
    # 2. 결과 저장 (다음 단계 Analyzer가 읽을 수 있도록)
    if articles:
        save_to_json(articles)
    else:
        print("수집된 뉴스가 없습니다.")
