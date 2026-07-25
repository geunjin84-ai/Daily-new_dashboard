import os
import json
import feedparser
import google.generativeai as genai
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
    "1면/종합": ["https://www.mk.co.kr/rss/30000001/", "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml"],
    "신문 사설": ["https://www.khan.co.kr/rss/rssdata/opinion.xml", "https://rss.hankyung.com/feed/opinion.xml"],
    "글로벌/해외이슈": ["https://feeds.a.dj.com/rss/RSSWorldNews.xml", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"],
    "해외 테크/AI": ["https://techcrunch.com/feed/", "https://www.theverge.com/rss/index.xml"],
    "경제/정책": ["https://www.mk.co.kr/rss/30100041/", "https://rss.hankyung.com/feed/economy.xml"],
    "금융/증권": ["https://www.mk.co.kr/rss/50200011/", "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"],
    "산업/기업": ["https://www.mk.co.kr/rss/50100032/", "https://rss.hankyung.com/feed/industry.xml"],
    "부동산": ["https://www.mk.co.kr/rss/50300009/", "https://rss.hankyung.com/feed/land.xml"],
    "IT/과학/Bio": ["https://www.mk.co.kr/rss/50700001/", "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/it.xml"],
    "연예/스타": ["https://rss.donga.com/entertainment.xml", "https://www.mk.co.kr/rss/30000023/"],
    "문화/예술": ["https://www.mk.co.kr/rss/70000001/", "https://rss.donga.com/culture.xml"],
    "교육/입시": ["https://rss.hankyung.com/feed/society.xml", "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/society.xml"]
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
    """Gemini API 안정적 호환 및 예외 처리 완비"""
    if not model:
        return get_fallback_learning()

    try:
        prompt = """
        초보자를 위한 금융/주식 학습 세트 5개와 왕초보용 일상 영어 표현 세트 5개를 생성해라.
        반드시 설명이나 마크다운 표현(```json 등) 없이, 오직 완벽한 JSON 텍스트 하나만 출력해라.

        [JSON 양식 구조]:
        {
          "finance_sets": [
            {
              "stock": {"term": "PER", "concept": "이 회사가 버는 돈 대비 주가가 싸냐, 비싸냐?", "analogy": "1년에 100만 원 버는 가게를 1000만 원에 산다면 PER은 10배!", "signal": "🟢 10배 이하: 저평가 | 🔴 30배 이상: 고평가", "mts": "종목 검색 ➔ [기업정보] ➔ [재무/지표]"},
              "economy": {"title": "기준금리", "concept": "모든 이자의 기준점", "impact": "금리가 오르면 대출 이자 부담이 커져요."},
              "quiz": {"q": "PER이 낮다는 것은 보통 무슨 의미일까요?", "opts": ["이익 대비 주가가 저평가되어 있다", "회사가 위험하다"], "ans": 0, "exp": "이익 대비 주가가 낮은 상태입니다."}
            }
          ],
          "daily_sets": [
            {
              "pattern": "Can I get ~ ? (~ 좀 주시겠어요?)",
              "words": [
                {"word": "Water (물)", "example": "Can I get water?", "meaning": "물 좀 주시겠어요?"},
                {"word": "Coffee (커피)", "example": "Can I get coffee?", "meaning": "커피 좀 주시겠어요?"},
                {"word": "The bill (계산서)", "example": "Can I get the bill?", "meaning": "계산서 좀 주시겠어요?"}
              ],
              "quote": {"en": "The only way to do great work is to love what you do.", "ko": "위대한 일을 하는 유일한 방법은 당신이 하는 일을 사랑하는 것이다.", "author": "Steve Jobs"},
              "question": {"q": "How are you today?", "hint": "I am good! 또는 I am tired. 라고 대답해보세요."}
            }
          ]
        }
        finance_sets와 daily_sets 항목을 각각 서로 다른 내용으로 5개씩 풍부하게 채워라.
        """

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # JSON 텍스트 부분만 안전하게 추출
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Gemini API Error: {e}")
        
    return get_fallback_learning()

def get_fallback_learning():
    """API 실패 시에도 대시보드가 완벽히 작동하도록 보장하는 백업 데이터셋 5개"""
    return {
        "finance_sets": [
            {"stock": {"term": "PER", "concept": "버는 돈 대비 주가 수준", "analogy": "1년 이익 대비 가게 매매가 비율", "signal": "🟢 10배 이하 저평가", "mts": "종목검색 ➔ 기업정보"}, "economy": {"title": "기준금리", "concept": "금리의 기준점", "impact": "대출 및 예금 이자 영향"}, "quiz": {"q": "PER이 낮으면?", "opts": ["저평가", "고평가"], "ans": 0, "exp": "이익 대비 주가가 싼 상태입니다."}},
            {"stock": {"term": "PBR", "concept": "가진 재산 대비 주가 수준", "analogy": "가게 장비 다 판 값과 주가의 비교", "signal": "🟢 1배 미만 저평가", "mts": "종목검색 ➔ 재무지표"}, "economy": {"title": "환율", "concept": "외국 돈과의 교환 비율", "impact": "수출입 물가 영향"}, "quiz": {"q": "PBR 1배 미만은?", "opts": ["저평가", "고평가"], "ans": 0, "exp": "재산 가치보다 주가가 낮습니다."}},
            {"stock": {"term": "ROE", "concept": "투자한 돈으로 얼마나 버는가", "analogy": "자본금 대비 연간 순이익 비율", "signal": "🟢 10% 이상 우수", "mts": "기업분석 ➔ 투자지표"}, "economy": {"title": "인플레이션", "concept": "물가가 지속적으로 오르는 현상", "impact": "화폐 가치가 떨어져요."}, "quiz": {"q": "ROE가 높으면?", "opts": ["경영 효율이 좋음", "나쁨"], "ans": 0, "exp": "투입한 자본 대비 돈을 잘 번다는 뜻입니다."}},
            {"stock": {"term": "CPI", "concept": "소비자가 사는 물건들의 평균 가격 변동", "analogy": "장바구니 물가 성적표", "signal": "🔴 3% 이상 상승 시 인플레 우려", "mts": "해외 경제 지표 ➔ 미국 CPI"}, "economy": {"title": "무역수지", "concept": "수출액과 수입액의 차이", "impact": "적자가 지속되면 환율이 올라요."}, "quiz": {"q": "무역수지 흑자란?", "opts": ["수출이 수입보다 많음", "수입이 많음"], "ans": 0, "exp": "벌어들인 외화가 더 많다는 뜻입니다."}},
            {"stock": {"term": "시가총액", "concept": "기업의 총 덩치(가격)", "analogy": "주식 수 x 현재 주가", "signal": "🟢 덩치가 클수록 안정적", "mts": "종목 검색 ➔ 기본정보"}, "economy": {"title": "스태그플레이션", "concept": "불경기인데 물가도 오르는 현상", "impact": "서민 경제에 가장 부담이 큽니다."}, "quiz": {"q": "시가총액 계산법은?", "opts": ["주가 × 발행주식수", "매출액 × 자산"], "ans": 0, "exp": "기업의 전체 가치를 나타내는 척도입니다."}}
        ],
        "daily_sets": [
            {
                "pattern": "Can I get ~ ? (~ 좀 주시겠어요?)",
                "words": [
                    {"word": "Water (물)", "example": "Can I get water?", "meaning": "물 좀 주시겠어요?"},
                    {"word": "Coffee (커피)", "example": "Can I get coffee?", "meaning": "커피 좀 주시겠어요?"},
                    {"word": "The bill (계산서)", "example": "Can I get the bill?", "meaning": "계산서 좀 주시겠어요?"}
                ],
                "quote": {"en": "Stay hungry, stay foolish.", "ko": "늘 갈망하고 우직하게 나아가라.", "author": "Steve Jobs"},
                "question": {"q": "How are you today?", "hint": "I am good! 또는 I am tired. 라고 대답해보세요."}
            },
            {
                "pattern": "I want to ~ (~하고 싶어요)",
                "words": [
                    {"word": "Go home (집에 가다)", "example": "I want to go home.", "meaning": "집에 가고 싶어요."},
                    {"word": "Drink water (물을 마시다)", "example": "I want to drink water.", "meaning": "물 마시고 싶어요."},
                    {"word": "Buy this (이걸 사다)", "example": "I want to buy this.", "meaning": "이것을 사고 싶어요."}
                ],
                "quote": {"en": "Change your thoughts and you change your world.", "ko": "생각을 바꾸면 세상이 바뀐다.", "author": "Norman Vincent Peale"},
                "question": {"q": "What do you want to eat today?", "hint": "I want to eat pizza! 라고 문장으로 말해보세요."}
            }
        ]
    }

def get_ai_summaries(title, snippet):
    if not model:
