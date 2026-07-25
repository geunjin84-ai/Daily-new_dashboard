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
    "연예/스타":
