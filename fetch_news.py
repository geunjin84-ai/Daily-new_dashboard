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

# 2. 지면 신문 및 주요 일간지/경제지 핵심 RSS
RSS_FEEDS = {
    "1면/종합": [
        "https://www.mk.co.kr/rss/30000001/",  # 매경 헤드라인
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml",  # 연합 헤드라인
        "https://www.chosun.com/arc/outboundfeeds/rss/category/national/?outputType=xml"
    ],
    "정치/외교": [
        "https://www.mk.co.kr/rss/30200030/",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/politics.xml"
    ],
    "경제/정책": [
        "https://www.mk.co.kr/rss/30100041/",  # 매경 경제
        "https://rss.hankyung.com/feed/economy.xml",  # 한경 경제
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/economy.xml"
    ],
    "금융/증권": [
        "https://www.mk.co.kr/rss/50200011/",  # 매경 증권
        "https://rss.hankyung.com/feed/stock.xml"  # 한경 증권
    ],
    "산업/기업": [
        "https://www.mk.co.kr/rss/50100032/",  # 매경 산업
        "https://rss.hankyung.com/feed/industry.xml"  # 한경 산업
    ],
    "부동산": [
        "https://www.mk.co.kr/rss/50300009/",  # 매경 부동산
        "https://rss.hankyung.com/feed/land.xml"  # 한경 부동산
    ],
    "IT/과학/Bio": [
        "https://www.mk.co.kr/rss/50700001/",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/it.xml",
        "https://www.khan.co.kr/rss/rssdata/it.xml"
    ],
    "국제/글로벌": [
        "https://www.mk.co.kr/rss/30300018/",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/international.xml"
    ],
    "사회/오피니언": [
        "https://www.mk.co.kr/rss/30500001/",
        "https://www.mk.co.kr/rss/30500011/"
    ],
    "라이프/스포츠": [
        "https://www.mk.co.kr/rss/70000001/",
        "https://rss.donga.com/sports.xml"
    ]
}

def clean_title(title):
    """특수문자 및 언론사 태그 제거하여 순수 키워드 추출"""
    title = re.sub(r'\[.*?\]|\(.*?\)', '', title)  # [속보], (종합) 등 제거
    return title.strip()

def is_duplicate(new_title, existing_titles, threshold=0.65):
    """제목 유사도 및 핵심 키워드 중복 검사 (비용 0원)"""
    clean_new = clean_title(new_title)
    for ext in existing_titles:
        clean_ext = clean_title(ext)
        # 1. 단순 유사도 비율 검사
        ratio = SequenceMatcher(None, clean_new, clean_ext).ratio()
        if ratio > threshold:
            return True
        # 2. 주요 명사/단어 3개 이상 겹치는지 검사
        words_new = set([w for w in clean_new.split() if len(w) > 1])
        words_ext = set([w for w in clean_ext.split() if len(w) > 1])
        common = words_new.intersection(words_ext)
        if len(common) >= 3:
            return True
    return False

def get_ai_summaries(title, snippet):
    """Gemini 무료 API를 활용한 1줄/3줄 요약"""
    try:
        prompt = f"""
        뉴스 제목: {title}
        내용: {snippet}
        
        위 기사 내용을 바탕으로 아래 양식에 맞추어 요약해줘:
        1줄: [30자 이내의 핵심 1줄 요약]
        3줄:
        - [상세 내용 1]
        - [상세 내용 2]
        - [상세 내용 3]
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        lines = text.split('\n')
        one_line = lines[0].replace('1줄:', '').strip()
        three_lines = [l.strip() for l in lines if l.strip().startswith('-')]
        
        if not one_line:
            one_line = title[:30]
        if len(three_lines) < 1:
            three_lines = [title]
            
        return one_line, three_lines[:3]
    except Exception as e:
        print(f"AI Summary Error: {e}")
        return title[:30], ["요약 정보를 불러오지 못했습니다.", "-", "-"]

def fetch_and_process():
    processed_articles = {}
    
    for category, urls in RSS_FEEDS.items():
        processed_articles[category] = []
        collected_titles = []
        
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:8]:
                    title = entry.title.strip()
                    link = entry.link
                    
                    # 언론사 간 중복 기사 제거 (최초 1개 기사만 채택)
                    if is_duplicate(title, collected_titles):
                        continue
                    
                    collected_titles.append(title)
                    
                    pub_date = entry.get('published_parsed', time.localtime())
                    iso_date = time.strftime('%Y-%m-%dT%H:%M:%S', pub_date)
                    
                    summary_1, summary_3 = get_ai_summaries(title, getattr(entry, 'summary', ''))
                    
                    processed_articles[category].append({
                        "title": title,
                        "link": link,
                        "summary": summary_1,
                        "detail": summary_3,
                        "date": iso_date
                    })
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                
    # 각 카테고리별 최신순 정렬 후 최대 6개 추출
    for cat in processed_articles:
        processed_articles[cat].sort(key=lambda x: x['date'], reverse=True)
        processed_articles[cat] = processed_articles[cat][:6]

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()
