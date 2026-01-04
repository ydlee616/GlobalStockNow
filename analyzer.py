#!/usr/bin/env python3
# GlobalStockNow Analyzer v1.1 - 점수 로직 강화 (2026.1.3)

import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,
    device_map="auto",
    low_cpu_mem_usage=True
)

def analyze_news(news_list):
    results = []
    for item in news_list:
        title = item['title']
        summary = item.get('summary', '')

        prompt = f"""
다음 해외 속보를 분석해 주세요. 한국 주식 시장에 미치는 영향도를 0~10점으로 평가하세요.
- 직접 관련 없음: 0~3점
- 간접적 영향: 4~6점
- 직접적 영향: 7~10점

뉴스 제목: {title}
요약: {summary}

출력 형식 (JSON 객체):
{{
  "title": "뉴스 제목",
  "impact_score": 0~10,
  "korean_stocks": ["종목1", "종목2"],
  "reason": "영향 이유 (한국 시장 중심)"
}}
"""

        inputs = tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.5
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        response = response[len(prompt):]  # 프롬프트 제거

        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            analyzed = json.loads(json_str)
            analyzed["original_link"] = item['link']
            analyzed["published"] = item['published']
            results.append(analyzed)
        except:
            results.append({
                "title": title,
                "impact_score": 0,
                "korean_stocks": [],
                "reason": "분석 실패 - 무관 뉴스",
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
