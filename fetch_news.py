import os
import json
import feedparser
import google.generativeai as genai
import time
from difflib import SequenceMatcher
import re

# 1. Gemini 설정
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

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
    """새로고침 기능을 위해 금융 5세트 + 왕초보 패턴 영어 5세트 데이터 생성"""
    try:
        prompt = """
        초보자를 위한 금융/주식 학습 세트 5개와 왕초보용 일상 영어 표현 세트 5개를 생성해줘.
        반드시 다음 JSON 규격을 엄격하게 지켜서 정확한 JSON 텍스트만 반환해줘.

        [영어 세트 구성 조건]:
        1. 영단어는 중학교 수준의 완전히 기초적인 일상 생활 필수 단어(예: Water, Coffee, Time, Happy 등) 3개로 구성할 것.
        2. 'pattern'은 일상생활이나 해외여행에서 가장 자주 쓰는 초보자용 만능 회화 뼈대 문장(예: Can I get ~?, I want to ~?, Where is ~?) 1개를 선정할 것.
        3. 3개의 기초 단어가 이 만능 패턴 안에 대입되어 바로 써먹을 수 있는 아주 짧고 실용적인 일상 대화 문장 예시를 만들 것.
        4. 'question'은 왕초보가 단어 하나로라도 툭 뱉어 답할 수 있는 매우 쉽고 간단한 AI의 1줄 일상 질문과 예시 답변 힌트를 제공할 것.

        [출력 JSON 양식]:
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
              "question": {"q": "How are you today?", "hint": "I am good! 또는 I am tired. 라고 소리내어 대답해보세요."}
            }
          ]
        }
        finance_sets와 daily_sets 항목을 각각 서로 다른 내용으로 정확히 5개씩 채워줘.
        """
        response = model.generate_content(prompt)
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Learning Gen Error: {e}")
        
    # 예외 발생 시 폴백 데이터 (구조 보장)
    return {
        "finance_sets": [{
            "stock": {"term": "PER", "concept": "버는 돈 대비 주가 수준", "analogy": "1년 이익 대비 가게 매매가 비율", "signal": "🟢 10배 이하 저평가", "mts": "종목검색 ➔ 기업정보"},
            "economy": {"title": "기준금리", "concept": "금리의 기준점", "impact": "대출 및 예금 이자 영향"},
            "quiz": {"q": "PER이 낮으면?", "opts": ["저평가", "고평가"], "ans": 0, "exp": "이익 대비 주가가 싼 상태입니다."}
        }],
        "daily_sets": [{
            "pattern": "Can I get ~ ? (~ 좀 주시겠어요?)",
            "words": [
                {"word": "Water (물)", "example": "Can I get water?", "meaning": "물 좀 주시겠어요?"},
                {"word": "Coffee (커피)", "example": "Can I get coffee?", "meaning": "커피 좀 주시겠어요?"},
                {"word": "The bill (계산서)", "example": "Can I get the bill?", "meaning": "계산서 좀 주시겠어요?"}
            ],
            "quote": {"en": "Stay hungry, stay foolish.", "ko": "늘 갈망하고 우직하게 나아가라.", "author": "Steve Jobs"},
            "question": {"q": "How are you today?", "hint": "I am good! 이라고 답변해보세요."}
        }]
    }

def get_ai_summaries(title, snippet):
    try:
        prompt = f"제목:{title}\n내용:{snippet}\n위 기사를 한국어로 1줄 요약과 3줄 상세 내용을 작성해줘.\n양식:\n1줄: [내용]\n3줄:\n- [내용]\n- [내용]\n- [내용]"
        response = model.generate_content(prompt)
        lines = response.text.strip().split('\n')
        one = lines[0].replace('1줄:', '').strip()
        three = [l.strip() for l in lines if l.strip().startswith('-')]
        return one
