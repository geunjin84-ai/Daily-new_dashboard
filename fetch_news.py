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
    """새로고침 기능을 위해 금융 5세트 + 왕초보용 일상 영어 표현 세트 5개 생성"""
    if not model:
        return get_fallback_learning()

    try:
        prompt = """
        초보자를 위한 금융/주식 학습 세트 5개와 왕초보용 일상 영어 표현 세트 5개를 생성해줘.
        반드시 다음 JSON 규격을 엄격하게 지켜서 순수 JSON 텍스트만 반환해줘.

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
        
    return get_fallback_learning()

def get_fallback_learning():
    return {
        "finance_sets": [
            {"stock": {"term": "PER", "concept": "버는 돈 대비 주가 수준", "analogy": "1년 이익 대비 가게 매매가 비율", "signal": "🟢 10배 이하 저평가", "mts": "종목검색 ➔ 기업정보"}, "economy": {"title": "기준금리", "concept": "금리의 기준점", "impact": "대출 및 예금 이자 영향"}, "quiz": {"q": "PER이 낮으면?", "opts": ["저평가", "고평가"], "ans": 0, "exp": "이익 대비 주가가 싼 상태입니다."}},
            {"stock": {"term": "PBR", "concept": "가진 재산 대비 주가 수준", "analogy": "가게 장비 다 판 값과 주가의 비교", "signal": "🟢 1배 미만 저평가", "mts": "종목검색 ➔ 재무지표"}, "economy": {"title": "환율", "concept": "외국 돈과의 교환 비율", "impact": "수출입 물가 및 해외주식 영향"}, "quiz": {"q": "PBR 1배 미만은?", "opts": ["재산 가치보다 주가가 쌈", "비쌈"], "ans": 0, "exp": "청산 가치보다 주가가 낮습니다."}}
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
                "question": {"q": "How are you today?", "hint": "I am good! 이라고 답변해보세요."}
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
