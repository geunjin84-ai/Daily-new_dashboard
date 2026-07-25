import os
import json
import feedparser
import google.generativeai as genai
from datetime import datetime
import time
from difflib import SequenceMatcher
import re

# 1. Gemini 설정
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. RSS 피드 정의 (사설 섹션 추가)
RSS_FEEDS = {
    "1면/종합": [
        "https://www.mk.co.kr/rss/30000001/",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml"
    ],
    "신문 사설": [
        "https://www.khan.co.kr/rss/rssdata/opinion.xml",  # 경향 사설/칼럼
        "https://rss.donga.com/editorial.xml",           # 동아 사설
        "https://rss.hankyung.com/feed/opinion.xml"      # 한경 오피니언
    ],
    "글로벌/해외이슈": [
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml"
    ],
    "해외 테크/AI": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml"
    ],
    "정치/외교": [
        "https://www.mk.co.kr/rss/30200030/",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/politics.xml"
    ],
    "경제/정책": [
        "https://www.mk.co.kr/rss/30100041/",
        "https://rss.hankyung.com/feed/economy.xml"
    ],
    "금융/증권": [
        "https://www.mk.co.kr/rss/50200011/",
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"
    ],
    "산업/기업": [
        "https://www.mk.co.kr/rss/50100032/",
        "https://rss.hankyung.com/feed/industry.xml"
    ],
    "부동산": [
        "https://www.mk.co.kr/rss/50300009/",
        "https://rss.hankyung.com/feed/land.xml"
    ],
    "IT/과학/Bio": [
        "https://www.mk.co.kr/rss/50700001/",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/it.xml"
    ],
    "연예/스타": [
        "https://rss.donga.com/entertainment.xml",
        "https://www.mk.co.kr/rss/30000023/"
    ],
    "문화/예술": [
        "https://www.mk.co.kr/rss/70000001/",
        "https://rss.donga.com/culture.xml"
    ],
    "교육/입시": [
        "https://rss.hankyung.com/feed/society.xml",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/society.xml"
    ]
}

def clean_title(title):
    title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    return title.strip()

def is_duplicate(new_title, existing_titles, threshold=0.65):
    clean_new = clean_title(new_title)
    for ext in existing_titles:
        clean_ext = clean_title(ext)
        ratio = SequenceMatcher(None, clean_new, clean_ext).ratio()
        if ratio > threshold:
            return True
        words_new = set([w for w in clean_new.split() if len(w) > 1])
        words_ext = set([w for w in clean_ext.split() if len(w) > 1])
        if len(words_new.intersection(words_ext)) >= 3:
            return True
    return False

def generate_daily_learning():
    """매일 실용 영단어 3개와 명언 1개 자동 생성"""
    try:
        prompt = """
        매일 읽기 좋은 실용 비즈니스/시사 영단어 3개와 동기부여 명언 1개를 생성해줘.
        
        [출력 JSON 양식 (반드시 JSON 형식으로만 응답할 것)]:
        {
          "words": [
            {"word": "Resilience", "meaning": "회복력, 탄력성", "example": "Resilience is key to overcoming hardship."},
            {"word": "Innovative", "meaning": "혁신적인", "example": "We need innovative ideas for this project."},
            {"word": "Benchmark", "meaning": "기준, 벤치마크", "example": "They set a new benchmark for quality."}
          ],
          "quote": {
            "english": "The only way to do great work is to love what you do.",
            "korean": "위대한 일을 하는 유일한 방법은 당신이 하는 일을 사랑하는 것이다.",
            "author": "Steve Jobs"
          }
        }
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        # JSON 부분만 추출
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Daily Learning Gen Error: {e}")
        
    return {
        "words": [
            {"word": "Perspective", "meaning": "관점, 시각", "example": "Try to see it from a different perspective."},
            {"word": "Strategy", "meaning": "전략", "example": "We need a clear strategy for growth."},
            {"word": "Insight", "meaning": "통찰력", "example": "The report provides valuable market insights."}
        ],
        "quote": {
          "english": "Success is not final, failure is not fatal: it is the courage to continue that counts.",
          "korean": "성공이 끝이 아니며, 실패가 치명적인 것도 아니다. 중요한 것은 계속해 나가는 용기다.",
          "author": "Winston Churchill"
        }
    }

def get_ai_summaries(title, snippet):
    try:
        prompt = f"""
        기사 제목: {title}
        기사 내용: {snippet}
        
        [지침]
        1. 영문 기사는 자연스러운 한국어로 번역하여 요약해줘.
        2. 사설이나 칼럼인 경우 주장의 핵심 요지를 명확히 짚어줘.
        
        [출력 양식]
        제목번역: [한국어로 번역된 기사 제목]
        1줄: [30자 이내의 핵심 1줄 요약]
        3줄:
        - [상세 핵심 내용 1]
        - [상세 핵심 내용 2]
        - [상세 핵심 내용 3]
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        lines = text.split('\n')
        translated_title = title
        one_line = ""
        three_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("제목번역:"):
                translated_title = line.replace("제목번역:", "").strip()
            elif line.startswith("1줄:"):
                one_line = line.replace("1줄:", "").strip()
            elif line.startswith("-"):
                three_lines.append(line)
                
        if not one_line:
            one_line = translated_title[:30]
        if len(three_lines) < 1:
            three_lines = [translated_title]
            
        return translated_title, one_line, three_lines[:3]
    except Exception as e:
        print(f"AI Summary Error: {e}")
        return title, title[:30], ["요약 정보를 불러오지 못했습니다.", "-", "-"]

def fetch_and_process():
    processed_data = {
        "daily_learning": generate_daily_learning(),
        "articles": {}
    }
    
    for category, urls in RSS_FEEDS.items():
        processed_data["articles"][category] = []
        collected_titles = []
        
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:6]:
                    raw_title = entry.title.strip()
                    link = entry.link
                    
                    if is_duplicate(raw_title, collected_titles):
                        continue
                    
                    collected_titles.append(raw_title)
                    
                    pub_date = entry.get('published_parsed', time.localtime())
                    iso_date = time.strftime('%Y-%m-%dT%H:%M:%S', pub_date)
                    
                    kor_title, summary_1, summary_3 = get_ai_summaries(raw_title, getattr(entry, 'summary', ''))
                    
                    processed_data["articles"][category].append({
                        "title": kor_title,
                        "link": link,
                        "summary": summary_1,
                        "detail": summary_3,
                        "date": iso_date
                    })
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                
    for cat in processed_data["articles"]:
        processed_data["articles"][cat].sort(key=lambda x: x['date'], reverse=True)
        processed_data["articles"][cat] = processed_data["articles"][cat][:5]

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()
