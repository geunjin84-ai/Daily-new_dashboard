import os
import json
import feedparser
import google.generativeai as genai
from datetime import datetime
import time

# 1. Gemini 설정
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 분야 확장 (RSS_FEEDS) - 더 많은 채널을 추가했습니다.
RSS_FEEDS = {
    "IT/테크": [
        "https://rss.donga.com/it.xml",
        "https://www.itworld.co.kr/rss/feed"
    ],
    "경제/비즈니스": [
        "https://rss.donga.com/national.xml",
        "https://php.yonhapnews.co.kr/yonhapnewsv1/static/rss/economy.xml"
    ],
    "문화/라이프": [
        "https://rss.donga.com/culture.xml",
        "https://rss.donga.com/sports.xml"
    ]
}

def get_ai_summaries(title, snippet):
    """AI에게 1줄 요약과 3줄 디테일 요약을 동시에 요청"""
    try:
        prompt = f"""
        뉴스 제목: {title}
        내용: {snippet}
        
        위 내용을 바탕으로 다음 두 가지를 만들어줘:
        1. 핵심 1줄 요약 (30자 이내)
        2. 상세 3줄 요약 (각 줄마다 짧은 문장으로, 총 3문장)
        
        형식:
        1줄: [요약 내용]
        3줄:
        - [내용1]
        - [내용2]
        - [내용3]
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 텍스트에서 1줄과 3줄 분리 로직 (간단화)
        lines = text.split('\n')
        one_line = lines[0].replace('1줄:', '').strip()
        three_lines = [l.strip() for l in lines if l.strip().startswith('-')]
        
        return one_line, three_lines[:3]
    except:
        return title[:30], ["요약을 불러오지 못했습니다.", "-", "-"]

def fetch_and_process():
    processed_articles = {}
    
    for category, urls in RSS_FEEDS.items():
        processed_articles[category] = []
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.title
                link = entry.link
                # 시간 데이터 추출 (정렬용)
                pub_date = entry.get('published_parsed', time.localtime())
                iso_date = time.strftime('%Y-%m-%dT%H:%M:%S', pub_date)
                
                # AI 요약 (1줄 + 3줄)
                summary_1, summary_3 = get_ai_summaries(title, getattr(entry, 'summary', ''))
                
                processed_articles[category].append({
                    "title": title,
                    "link": link,
                    "summary": summary_1,
                    "detail": summary_3,
                    "date": iso_date
                })
                
    # 시간 순으로 정렬 (최신순)
    for cat in processed_articles:
        processed_articles[cat].sort(key=lambda x: x['date'], reverse=True)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()
