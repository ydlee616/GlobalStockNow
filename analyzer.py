"""Module: analyzer.py | Version: 1.8.0 | Focus: High-Quality HTML & File Output"""
import json, time, requests, os

# [Master Logic] 7단계 전문 프롬프트 셋팅
BLOG_PROMPT = """당신은 'The Specialist' 주식/테크 유튜버입니다. 
다음 뉴스를 바탕으로 독자가 전율을 느낄 만큼 전문적이고 재미있는 블로그 HTML을 작성하세요.

[필수 구조]:
1. 요약: "이 뉴스, 딱 3줄로 끝내드립니다."
2. 배경: "판이 어떻게 깔렸나? (거시적 흐름)"
3. 행간: "기사 뒤에 숨은 빅테크의 음흉한(?) 계산기 소리"
4. 역사: "과거 000 사건과 소름 돋게 닮은 현재" (테이블 포함)
5. 영향: "내 계좌를 불려줄 K-관련주(삼성전자, 두산에너빌리티 등) 정밀 타격"
6. 시가: "지금 호가창이 말해주는 실시간 민심"
7. 리스크: "장밋빛 희망회로 돌리기 전에 꼭 봐야 할 가시"

문체: 슈카월드처럼 위트 있게, 실리콘밸리 기술 컨퍼런스처럼 세련되게 작성.
형식: CSS가 포함된 단일 <div> 태그 형태."""

def save_as_html_file(content, filename="special_list.html"):
    """[신규] 분석 결과를 HTML 파일로 저장하는 로직"""
    header = """<meta charset="utf-8"><style>
        .master-box { max-width: 800px; margin: auto; font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }
        .section { margin-bottom: 30px; padding: 20px; border-radius: 12px; background: #ffffff; border: 1px solid #e1e4e8; }
        .highlight { color: #00698f; font-weight: bold; border-left: 5px solid #00698f; padding-left: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: center; }
        th { background: #f8f9fa; color: #00698f; }
    </style><div class="master-box">"""
    footer = "</div>"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(header + content + footer)
    print(f"✅ 파일 생성 완료: {filename}")

# ... (기존 분석 및 전송 로직 동일) ...
# analyze_result = generate_content_with_groq(BLOG_PROMPT, news_data)
# save_as_html_file(analyze_result)
