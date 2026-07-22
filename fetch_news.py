import os
import json
import feedparser
import google.generativeai as genai
from datetime import datetime
import time
from difflib import SequenceMatcher

# 1. Gemini 설정
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 매경 종이신문 섹션 기준 + 주요 일간지/경제지 RSS 화이트리스트
RSS_FEEDS = {
    "1면/종합": [
        "https://www.mk.co.kr/rss/30000001/",  # 매경 헤드라인
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/headline.xml",  # 연합뉴스 헤드라인
        "https://www.chosun.com/arc/outboundfeeds/rss/category/national/?outputType=xml"
    ],
    "정치/외교": [
        "https://www.mk.co.kr/rss/30200030/",  # 매경 정치
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
        "https://www.mk.co.kr/rss/50100032/",  # 매경 기업/산업
        "https://rss.hankyung.com/feed/industry.xml"
    ],
    "부동산": [
        "https://www.mk.co.kr/rss/50300009/",  # 매경 부동산
        "https://rss.hankyung.com/feed/land.xml"
    ],
    "IT/과학/Bio": [
        "https://www.mk.co.kr/rss/50700001/",  # 매경 IT/과학
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/it.xml",
        "https://www.khan.co.kr/rss/rssdata/it.xml"
    ],
    "국제/글로벌": [
        "https://www.mk.co.kr/rss/30300018/",  # 매경 국제
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/international.xml"
    ],
    "사회/오피니언": [
        "https://www.mk.co.kr/rss/30500001/",  # 매경 사회
        "https://www.mk.co.kr/rss/30500011/"   # 매경 사설/칼럼
    ],
    "라이프/스포츠": [
        "https://www.mk.co.kr/rss/70000001/",  # 매경 문화/생활
        "https://rss.donga.com/sports.xml"
    ],
    "스타트업/벤처": [
        "https://rss.hankyung.com/feed/it.xml"  # 한경 IT/벤처
    ]
}

def is_similar(title1, title2, threshold=0.7):
    """비용 0원으로 제목 중복 걸러내는 알고리즘"""
    return SequenceMatcher(None, title1, title2).ratio() > threshold

def get_ai_summaries(title, snippet):
    """Gemini 무료 API를 사용한 핵심 요약"""
    try:
        prompt = f"""
        뉴스 제목: {title}
        내용: {snippet}
        
        위 기사를 바탕으로 작성해줘:
        1. 핵심 1줄 요약 (30자 이내)
        2. 상세 3줄 요약 (각 줄마다 짧은 문장 1개씩, 총 3문장)
        
        형식:
        1줄: [요약]
        3줄:
        - [내용1]
        - [내용2]
        - [내용3]
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        lines = text.split('\n')
        one_line = lines[0].replace('1줄:', '').strip()
        three_lines = [l.strip() for l in lines if l.strip().startswith('-')]
        
        return one_line, three_lines[:3]
    except:
        return title[:30], ["요약 정보를 불러오지 못했습니다.", "-", "-"]

def fetch_and_process():
    processed_articles = {}
    
    for category, urls in RSS_FEEDS.items():
        processed_articles[category] = []
        collected_titles = []
        
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:6]:
                    title = entry.title.strip()
                    link = entry.link
                    
                    # 1차 파이썬 단 중복 검사 (비용 0원)
                    if any(is_similar(title, t) for t in collected_titles):
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
                
    # 최신순 정렬 및 카테고리당 최대 5개 기사 제한
    for cat in processed_articles:
        processed_articles[cat].sort(key=lambda x: x['date'], reverse=True)
        processed_articles[cat] = processed_articles[cat][:5]

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()
