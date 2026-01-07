#!/usr/bin/env python3
# GlobalStockNow Analyzer v1.6 - 신기술/IT 뉴스 강제 포함 + 환각 최소화 (2026.1.8)

import json
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"  # 안정성 높은 1.5B 모델

print("AI 모델 로딩 시작 (Qwen2.5-1.5B)")
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
        summary = item.get('summary', '') or ''
        link = item.get('link', item.get('original_link', ''))
        published = item.get('published', '')

        # 신기술/IT 키워드 체크 (강제 포함 여부 판단)
        tech_keywords = ['ces', 'laptop', 'notebook', 'wi-fi', 'wifi', 'ai', 'artificial intelligence',
                         'robot', 'humanoid', 'display', 'oled', 'micro led', 'hbm', 'chip', 'semiconductor',
                         'battery', 'ev', 'smart', 'gadget', 'tech', 'innovation', 'product launch']
        content_lower = (title + " " + summary).lower()
        is_tech_news = any(kw in content_lower for kw in tech_keywords)

        prompt = f"""
다음 해외 뉴스를 한국 주식 시장 투자자 관점에서 분석하세요. **사실에 기반해서만 답변하고, 추측이나 가짜 정보는 절대 만들지 마세요.**

제목: {title}
요약: {summary}

특별 규칙:
- CES, 노트북, Wi-Fi, AI, 로봇, 반도체, 디스플레이, 배터리, 인공 피부 등 **신기술/IT 신상품 관련 뉴스**는 영향도가 0점이라도 반드시 결과에 포함하세요 (한국 기업 잠재 수혜/경쟁 가능성 때문).
- 정치·지정학 뉴스는 영향도 0~3점으로 엄격히 판단.
- 경제·기술 뉴스만 영향도 7점 이상 부여 가능.

1. 한국 시장 영향도: 0~10점 (0점: 무관 또는 영향 미미)
2. 영향 받는 한국 종목: 뉴스에 직접 관련된 종목만 나열 (없으면 빈 목록)
3. 이유: 한글로 1~2문장, 뉴스에 나온 사실만 기반으로 설명

반드시 이 JSON 형식으로만 출력:
{{
  "title": "{title}",
  "impact_score": 점수,
  "korean_stocks": ["종목1", "종목2"],
  "reason": "상세 이유 한글 설명"
}}
"""

        inputs = tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=250,
                temperature=0.3,  # 환각 최소화
                top_p=0.9,
                do_sample=True
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        response = response[len(prompt):].strip()  # 프롬프트 제거

        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            analyzed = json.loads(json_str)
        except Exception as e:
            print(f"JSON 파싱 실패 ({title}): {e}")
            analyzed = {
                "title": title,
                "impact_score": 0 if not is_tech_news else 3,  # 기술 뉴스는 최소 3점 보장
                "korean_stocks": [],
                "reason": "신기술/IT 관련 뉴스로 잠재 영향 가능성 있으나 직접적 언급 없음." if is_tech_news else "한국 주식 시장에 직접적인 영향이 없는 뉴스입니다."
            }

        analyzed["original_link"] = link
        analyzed["published"] = published
        results.append(analyzed)

    return results

if __name__ == "__main__":
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            news_data = json.load(f)
    except FileNotFoundError:
        news_data = []
        print("breaking_news.json 파일 없음")

    if not news_data:
        print("분석할 뉴스 없음")
        analyzed_data = []
    else:
        analyzed_data = analyze_news(news_data)

    with open('analyzed_news.json', 'w', encoding='utf-8') as f:
        json.dump(analyzed_data, f, indent=2, ensure_ascii=False)

    print(f"AI 분석 완료 - {len(analyzed_data)}개 뉴스 처리 → analyzed_news.json 저장")
