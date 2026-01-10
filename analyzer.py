#!/usr/bin/env python3
# GlobalStockNow Analyzer v1.7 - 행간/파급효과 분석 강화 + 신기술/IT 강제 포함 (2026.1.9)

import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import time

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"  # 경량 모델로 속도 최적화

print("AI 모델 로딩 시작 (Qwen2.5-0.5B)")
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
    for idx, item in enumerate(news_list):
        start_time = time.time()
        title = item['title']
        summary = item.get('summary', '') or ''
        link = item.get('link', item.get('original_link', ''))
        published = item.get('published', '')

        # 신기술/IT 키워드 체크 (강제 포함)
        tech_keywords = ['ces', 'laptop', 'notebook', 'wi-fi', 'wifi', 'ai', 'robot', 'humanoid',
                         'display', 'oled', 'hbm', 'chip', 'semiconductor', 'battery', 'ev', 'tech', 'innovation']
        content_lower = (title + " " + summary).lower()
        is_tech_news = any(kw in content_lower for kw in tech_keywords)

        prompt = f"""
다음 해외 뉴스를 한국 주식 시장 투자자 관점에서 분석하세요. 사실에 기반해서만 답변하고, 추측이나 가짜 정보는 절대 만들지 마세요. 뉴스 내용의 행간을 잘 파악하여 잠재적 파급효과를 적극적으로 고려해서 분석하세요.

제목: {title}
요약: {summary}

특별 규칙:
- CES, 노트북, Wi-Fi, AI, 로봇, 반도체, 디스플레이, 배터리, 인공 피부 등 신기술/IT 신상품 관련 뉴스는 영향도가 낮더라도 반드시 포함하세요 (한국 기업 잠재 수혜/경쟁 가능성 때문).
- 정치·지정학 뉴스는 기본 0~3점으로 엄격히 판단.
- 경제·기술 뉴스 및 잠재적 파급효과가 있는 경우 4~8점까지 적극 평가.
- 잠재적·간접적 파급효과(예: Wi-Fi 8 채택 시 삼성/LG전자 수혜 가능성, 중동 불안 시 유가 상승 → 에너지주 영향 등)는 3~6점으로 평가하여 브리핑에 포함하세요.

1. 한국 시장 영향도: 0~10점
2. 영향 받는 한국 종목: 뉴스에 직접 관련된 종목만 나열 (없으면 빈 목록)
3. 이유: 한글로 1~2문장, 뉴스 사실과 행간/파급효과 기반으로 설명

반드시 이 JSON 형식으로만 출력:
{{
  "title": "{title}",
  "impact_score": 점수,
  "korean_stocks": ["종목1", "종목2"],
  "reason": "상세 이유 한글 설명"
}}
"""

        inputs = tokenizer(prompt, return_tensors="pt")

        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=250,
                    temperature=0.35,
                    top_p=0.9,
                    do_sample=True
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
                    "impact_score": 4 if is_tech_news else 0,
                    "korean_stocks": [],
                    "reason": "신기술/IT 관련 뉴스로 잠재 파급효과 있음." if is_tech_news else "직접 영향 없음."
                }
        except Exception as e:
            print(f"분석 실패 ({title[:50]}...): {e}")
            analyzed = {
                "title": title,
                "impact_score": 4 if is_tech_news else 0,
                "korean_stocks": [],
                "reason": "분석 중 오류 발생, 잠재 영향 뉴스." if is_tech_news else "분석 중 오류."
            }

        analyzed["original_link"] = link
        analyzed["published"] = published
        results.append(analyzed)

        elapsed = time.time() - start_time
        print(f"  [{idx+1}/{len(news_list)}] 분석 완료 ({elapsed:.1f}초)")

    return results

if __name__ == "__main__":
    start_total = time.time()
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            news_data = json.load(f)
    except:
        news_data = []

    if not news_data:
        print("뉴스 없음")
        analyzed_data = []
    else:
        print(f"{len(news_data)}개 뉴스 분석 시작")
        analyzed_data = analyze_news(news_data)

    with open('analyzed_news.json', 'w', encoding='utf-8') as f:
        json.dump(analyzed_data, f, indent=2, ensure_ascii=False)

    total_time = time.time() - start_total
    print(f"전체 분석 완료: {len(analyzed_data)}개 ({total_time:.1f}초)")
