import os
import json
import feedparser
import time
from datetime import datetime
from difflib import SequenceMatcher
import re

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
    avoid_terms = ", ".join(history["used_terms"][-20:])
    avoid_patterns = ", ".join(history["used_patterns"][-20:])

    if not model:
        return get_fallback_learning()

    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        Today is {today_str}. Generate 5 finance sets and 5 daily English sets for beginners.
        Output ONLY valid JSON string without markdown or commentary.

        Avoid using:
        - Terms: [{avoid_terms}]
        - Patterns: [{avoid_patterns}]

        [JSON Format]:
        {{
          "finance_sets": [
            {{
              "stock": {{"term": "PER", "concept": "이익 대비 주가 수준", "analogy": "가게 매매가 비율", "signal": "🟢 저평가", "mts": "종목검색➔기업정보"}},
              "economy": {{"title": "기준금리", "concept": "이자의 기준점", "impact": "대출이자 변동"}},
              "quiz": {{"q": "PER이란?", "opts": ["이익대비 주가", "매출대비 주가"], "ans": 0, "exp": "이익과 주가의 비율입니다."}}
            }}
          ],
          "daily_sets": [
            {{
              "pattern": "Can I get ~ ?",
              "words": [
                {{"word": "Water", "example": "Can I get water?", "meaning": "물 좀 주시겠어요?"}},
                {{"word": "Coffee", "example": "Can I get coffee?", "meaning": "커피 좀 주시겠어요?"}},
                {{"word": "The bill", "example": "Can I get the bill?", "meaning": "계산서 주시겠어요?"}},
                {{"word": "A menu", "example": "Can I get a menu?", "meaning": "메뉴판 주시겠어요?"}},
                {{"word": "Some ice", "example": "Can I get some ice?", "meaning": "얼음 좀 주시겠어요?"}}
              ],
              "quote": {{"en": "Stay hungry, stay foolish.", "ko": "늘 갈망하고 우직하게 나아가라.", "author": "Steve Jobs"}},
              "questions": [
                {{"q": "How are you doing today?", "answers": ["Not too bad, just chilling. (쉬는 중이야)", "Pretty good! (완전 좋아!)"]}},
                {{"q": "What are you up to this weekend?", "answers": ["Nothing much. (별거 없어)", "Hanging out with family! (가족과 노는 중!)"]}}
              ]
            }}
          ]
        }}
        Provide exactly 5 unique finance_sets and 5 unique daily_sets.
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group())
            
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
    # 백업 데이터도 5개로 풍부하게 구성하여 API 실패 시에도 [다른 내용 보기]가 계속 작동함
    return {
        "finance_sets": [
            {"stock": {"term": "PER", "concept": "버는 돈 대비 주가 수준", "analogy": "1년 이익 대비 가게 매매가 비율", "signal": "🟢 10배 이하 저평가", "mts": "종목검색 -> 기업정보"}, "economy": {"title": "기준금리", "concept": "금리의 기준점", "impact": "대출 및 예금 이자 영향"}, "quiz": {"q": "PER이 낮으면 어떤 상태일까요?", "opts": ["저평가 상태", "고평가 상태"], "ans": 0, "exp": "이익 대비 주가가 싼 상태입니다."}},
            {"stock": {"term": "PBR", "concept": "가진 재산 대비 주가 수준", "analogy": "가게 장비 다 판 값과 주가의 비교", "signal": "🟢 1배 미만 저평가", "mts": "종목검색 -> 재무지표"}, "economy": {"title": "환율", "concept": "외국 돈과의 교환 비율", "impact": "수출입 물가 영향"}, "quiz": {"q": "PBR이 1배 미만이라는 의미는?", "opts": ["장부상 재산보다 주가가 저렴함", "비쌈"], "ans": 0, "exp": "재산 가치보다 주가가 낮은 상태입니다."}},
            {"stock": {"term": "ROE", "concept": "투자한 돈으로 얼마나 버는가", "analogy": "자본금 대비 연간 순이익 비율", "signal": "🟢 10% 이상 우수", "mts": "기업분석 -> 투자지표"}, "economy": {"title": "인플레이션", "concept": "물가가 지속적으로 오르는 현상", "impact": "화폐 가치가 떨어져요."}, "quiz": {"q": "ROE가 높을수록 어떤 기업일까요?", "opts": ["경영 효율이 좋은 기업", "돈을 못 버는 기업"], "ans": 0, "exp": "투입한 자본 대비 돈을 효율적으로 잘 번다는 의미입니다."}},
            {"stock": {"term": "CPI", "concept": "소비자가 사는 물건들의 평균 가격 변동", "analogy": "장바구니 물가 성적표", "signal": "🔴 3% 이상 상승 시 인플레 우려", "mts": "해외 경제 지표 -> 미국 CPI"}, "economy": {"title": "무역수지", "concept": "수출액과 수입액의 차이", "impact": "적자가 지속되면 환율이 올라요."}, "quiz": {"q": "무역수지 흑자는 어떤 상황을 뜻할까요?", "opts": ["수출이 수입보다 많음", "수입이 수출보다 많음"], "ans": 0, "exp": "벌어들인 외화가 수입으로 나간 돈보다 많은 유익한 상태입니다."}},
            {"stock": {"term": "시가총액", "concept": "기업의 총 덩치와 가격", "analogy": "주식 수와 현재 주가를 곱한 값", "signal": "🟢 덩치가 클수록 안정적", "mts": "종목 검색 -> 기본정보"}, "economy": {"title": "스태그플레이션", "concept": "불경기인데 물가도 오르는 현상", "impact": "서민 경제에 가장 부담이 큽니다."}, "quiz": {"q": "시가총액은 어떻게 계산하나요?", "opts": ["주가와 발행주식수를 곱함", "매출액과 자산을 곱함"], "ans": 0, "exp": "현재 주가에 발행된 총 주식 수를 곱해 산출합니다."}}
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
            },
            {
                "pattern": "I want to ~ (~하고 싶어요)",
                "words": [
                    {"word": "Go home (집에 가다)", "example": "I want to go home.", "meaning": "집에 가고 싶어요."},
                    {"word": "Drink water (물을 마시다)", "example": "I want to drink water.", "meaning": "물 마시고 싶어요."},
                    {"word": "Buy this (이걸 사다)", "example": "I want to buy this.", "meaning": "이것을 사고 싶어요."},
                    {"word": "Take a rest (쉬다)", "example": "I want to take a rest.", "meaning": "좀 쉬고 싶어요."},
                    {"word": "Learn English (영어 공부하다)", "example": "I want to learn English.", "meaning": "영어 공부하고 싶어요."}
                ],
                "quote": {"en": "Change your thoughts and you change your world.", "ko": "생각을 바꾸면 세상이 바뀐다.", "author": "Norman Vincent Peale"},
                "questions": [
                    {"q": "What do you feel like eating today?", "answers": ["I'm in the mood for something spicy! (오늘 매콤한 게 땡기네!)", "A burger sounds good to me. (버거나 하나 먹을까 해)"]},
                    {"q": "Where do you want to travel next?", "answers": ["I'd love to go somewhere sunny! (햇살 좋은 따뜻한 곳으로 가고 싶어!)", "Anywhere with a nice beach! (멋진 해변이 있는 곳이라면 어디든!)"]}
                ]
            },
            {
                "pattern": "Could you tell me ~ ? (~를 알려주시겠어요?)",
                "words": [
                    {"word": "The way (길)", "example": "Could you tell me the way?", "meaning": "길을 알려주시겠어요?"},
                    {"word": "Your name (이름)", "example": "Could you tell me your name?", "meaning": "성함을 알려주시겠어요?"},
                    {"word": "The price (가격)", "example": "Could you tell me the price?", "meaning": "가격을 알려주시겠어요?"},
                    {"word": "The time (시간)", "example": "Could you tell me the time?", "meaning": "몇 시인지 알려주시겠어요?"},
                    {"word": "The answer (정답)", "example": "Could you tell me the answer?", "meaning": "정답을 알려주시겠어요?"}
                ],
                "quote": {"en": "Action is the foundational key to all success.", "ko": "행동은 모든 성공의 가장 기본적인 열쇠다.", "author": "Pablo Picasso"},
                "questions": [
                    {"q": "Could you tell me where the bathroom is?", "answers": ["It's right around the corner. (바로 모퉁이 돌면 있어요)", "Go straight and it's on your left. (직진하시면 왼쪽에 있어요)"]},
                    {"q": "Could you tell me what time it is?", "answers": ["It's almost 3 PM. (3시 다 되어가요)", "Sorry, I don't have a watch on me. (죄송해요, 시계가 없네요)"]}
                ]
            },
            {
                "pattern": "How about ~ ? (~하는 건 어때요?)",
                "words": [
                    {"word": "Lunch (점심 식사)", "example": "How about lunch?", "meaning": "점심 먹는 건 어때요?"},
                    {"word": "Going out (외출하기)", "example": "How about going out?", "meaning": "밖에 나가는 건 어때요?"},
                    {"word": "A cup of tea (차 한 잔)", "example": "How about a cup of tea?", "meaning": "차 한 잔 어때요?"},
                    {"word": "Taking a break (휴식 취하기)", "example": "How about taking a break?", "meaning": "잠시 쉬는 건 어때요?"},
                    {"word": "This one (이것)", "example": "How about this one?", "meaning": "이건 어때요?"}
                ],
                "quote": {"en": "The secret of getting ahead is getting started.", "ko": "앞서 나가는 비결은 바로 시작하는 것이다.", "author": "Mark Twain"},
                "questions": [
                    {"q": "How about grabbing a coffee after work?", "answers": ["Sounds like a plan! (좋아요, 그러죠!)", "I'd love to, but I have plans tonight. (그러고 싶은데 오늘 약속이 있어요)"]},
                    {"q": "How about watching a movie tonight?", "answers": ["I'm down for that! (나 완전 좋아!)", "Maybe next time, I'm super tired. (다음 기회에, 나 너무 피곤해)"]}
                ]
            },
            {
                "pattern": "I'm looking for ~ (~를 찾고 있어요)",
                "words": [
                    {"word": "The subway (지하철역)", "example": "I'm looking for the subway.", "meaning": "지하철역을 찾고 있어요."},
                    {"word": "My phone (내 핸드폰)", "example": "I'm looking for my phone.", "meaning": "핸드폰을 찾고 있어요."},
                    {"word": "A souvenir (기념품)", "example": "I'm looking for a souvenir.", "meaning": "기념품을 찾고 있어요."},
                    {"word": "A pharmacy (약국)", "example": "I'm looking for a pharmacy.", "meaning": "약국을 찾고 있어요."},
                    {"word": "My hotel (내 숙소)", "example": "I'm looking for my hotel.", "meaning": "제 숙소를 찾고 있어요."}
                ],
                "quote": {"en": "It always seems impossible until it's done.", "ko": "완성되기 전까지는 항상 불가능해 보인다.", "author": "Nelson Mandela"},
                "questions": [
                    {"q": "Are you looking for anything in particular?", "answers": ["Just browsing, thanks! (그냥 구경 중이에요, 감사해요!)", "Yes, I'm looking for a gift. (네, 선물용을 찾고 있어요)"]},
                    {"q": "What kind of place are you looking for?", "answers": ["A cozy place to work on my laptop. (노트북 하기 편하고 아늑한 곳이요)", "Somewhere with good food! (맛있는 음식 있는 곳이요!)"]}
                ]
            }
        ]
    }

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
