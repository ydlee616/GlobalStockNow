#!/usr/bin/env python3
# GlobalStockNow Analyzer v1.0 - Qwen2.5 기반 한국 시장 영향도 분석 (2026.1.3)

import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

print("AI 모델 로딩 시작 (Qwen2.5-1.5B)")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
    low_cpu_mem_usage=True
)

print("AI 모델 로딩 완료")

def analyze_news(news_list):
    if not news_list:
        print("분석할 뉴스 없음")
        return []

    results = []
    for item in news_list:
        title = item['title']
        summary = item.get('summary', '')

        prompt = f"""
다음 해외 속보를 분석해 주세요. 한국 주식 시장에 미치는 영향도를 0~10점으로 평가하고, 관련 한국 종목과 이유를 간단히 설명하세요.

뉴스 제목: {title}
요약: {summary}

출력 형식 (JSON 배열의 한 객체로):
{{
  "title": "뉴스 제목",
  "impact_score": 0~10,
  "korean_stocks": ["종목1", "종목2"],
  "reason": "간단한 이유"
}}
"""

        inputs = tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = inputs.to('cuda')

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=0.3,
                do_sample=True
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = response[len(prompt):].strip()  # 프롬프트 부분 제거

        # JSON 추출 시도
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            analyzed = json.loads(json_str)
            analyzed["original_link"] = item['link']
            analyzed["published"] = item['published']
            results.append(analyzed)
            print(f"분석 완료: {title}")
        except:
            print(f"JSON 파싱 실패, 기본값 사용: {title}")
            results.append({
                "title": title,
                "impact_score": 5,
                "korean_stocks": [],
                "reason": "분석 실패 (임시값)",
                "original_link": item['link'],
                "published": item['published']
            })

    return results

if __name__ == "__main__":
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            news_data = json.load(f)
    except:
        news_data = []

    analyzed_data = analyze_news(news_data)

    with open('analyzed_news.json', 'w', encoding='utf-8') as f:
        json.dump(analyzed_data, f, indent=2, ensure_ascii=False)

    print(f"AI 분석 완료 - {len(analyzed_data)}개 결과 저장")
