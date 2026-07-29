import os
import json
import feedparser
import time
from datetime import datetime
from difflib import SequenceMatcher
import re
import random

try:
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        model = None
except Exception as e:
    print(f"Gemini Init Error: {e}")
    model = None

RSS_FEEDS = {
    "1면/종합": ["https://www.mk.co.kr/rss/30000001/", "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml", "https://www.chosun.com/arc/outboundfeeds/rss/category/politics/?outputType=xml", "https://www.khan.co.kr/rss/rssdata/total_news.xml"],
    "신문 사설": ["https://rss.donga.com/editorials.xml", "https://www.mk.co.kr/rss/30000023/", "https://www.hani.co.kr/rss/editorial/"],
    "글로벌/해외이슈": ["https://feeds.a.dj.com/rss/RSSWorldNews.xml", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://feeds.bbci.co.uk/news/world/rss.xml"],
    "해외 테크/AI": ["https://techcrunch.com/feed/", "https://www.theverge.com/rss/index.xml"],
    "경제/정책": ["https://www.mk.co.kr/rss/30100041/", "https://rss.hankyung.com/feed/economy.xml", "https://www.sedaily.com/Rss/Economy"],
    "금융/증권": ["https://www.mk.co.kr/rss/50200011/", "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "https://www.sedaily.com/Rss/Stock"],
    "산업/기업": ["https://www.mk.co.kr/rss/50100032/", "https://rss.hankyung.com/feed/industry.xml", "https://www.sedaily.com/Rss/Industry"],
    "부동산": ["https://www.mk.co.kr/rss/50300009/", "https://rss.hankyung.com/feed/land.xml", "https://www.sedaily.com/Rss/Realestate"],
    "IT/과학/Bio": ["https://www.mk.co.kr/rss/50700001/", "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/it.xml", "https://zdnet.co.kr/rss/all.xml", "https://www.etnews.com/arc/outboundfeeds/rss/category/01/?outputType=xml"],
    "스포츠": ["https://sports.chosun.com/arc/outboundfeeds/rss/all/?outputType=xml", "https://www.chosun.com/arc/outboundfeeds/rss/category/sports/?outputType=xml"],
    "헬스/건강": ["https://kormedi.com/feed/", "https://health.chosun.com/site/data/rss/rss.xml"]
}

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"used_terms": [], "used_patterns": []}

def save_history(history):
    # 최근 150개 까지만 보관하여 무한정 불어나는 것 방지 (약 20일 분량 방어용)
    history["used_terms"] = history["used_terms"][-150:]
    history["used_patterns"] = history["used_patterns"][-150:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def clean_title(title):
    title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    return title.strip()

def is_duplicate(new_title, existing_titles, threshold=0.55):
    clean_new = clean_title(new_title)
    for ext in existing_titles:
        if SequenceMatcher(None, clean_new, clean_title(ext)).ratio() > threshold:
            return True
    return False

def generate_multi_learning():
    history = load_history()
    
    # AI가 피해야 할 최근 리스트 파싱
    avoid_terms = ", ".join(history["used_terms"])
    avoid_patterns = ", ".join(history["used_patterns"])

    if not model:
        return get_fallback_learning()

    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        오늘은 {today_str}이다. 초보자를 위한 금융/주식/경제 학습 세트 10개와 일상 영어 표현 세트 10개를 생성해라.
        
        [중요 지시 - 절대 중복 차단]:
        최근 사용된 아래 목록의 용어와 영어 패턴은 이미 사용자가 공부했으므로 '절대' 다시 출력하지 마라. 완전 새로운 단어로 다채롭게 채워라.
        - 제외할 금융 용어: [{avoid_terms}]
        - 제외할 영어 패턴: [{avoid_patterns}]

        반드시 설명이나 마크다운(```json 등) 없이, 순수 JSON 텍스트 하나만 출력해라.

        [JSON 구조]:
        {{
          "finance_sets": [
            {{
              "stock": {{"term": "용어명", "concept": "3초 개념 설명", "analogy": "쉬운 비유 설명", "signal": "🟢 저평가 판단 신호", "mts": "MTS 메뉴 위치"}},
              "economy": {{"title": "주제명", "concept": "핵심 설명", "impact": "실생활 영향"}},
              "quiz": {{"q": "퀴즈 질문", "opts": ["정답선택지", "오답선택지"], "ans": 0, "exp": "퀴즈 해설"}}
            }}
          ],
          "daily_sets": [
            {{
              "pattern": "오늘의 만능 패턴",
              "words": [
                {{"word": "단어1 (뜻)", "example": "예문1", "meaning": "해석1"}},
                {{"word": "단어2 (뜻)", "example": "예문2", "meaning": "해석2"}},
                {{"word": "단어3 (뜻)", "example": "예문3", "meaning": "해석3"}},
                {{"word": "단어4 (뜻)", "example": "예문4", "meaning": "해석4"}},
                {{"word": "단어5 (뜻)", "example": "예문5", "meaning": "해석5"}}
              ],
              "quote": {{"en": "영문 명언", "ko": "한글 번역", "author": "작성자"}},
              "questions": [
                {{"q": "원어민 질문1", "answers": ["현지인 답변1 (해석)", "현지인 답변2 (해석)"]}},
                {{"q": "원어민 질문2", "answers": ["현지인 답변1 (해석)", "현지인 답변2 (해석)"]}}
              ]
            }}
          ]
        }}
        finance_sets와 daily_sets 각각 정확히 10개씩 서로 겹치지 않는 새로운 내용으로 가득 채워라.
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group())
            
            # 새로 생성된 단어를 역사 노드에 누적 저장
            for s in data.get("finance_sets", []):
                t = s.get("stock", {}).get("term")
                if t and t not in history["used_terms"]: history["used_terms"].append(t)
            for d in data.get("daily_sets", []):
                p = d.get("pattern")
                if p and p not in history["used_patterns"]: history["used_patterns"].append(p)
            
            save_history(history)
            return data
            
    except Exception as e:
        print(f"Gemini API Error: {e}")
        
    return get_fallback_learning()

def get_fallback_learning():
    # 기본 백업 데이터셋
    data = {
        "finance_sets": [
            {"stock": {"term": "PER", "concept": "버는 돈 대비 주가 수준", "analogy": "1년 이익 대비 가게 매매가 비율", "signal": "🟢 10배 이하 저평가", "mts": "종목검색 -> 企业정보"}, "economy": {"title": "기준금리", "concept": "금리의 기준점", "impact": "대출 및 예금 이자 영향"}, "quiz": {"q": "PER이 낮으면 어떤 상태일까요?", "opts": ["저평가 상태", "고평가 상태"], "ans": 0, "exp": "이익 대비 주가가 싼 상태입니다."}}
        ],
        "daily_sets": [
            {
                "pattern": "Can I get ~ ? (~ 좀 주시겠어요?)",
                "words": [
                    {"word": "Water (물)", "example": "Can I get water?", "meaning": "물 좀 주시겠어요?"},
                    {"word": "Coffee (커피)", "example": "Can I get coffee?", "meaning": "커피 좀 주시겠어요?"},
                    {"word": "The bill (계산서)", "example": "Can I get the bill?", "meaning": "계산서 좀 주시겠어요?"},
                    {"word": "A menu (메뉴판)", "example": "Can I get a menu?", "meaning": "메뉴판 좀 주시겠어요?"},
                    {"word": "Some ice (얼음)", "example": "Can I get some ice?", "meaning": "얼음 좀 주시겠어요?"}
                ],
                "quote": {"en": "Stay hungry, stay foolish.", "ko": "늘 갈망하고 우직하게 나아가라.", "author": "Steve Jobs"},
                "questions": [
                    {"q": "How are you doing today?", "answers": ["Not too bad, just chilling. (그럭저럭 괜찮아, 쉬는 중이야)", "Pretty good! Can't complain. (완전 좋아! 더할 나위 없지)"]},
                    {"q": "What are you up to this weekend?", "answers": ["Nothing much, just taking it easy. (별거 없어, 편히 쉬려고)", "I'm hanging out with my family! (가족들이랑 노는 중이야!)"]}
                ]
            }
        ]
    }
    return data

def fetch_and_process():
    learning_data = generate_multi_learning()
    processed_articles = {}
    
    for category, urls in RSS_FEEDS.items():
        processed_articles[category] = []
        titles = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:6]:
                    if is_duplicate(entry.title, titles): 
                        continue
                    titles.append(entry.title)
                    
                    pub_date = entry.get('published_parsed', time.localtime())
                    iso_date = time.strftime('%Y-%m-%dT%H:%M:%S', pub_date)
                    
                    processed_articles[category].append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": "클릭 시 해당 언론사의 뉴스 상세 원문 페이지로 바로 연결됩니다.",
                        "detail": ["-", "-", "-"],
                        "date": iso_date
                    })
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"learning": learning_data, "articles": processed_articles}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()
