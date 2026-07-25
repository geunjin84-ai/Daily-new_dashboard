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
    # 가장 안정적인 모델명으로 설정
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
    """오류 방지를 위해 프롬프트를 직관적으로 수정하고 구조적 안전장치 확보"""
    if not model:
        return get_fallback_learning()

    try:
        # API 오류를 유발할 수 있는 복잡한 스키마 지정을 빼고 자연스러운 프롬프트로 교체
        prompt = """
        초보자를 위한 주식/경제 용어 5세트와 왕초보용 일상 영어 표현 5세트를 만들어줘.
        출력은 마크다운 기호 없이 오직 JSON 데이터 포맷으로만 써줘.

        양식:
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
        내용이 겹치지 않게 총 5개씩 세트를 만들어서 JSON으로 채워줘.
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 마크다운 백틱(```json)이 포함되어 올 경우 제거하는 정규식 필터
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Gemini API 또는 파싱 에러 발생: {e}. 안전 모드로 전환합니다.")
        
    return get_fallback_learning()

def get_fallback_learning():
    """AI 에러 발생 시 대시보드 화면이 멈추지 않도록 보장하는 5세트 기본 백업 데이터"""
    return {
        "finance_sets": [
            {"stock": {"term": "PER", "concept": "버는 돈 대비 주가 수준", "analogy": "1년 이익 대비 가게 매매가 비율", "signal": "🟢 10배 이하 저평가", "mts": "종목검색 ➔ 기업정보"}, "economy": {"title": "기준금리", "concept": "금리의 기준점", "impact": "대출 및 예금 이자 영향"}, "quiz": {"q": "PER이 낮으면?", "opts": ["저평가", "고평가"], "ans": 0, "exp": "이익 대비 주가가 싼 상태입니다."}},
            {"stock": {"term": "PBR", "concept": "가진 재산 대비 주가 수준", "analogy": "가게 장비 다 판 값과 주가의 비교", "signal": "🟢 1배 미만 저평가", "mts": "종목검색 ➔ 재무지표"}, "economy": {"title": "환율", "concept": "외국 돈과의 교환 비율", "impact": "수출입 물가 영향"}, "quiz": {"q": "PBR 1배 미만은?", "opts": ["저평가", "고평가"], "ans": 0, "exp": "재산 가치보다 주가가 낮습니다."}},
            {"stock": {"term": "ROE", "concept": "투자한 돈으로 얼마나 버는가", "analogy": "자본금 대비 연간 순이익 비율", "signal": "🟢 10% 이상 우수", "mts": "기업분석 ➔ 투자지표"}, "economy": {"title": "인플레이션", "concept": "물가가 지속적으로 오르는 현상", "impact": "화폐 가치가 떨어져요."}, "quiz": {"q": "ROE가 높으면?", "opts": ["경영 효율이 좋음", "나쁨"], "ans": 0, "exp": "투입한 자본 대비 돈을 잘 번다는 뜻입니다."}},
            {"stock": {"term": "원자재 가격", "concept": "석유, 구리 등 기초 자재 값", "analogy": "제품을 만들기 위한 원가 재료비", "signal": "🔴 상승 시 기업 비용 증가", "mts": "해외시장 ➔ 원자재"}, "economy": {"title": "무역수지", "concept": "수출액과 수입액의 차이", "impact": "적자가 지속되면 환율이 올라요."}, "quiz": {"q": "무역수지 흑자란?", "opts": ["수출이 수입보다 많음", "수입이 많음"], "ans": 0, "exp": "벌어들인 외화가 더 많다는 뜻입니다."}},
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
                "question": {"q": "What do you want to eat today?", "hint": "I want to eat pizza! 처럼 단어나 문장으로 말해보세요."}
            },
            {
                "pattern": "Where is the ~ ? (~은 어디에 있나요?)",
                "words": [
                    {"word": "Restroom (화장실)", "example": "Where is the restroom?", "meaning": "화장실이 어디인가요?"},
                    {"word": "Station (역)", "example": "Where is the station?", "meaning": "역이 어디인가요?"},
                    {"word": "Hotel (호텔)", "example": "Where is the hotel?", "meaning": "호텔이 어디인가요?"}
                ],
                "quote": {"en": "Success is not final, failure is not fatal.", "ko": "성공은 영원하지 않고, 실패는 치명적이지 않다.", "author": "Winston Churchill"},
                "question": {"q": "Where are you now?", "hint": "I am at home. 또는 Office. 라고 답해보세요."}
            },
            {
                "pattern": "Thank you for ~ (~해 주셔서 감사합니다)",
                "words": [
                    {"word": "The help (도움)", "example": "Thank you for the help.", "meaning": "도와주셔서 감사합니다."},
                    {"word": "The food (음식)", "example": "Thank you for the food.", "meaning": "음식 잘 먹었습니다."},
                    {"word": "Everything (모든 것)", "example": "Thank you for everything.", "meaning": " 모든 것에 감사드립니다."}
                ],
                "quote": {"en": "Happiness depends upon ourselves.", "ko": "행복은 우리 자신에게 달려 있다.", "author": "Aristotle"},
                "question": {"q": "Who are you thankful for?", "hint": "My family. 또는 My friend. 처럼 툭 뱉어보세요."}
            },
            {
                "pattern": "It is too ~ (너무 ~해요)",
                "words": [
                    {"word": "Hot (더운)", "example": "It is too hot.", "meaning": "날씨가 너무 더워요."},
                    {"word": "Cold (추운)", "example": "날씨가 너무 추워요.", "meaning": "It is too cold."},
                    {"word": "Expensive (비싼)", "example": "It is too expensive.", "meaning": "이거 너무 비싸요."}
                ],
                "quote": {"en": "Don't count the days, make the days count.", "ko": "날짜를 세지 말고, 하루하루를 의미 있게 보내라.", "author": "Muhammad Ali"},
                "question": {"q": "How is the weather today?", "hint": "It is hot! 또는 It is nice. 라고 답해보세요."}
            }
        ]
    }

def get_ai_summaries(title, snippet):
    if not model:
        return title[:30], [title, "-", "-"]
    try:
        prompt = f"제목:{title}\n내용:{snippet}\n위 기사를 한국어로 1줄 요약과 3줄 상세 내용을 작성해줘.\n양식:\n1줄: [내용]\n3줄:\n- [내용]\n- [내용]\n- [내용]"
        response = model.generate_content(prompt)
        lines = response.text.strip().split('\n')
        one = lines[0].replace('1줄:', '').strip()
        three = [l.strip() for l in lines if l.strip().startswith('-')]
        return one, three[:3]
    except Exception as e:
        print(f"Summary Error: {e}")
        return title[:30], ["정보를 불러오지 못했습니다.", "-", "-"]

def fetch_and_process():
    learning_data = generate_multi_learning()
    processed_articles = {}
    
    for category, urls in RSS_FEEDS.items():
        processed_articles[category] = []
        titles = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:8]:
                    if is_duplicate(entry.title, titles): 
                        continue
                    titles.append(entry.title)
                    s1, s3 = get_ai_summaries(entry.title, getattr(entry, 'summary', ''))
                    
                    pub_date = entry.get('published_parsed', time.localtime())
                    iso_date = time.strftime('%Y-%m-%dT%H:%M:%S', pub_date)
                    
                    processed_articles[category].append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": s1,
                        "detail": s3,
                        "date": iso_date
                    })
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"learning": learning_data, "articles": processed_articles}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()
