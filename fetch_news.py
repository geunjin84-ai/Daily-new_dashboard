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

# 2. 국내 매경 섹션 + 글로벌 해외 언론사 공식 RSS
RSS_FEEDS = {
    "1면/종합": [
        "https://www.mk.co.kr/rss/30000001/",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml"
    ],
    "글로벌/해외이슈": [
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml",  # 월스트리트저널(WSJ) World
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # 뉴욕타임스(NYT) World
        "https://feeds.bbci.co.uk/news/world/rss.xml"  # BBC World
    ],
    "해외 테크/AI": [
        "https://techcrunch.com/feed/",  # 테크크런치
        "https://www.theverge.com/rss/index.xml"  # 더버지
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
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"  # WSJ 금융/비즈니스
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
    "사회/오피니언": [
        "https://www.mk.co.kr/rss/30500001/",
        "https://www.mk.co.kr/rss/30500011/"
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

def get_ai_summaries(title, snippet):
    """영문/한글 기사를 매끄러운 한국어로 자동 번역 및 요약"""
    try:
        prompt = f"""
        기사 제목: {title}
        기사 내용: {snippet}
        
        [지침]
        1. 만약 입력된 기사 내용이 영문(외신)이라면, 반드시 자연스러운 한국어로 번역하여 작성해줘.
        2. 원문의 뜻을 왜곡하지 말고 가독성 높은 매끄러운 한국어로 요약해줘.
        
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
        return title, title[:30], ["요약 및 번역 정보를 불러오지 못했습니다.", "-", "-"]

def fetch_and_process():
    processed_articles = {}
    
    for category, urls in RSS_FEEDS.items():
        processed_articles[category] = []
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
                    
                    # AI 번역 및 요약 실행
                    kor_title, summary_1, summary_3 = get_ai_summaries(raw_title, getattr(entry, 'summary', ''))
                    
                    processed_articles[category].append({
                        "title": kor_title,  # 번역된 제목 저장
                        "link": link,
                        "summary": summary_1,
                        "detail": summary_3,
                        "date": iso_date
                    })
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                
    for cat in processed_articles:
        processed_articles[cat].sort(key=lambda x: x['date'], reverse=True)
        processed_articles[cat] = processed_articles[cat][:5]

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()
