#!/usr/bin/env python3
# GlobalStockNow Analyzer v1.2 - 한글 출력 강화 (2026.1.7)

import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

print("AI 모델 로딩 시작")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,
    device_map="auto",
    low_cpu_mem_usage=True
)
print("AI 모델 로딩 완료")

def analyze_news(news_list):
    results = []
    for item in news_list:
        title = item['title']
        summary = item.get('summary', '')

        prompt = f"""
다음 해외 속보를 한국 주식 시장 관점에서 분석해 주세요.

뉴스 제목: {title}
요약: {summary}

영향도 0~10점 평가 (0: 무관, 10: 매우 강한 영향)
관련 한국 종목 목록과 이유를 한글로 설명하세요.

JSON 형식으로만 출력:
{{
  "title": "{title}",
  "impact_score": 점수,
  "korean_stocks": ["종목1", "종목2"],
  "reason": "상세 이유"
}}
"""

        inputs = tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=0.4
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        response = response[len(prompt):].strip()

        try:
            json_start = response.rfind('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            analyzed = json.loads(json_str)
        except:
            analyzed = {
                "title": title,
                "impact_score": 0,
                "korean_stocks": [],
                "reason": "분석 실패 - 한국 시장 영향 없음으로 판단"
            }

        analyzed["original_link"] = item['link']
        analyzed["published"] = item['published']
        results.append(analyzed)

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

    print(f"AI 분석 완료 - {len(analyzed_data)}개 결과")
