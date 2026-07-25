import os
import json
import feedparser
import time
from difflib import SequenceMatcher
import re

# 1. RSS 피드 정의
RSS_FEEDS = {
    "1면/종합": ["https://www.mk.co.kr/rss/30000001/", "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml"],
    "신문 사설": ["https://www.khan.co.kr/rss/rssdata/opinion.xml", "https://rss.hankyung.com/feed/opinion.xml"],
    "글로벌/해외이슈": ["https://feeds.a.dj.com/rss/RSSWorldNews.xml", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"],
    "해외 테크/AI": ["https://techcrunch.com/feed/", "https://www.theverge.com/rss/index.xml"],
    "경제/정책": ["https://www.mk.co.kr/rss/30100041/", "https://rss.hankyung.com/feed/economy.xml"],
    "금융/증권": ["https://www.mk.co.kr/rss/50200011/", "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"],
    "산업/기업": ["https://www.mk.co.kr/rss/50100032/", "https://rss.hankyung.com/feed/industry.xml"],
    "부동산": ["https://www.mk.co.kr/rss/50300009/", "https://rss.hankyung.com/feed/land.xml"],
    "IT/과학/Bio": ["https://www.mk.co.kr/rss/50700001/", "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/it.xml"]
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

def get_fallback_learning():
    """자바스크립트 엔진과 100% 매칭되는 검증된 5세트 핵심 데이터"""
    return {
        "finance_sets": [
            {"stock": {"term": "PER", "concept": "버는 돈 대비 주가 수준", "analogy": "1년 이익 대비 가게 매매가 비율", "signal": "🟢 10배 이하 저평가", "mts": "종목검색 -> 기업정보"}, "economy": {"title": "기준금리", "concept": "금리의 기준점", "impact": "대출 및 예금 이자 영향"}, "quiz": {"q": "PER이 낮으면 어떤 상태일까요?", "opts": ["저평가 상태", "고평가 상태"], "ans": 0, "exp": "이익 대비 주가가 싼 상태입니다."}},
            {"stock": {"term": "PBR", "concept": "가진 재산 대비 주가 수준", "analogy": "가게 장비 다 판 값과 주가의 비교", "signal": "🟢 1배 미만 저평가", "mts": "종목검색 -> 재무지표"}, "economy": {"title": "환율", "concept": "외국 돈과의 교환 비율", "impact": "수출입 물가 영향"}, "quiz": {"q": "PBR이 1배 미만이라는 의미는?", "opts": ["재산보다 주가가 저렴함", "비쌈"], "ans": 0, "exp": "재산 가치보다 주가가 낮은 상태입니다."}},
            {"stock": {"term": "ROE", "concept": "투자한 돈으로 얼마나 버는가", "analogy": "자본금 대비 연간 순이익 비율", "signal": "🟢 10% 이상 우수", "mts": "기업분석 -> 투자지표"}, "economy": {"title": "인플레이션", "concept": "물가가 지속적으로 오르는 현상", "impact": "화폐 가치가 떨어져요."}, "quiz": {"q": "ROE가 높을수록 어떤 기업일까요?", "opts": ["경영 효율이 좋은 기업", "돈을 못 버는 기업"], "ans": 0, "exp": "자본 대비 돈을 효율적으로 잘 번다는 뜻입니다."}},
            {"stock": {"term": "CPI", "concept": "소비자 물가 변동 지수", "analogy": "장바구니 물가 성적표", "signal": "🔴 3% 이상 상승 시 인플레 우려", "mts": "해외 경제 지표 -> 미국 CPI"}, "economy": {"title": "무역수지", "concept": "수출액과 수입액의 차이", "impact": "적자가 지속되면 환율이 올라요."}, "quiz": {"q": "무역수지 흑자는 어떤 상황일까요?", "opts": ["수출이 수입보다 많음", "수입이 많음"], "ans": 0, "exp": "벌어들인 외화가 더 많은 상태입니다."}},
            {"stock": {"term": "시가총액", "concept": "기업의 총 가치 크기", "analogy": "주식 수 x 현재 주가", "signal": "🟢 덩치가 클수록 안정적", "mts": "종목 검색 -> 기본정보"}, "economy": {"title": "스태그플레이션", "concept": "불경기인데 물가도 오르는 현상", "impact": "서민 경제에 가장 부담이 큽니다."}, "quiz": {"q": "시가총액은 어떻게 계산하나요?", "opts": ["주가와 발행주식수를 곱함", "매출액과 자산을 곱함"], "ans": 0, "exp": "현재 주가에 발행된 총 주식 수를 곱합니다."}}
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
                "quote": {"en": "Change your thoughts and you change your world.", "ko": "생각을 바꾸면 세상이 바뀐다.", "author": "Norman Peale"},
                "question": {"q": "What do you want to eat today?", "hint": "I want to eat pizza! 라고 문장으로 말해보세요."}
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
                    {"word": "Everything (모든 것)", "example": "Thank you for everything.", "meaning": "모든 것에 감사드립니다."}
                ],
                "quote": {"en": "Happiness depends upon ourselves.", "ko": "행복은 우리 자신에게 달려 있다.", "author": "Aristotle"},
                "question": {"q": "Who are you thankful for?", "hint": "My family. 또는 My friend. 라고 툭 뱉어보세요."}
            },
            {
                "pattern": "It is too ~ (너무 ~해요)",
                "words": [
                    {"word": "Hot (더운)", "example": "It is too hot.", "meaning": "날씨가 너무 더워요."},
                    {"word": "Cold (추운)", "example": "It is too cold.", "meaning": "날씨가 너무 추워요."},
                    {"word": "Expensive (비싼)", "example": "It is too expensive.", "meaning": "이거 너무 비싸요."}
                ],
                "quote": {"en": "Don't count the days, make the days count.", "ko": "날짜를 세지 말고, 하루하루를 의미 있게 보내라.", "author": "Muhammad Ali"},
                "question": {"q": "How is the weather today?", "hint": "It is hot! 또는 It is nice. 라고 답해보세요."}
            }
        ]
    }

def fetch_and_process():
    learning_data = get_fallback_learning()
    processed_articles = {}
    
    for category, urls in RSS_FEEDS.items():
        processed_articles[category] = []
        titles = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:4]:
                    if is_duplicate(entry.title, titles): 
                        continue
                    titles.append(entry.title)
                    
                    pub_date = entry.get('published_parsed', time.localtime())
                    iso_date = time.strftime('%Y-%m-%dT%H:%M:%S', pub_date)
                    
                    # 기사 한 줄 요약 및 상세 내용 기본 연동
                    processed_articles[category].append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": "클릭 시 언론사 원문 기사 페이지로 바로 이동합니다.",
                        "detail": ["-", "-", "-"],
                        "date": iso_date
                    })
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"learning": learning_data, "articles": processed_articles}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()
