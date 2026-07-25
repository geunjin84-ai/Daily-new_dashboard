import os
import json
import feedparser
import google.generativeai as genai
from google.generativeai import types
import time
from difflib import SequenceMatcher
import re

# 1. Gemini 설정
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# 2. RSS 피드 정의
RSS_FEEDS = {
    "1면/종합": ["[https://www.mk.co.kr/rss/30000001/](https://www.mk.co.kr/rss/30000001/)", "[https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml](https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml)"],
    "신문 사설": ["[https://www.khan.co.kr/rss/rssdata/opinion.xml](https://www.khan.co.kr/rss/rssdata/opinion.xml)", "[https://rss.hankyung.com/feed/opinion.xml](https://rss.hankyung.com/feed/opinion.xml)"],
    "글로벌/해외이슈": ["[https://feeds.a.dj.com/rss/RSSWorldNews.xml](https://feeds.a.dj.com/rss/RSSWorldNews.xml)", "[https://rss.nytimes.com/services/xml/rss/nyt/World.xml](https://rss.nytimes.com/services/xml/rss/nyt/World.xml)"],
    "해외 테크/AI": ["[https://techcrunch.com/feed/](https://techcrunch.com/feed/)", "[https://www.theverge.com/rss/index.xml](https://www.theverge.com/rss/index.xml)"],
    "경제/정책": ["[https://www.mk.co.kr/rss/30100041/](https://www.mk.co.kr/rss/30100041/)", "[https://rss.hankyung.com/feed/economy.xml](https://rss.hankyung.com/feed/economy.xml)"],
    "금융/증권": ["[https://www.mk.co.kr/rss/50200011/](https://www.mk.co.kr/rss/50200011/)", "[https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml](https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml)"],
    "산업/기업": ["[https://www.mk.co.kr/rss/50100032/](https://www.mk.co.kr/rss/50100032/)", "[https://rss.hankyung.com/feed/industry.xml](https://rss.hankyung.com/feed/industry.xml)"],
    "부동산": ["[https://www.mk.co.kr/rss/50300009/](https://www.mk.co.kr/rss/50300009/)", "[https://rss.hankyung.com/feed/land.xml](https://rss.hankyung.com/feed/land.xml)"],
    "IT/과학/Bio": ["[https://www.mk.co.kr/rss/50700001/](https://www.mk.co.kr/rss/50700001/)", "[https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/it.xml](https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/it.xml)"],
    "연예/스타": ["[https://rss.donga.com/entertainment.xml](https://rss.donga.com/entertainment.xml)", "[https://www.mk.co.kr/rss/30000023/](https://www.mk.co.kr/rss/30000023/)"],
    "문화/예술": ["[https://www.mk.co.kr/rss/70000001/](https://www.mk.co.kr/rss/70000001/)", "[https://rss.donga.com/culture.xml](https://rss.donga.com/culture.xml)"],
    "교육/입시": ["[https://rss.hankyung.com/feed/society.xml](https://rss.hankyung.com/feed/society.xml)", "[https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/society.xml](https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/society.xml)"]
}

def clean_title(title):
    title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    return title.strip()

def is_duplicate(new_title, existing_titles, threshold=0.65):
    clean_new = clean_title(new_title)
    for ext in existing_titles:
        if SequenceMatcher(None, clean_new, clean_title(ext)).ratio() > threshold:
            return True
    return False

def generate_multi_learning():
    """공식 Structured Outputs 스키마를 적용하여 JSON 오류를 원천 차단"""
    if not model:
        return get_fallback_learning()

    try:
        # 데이터가 절대 깨지지 않도록 엄격한 타입 가이드를 지정합니다.
        json_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "finance_sets": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "stock": types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "term": types.Schema(type=types.Type.STRING),
                                    "concept": types.Schema(type=types.Type.STRING),
                                    "analogy": types.Schema(type=types.Type.STRING),
                                    "signal": types.Schema(type=types.Type.STRING),
                                    "mts": types.Schema(type=types.Type.STRING),
                                }
                            ),
                            "economy": types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "title": types.Schema(type=types.Type.STRING),
                                    "concept": types.Schema(type=types.Type.STRING),
                                    "impact": types.Schema(type=types.Type.STRING),
                                }
                            ),
                            "quiz": types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "q": types.Schema(type=types.Type.STRING),
                                    "opts": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                                    "ans": types.Schema(type=types.Type.INTEGER),
                                    "exp": types.Schema(type=types.Type.STRING),
                                }
                            )
                        }
                    )
                ),
                "daily_sets": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "pattern": types.Schema(type=types.Type.STRING),
                            "words": types.Schema(
                                type=types.Type.ARRAY,
                                items=types.Schema(
                                    type=types.Type.OBJECT,
                                    properties={
                                        "word": types.Schema(type=types.Type.STRING),
                                        "example": types.Schema(type=types.Type.STRING),
                                        "meaning": types.Schema(type=types.Type.STRING),
                                    }
                                )
                            ),
                            "quote": types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "en": types.Schema(type=types.Type.STRING),
                                    "ko": types.Schema(type=types.Type.STRING),
                                    "author": types.Schema(type=types.Type.STRING),
                                }
                            ),
                            "question": types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "q": types.Schema(type=types.Type.STRING),
                                    "hint": types.Schema(type=types.Type.STRING),
                                }
                            )
                        }
                    )
                )
            }
        )

        prompt = """
        초보자를 위한 금융/주식 학습 세트 5개와 왕초보용 일상 영어 표현 세트 5개를 생성해라.
        - 영단어는 중학교 수준의 완전 초급 단어(Water, Book, Happy 등) 3개로 해라.
        - pattern은 일상생활 만능 회화 뼈대(Can I get ~?, I want to ~?) 1개로 해라.
        - 그 기초 단어가 패턴 안에 대입되어 바로 입으로 쓸 수 있는 매우 짧고 실용적인 일상 예문을 단어별로 작성해라.
        - question은 단어 하나로도 대답할 수 있는 AI의 매우 쉬운 1줄 일상 질문과 대답 가이드 힌트를 적어라.
        - 주식용어(finance_sets)에는 영어 약어가 포함될 경우 원어 풀네임을 넣지 말고 용어 고유명칭(예: PER)만 적어라.
        """

        response = model.generate_content(
            prompt,
            generation_config=types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=json_schema
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini API Schema Error: {e}")
        return get_fallback_learning()

def get_fallback_learning():
    """안전 모드 구동을 위한 백업 데이터셋 5개 고정 구조"""
    return {
        "finance_sets": [
            {"stock": {"term": "PER", "concept": "버는 돈 대비 주가 수준", "analogy": "1년 이익 대비 가게 매매가 비율", "signal": "🟢 10배 이하 저평가", "mts": "종목검색 ➔ 기업정보"}, "economy": {"title": "기준금리", "concept": "금리의 기준점", "impact": "대출 및 예금 이자 영향"}, "quiz": {"q": "PER이 낮으면?", "opts": ["저평가", "고평가"], "ans": 0, "exp": "이익 대비 주가가 싼 상태입니다."}},
            {"stock": {"term": "PBR", "concept": "가진 재산 대비 주가 수준", "analogy": "가게 장비 다 판 값과 주가의 비교", "signal": "🟢 1배 미만 저평가", "mts": "종목검색 ➔ 재무지표"}, "economy": {"title": "환율", "concept": "외국 돈과의 교환 비율", "impact": "수출입 물가 영향"}, "quiz":
