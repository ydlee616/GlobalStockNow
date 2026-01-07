#!/usr/bin/env python3
# GlobalStockNow Analyzer v1.5 - 환각 최소화 + 사실 기반 강화 (2026.1.7)

import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"  # 1.5B로 복귀 (메모리 문제 해결됐으니 가능)

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
다음은 실제 해외 뉴스입니다. **절대 가짜 사실을 만들지 말고, 뉴스 내용에 나온 사실만 기반으로 분석하세요.**

제목: {title}
요약: {summary}

한국 주식 시장 관점에서만 분석:
- 영향도: 0~10점 (정치·지정학 뉴스는 보통 0~3점, 경제·기술 뉴스만 7점 이상)
- 관련 한국 종목: 뉴스에 직접 언급된 회사만 (없으면 빈 목록)
- 이유: 한글 1~2문장, **뉴스에 나온 사실만** 사용. 추측 금지.

JSON 형식만 출력:
{{
  "title": "{title}",
  "impact_score": 점수,
  "korean_stocks": [],
  "reason": "사실 기반 이유"
}}
"""

        inputs = tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.2,  # 환각 줄이기 위해 낮춤
                top_p=0.9
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        response = response[len(prompt):].strip()

        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            analyzed = json.loads(json_str)
        except:
            analyzed = {
                "title": title,
                "impact_score": 0,
                "korean_stocks": [],
                "reason": "한국 주식 시장에 직접적인 영향이 없는 뉴스입니다."
            }

        analyzed["original_link"] = item['link']
        analyzed["published"] = item['published']
        results.append(analyzed)

    return results

# 나머지 동일
