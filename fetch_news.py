import os
import json
import feedparser
import google.generativeai as genai
import time
from difflib import SequenceMatcher
import re

# 1. Gemini 설정
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. RSS 피드 정의 (신규 카테고리 포함)
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
        if SequenceMatcher(None, clean_new, clean_title(ext)).ratio() > threshold: return True
    return False

def generate_multi_learning():
    """새로고침 기능을 위해 5세트의 학습 데이터 생성"""
    try:
        prompt = """
        초보자를 위한 금융/주식 학습 세트 5개를 생성해줘. 각 세트는 주식용어(MTS위치 포함), 생활경제, 퀴즈를 포함해야 해.
        영단어 3개와 명언 1개도 별도로 1세트 포함해줘.
        
        [출력 JSON 양식]:
        {
          "finance_sets": [
            {
              "stock": {"term": "..", "concept": "..", "analogy": "..", "signal": "..", "mts": ".."},
              "economy": {"title": "..", "concept": "..", "impact": ".."},
              "quiz": {"q": "..", "opts": ["..", ".."], "ans": 0, "exp": ".."}
            },
            ... (총 5세트)
          ],
          "daily": {
            "words": [{"word": "..", "meaning": "..", "example": ".."}, ..],
            "quote": {"en": "..", "ko": "..", "author": ".."}
          }
        }
        """
        response = model.generate_content(prompt)
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group())
    except:
        return {"finance_sets": [], "daily": {}}

def get_ai_summaries(title, snippet):
    try:
        prompt = f"제목:{title}\n내용:{snippet}\n위 기사를 한국어로 1줄 요약과 3줄 상세 내용을 작성해줘. 양식: 1줄: [내용]\n3줄:\n- [내용]\n- [내용]\n- [내용]"
        response = model.generate_content(prompt)
        lines = response.text.strip().split('\n')
        one = lines[0].replace('1줄:', '').strip()
        three = [l.strip() for l in lines if l.strip().startswith('-')]
        return one, three[:3]
    except: return title[:30], ["정보를 불러오지 못했습니다.", "-", "-"]

def fetch_and_process():
    learning_data = generate_multi_learning()
    processed_articles = {}
    
    for category, urls in RSS_FEEDS.items():
        processed_articles[category] = []
        titles = []
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                if is_duplicate(entry.title, titles): continue
                titles.append(entry.title)
                s1, s3 = get_ai_summaries(entry.title, getattr(entry, 'summary', ''))
                processed_articles[category].append({
                    "title": entry.title, "link": entry.link, "summary": s1, "detail": s3, "date": time.strftime('%Y-%m-%dT%H:%M:%S', entry.get('published_parsed', time.localtime()))
                })
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"learning": learning_data, "articles": processed_articles}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_process()

---

### 📍 2단계: `index.html` 수정 (접기 + 새로고침 + 드래그 검색)
1. GitHub 저장소의 **`index.html`** 파일 ➔ 연필 모양(Edit) 클릭
2. 기존 내용을 모두 지우고 아래 코드를 붙여넣으세요.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>지식 대시보드 2.0</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    :root { --bg: #f4f6f8; --card: #fff; --main: #333; --sub: #555; --accent: #007bff; --border: #f1f1f1; }
    [data-theme="dark"] { --bg: #121212; --card: #1e1e1e; --main: #e0e0e0; --sub: #aaa; --border: #2c2c2c; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 15px; color: var(--main); }
    .container { max-width: 800px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
    .card { background: var(--card); border-radius: 12px; padding: 16px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .card-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; font-weight: bold; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
    .btn-refresh { background: none; border: 1px solid var(--accent); color: var(--accent); padding: 4px 8px; border-radius: 15px; font-size: 0.75rem; cursor: pointer; }
    .box { background: rgba(0,123,255,0.04); padding: 10px; border-radius: 8px; font-size: 0.82rem; margin-bottom: 10px; }
    .chip-container { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 15px; }
    .chip { padding: 6px 12px; border-radius: 20px; font-size: 0.78rem; border: 1px solid #ddd; background: var(--card); cursor: pointer; }
    .chip.active { background: var(--accent); color: #fff; border-color: var(--accent); }
    .news-item { border-bottom: 1px solid var(--border); padding: 10px 0; text-decoration: none; display: block; color: inherit; }
    .search-popup { display: none; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #222; color: #fff; padding: 10px 20px; border-radius: 30px; z-index: 1000; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📰 지식 대시보드 2.0</h1>
      <button onclick="document.body.toggleAttribute('data-theme')">🌗 테마</button>
    </div>

    <div class="card" style="background: linear-gradient(135deg, #2b5876, #4e4376); color: #fff;">
      <div class="card-header" onclick="toggle('learning-body')">✨ 오늘의 지식 <span id="learning-body-btn">▲</span></div>
      <div id="learning-body" style="padding-top:10px;">
        <div id="quote-display" style="font-style:italic; margin-bottom:10px;"></div>
        <div id="words-display" style="display:grid; grid-template-columns:1fr 1fr; gap:10px;"></div>
      </div>
    </div>

    <div class="card" style="border: 2px solid var(--accent);">
      <div class="card-header">
        <span onclick="toggle('finance-body')">✏️ 실전 경제 교실 <span id="finance-body-btn">▲</span></span>
        <button class="btn-refresh" onclick="refreshFinance()">🔄 다른 내용 보기</button>
      </div>
      <div id="finance-body" style="padding-top:10px;">
        <div class="box" id="stock-box"></div>
        <div class="box" id="economy-box"></div>
        <div class="box" id="quiz-box" style="background:rgba(40,167,69,0.05);"></div>
      </div>
    </div>

    <div class="chip-container" id="filter-chips"></div>

    <div class="card" style="border: 2px solid #28a745;">
      <div class="card-header">
        <span onclick="toggle('news-body')">📰 신문 기사 보기 <span id="news-body-btn">▲</span></span>
        <button class="btn-refresh" onclick="renderNews()" style="border-color:#28a745; color:#28a745;">🔄 기사 섞기</button>
      </div>
      <div id="news-body" style="padding-top:10px;">
        <div id="news-container"></div>
      </div>
    </div>
  </div>

  <div class="search-popup" id="search-popup">
    🔍 '<span id="sel-word"></span>' 뜻 검색 <button onclick="goDict()" style="margin-left:10px; border:none; background:var(--accent); color:#fff; border-radius:10px; padding:2px 10px;">검색</button>
  </div>

  <script>
    let db = {}, enabledCats = [], curFinanceIdx = 0, selTxt = "";

    async function init() {
      const res = await fetch('./data.json?t=' + Date.now());
      db = await res.json();
      enabledCats = Object.keys(db.articles);
      renderLearning(); refreshFinance(); renderChips(); renderNews();
    }

    function toggle(id) {
      const el = document.getElementById(id), btn = document.getElementById(id+'-btn');
      const isHidden = el.style.display === 'none';
      el.style.display = isHidden ? 'block' : 'none';
      btn.innerText = isHidden ? '▲' : '▼';
    }

    function renderLearning() {
      const d = db.learning.daily;
      document.getElementById('quote-display').innerText = `"${d.quote.en}" (${d.quote.ko}) - ${d.quote.author}`;
      document.getElementById('words-display').innerHTML = d.words.map(w => `<div><b>${w.word}</b>: ${w.meaning}</div>`).join('');
    }

    function refreshFinance() {
      const f = db.learning.finance_sets[curFinanceIdx];
      document.getElementById('stock-box').innerHTML = `<b>• 용어:</b> ${f.stock.term}<br><b>• 비유:</b> ${f.stock.analogy}<br><b>• 신호:</b> ${f.stock.signal}<br><b>📍 MTS:</b> ${f.stock.mts}`;
      document.getElementById('economy-box').innerHTML = `<b>• 상식:</b> ${f.economy.title}<br><b>• 영향:</b> ${f.economy.impact}`;
      document.getElementById('quiz-box').innerHTML = `<b>Q. ${f.quiz.q}</b><br>` + f.quiz.opts.map((o,i) => `<button onclick="alert('${i===f.quiz.ans? '정답! '+f.quiz.exp : '오답입니다.'}')" style="width:100%; text-align:left; margin-top:5px; padding:5px;">${i+1}. ${o}</button>`).join('');
      curFinanceIdx = (curFinanceIdx + 1) % db.learning.finance_sets.length;
    }

    function renderNews() {
      const container = document.getElementById('news-container');
      container.innerHTML = '';
      enabledCats.forEach(cat => {
        const arts = db.articles[cat].sort(() => Math.random() - 0.5).slice(0, 3);
        const div = document.createElement('div');
        div.innerHTML = `<h3 style="color:var(--accent); font-size:1rem;">${cat}</h3>` + arts.map(a => `<a class="news-item" href="${cat.includes('해외')? 'https://translate.google.com/translate?u='+encodeURIComponent(a.link) : a.link}" target="_blank"><b>${a.title}</b><div style="font-size:0.75rem; color:var(--sub);">${a.summary}</div></a>`).join('');
        container.appendChild(div);
      });
    }

    function renderChips() {
      const container = document.getElementById('filter-chips');
      Object.keys(db.articles).forEach(cat => {
        const chip = document.createElement('div');
        chip.className = 'chip active'; chip.innerText = cat;
        chip.onclick = () => { chip.classList.toggle('active'); enabledCats = Array.from(document.querySelectorAll('.chip.active')).map(c => c.innerText); renderNews(); };
        container.appendChild(chip);
      });
    }

    document.addEventListener('selectionchange', () => {
      const s = window.getSelection().toString().trim();
      const p = document.getElementById('search-popup');
      if(s && s.length < 10) { selTxt = s; document.getElementById('sel-word').innerText = s; p.style.display = 'block'; }
      else { p.style.display = 'none'; }
    });

    function goDict() { window.open(`https://search.naver.com/search.naver?query=${encodeURIComponent(selTxt + ' 뜻')}`, '_blank'); }

    init();
  </script>
</body>
</html>

---

### 🚀 마무리 안내
1. 두 파일을 모두 수정하신 후 **Actions** 탭에서 **Daily News Collector**를 실행(Run workflow)해 주세요.
2. 약 2분 후 대시보드에 접속하시면 새로운 **2.0 시스템**이 가동됩니다.
3. 이제 아침마다 기사를 드래그해서 모르는 단어를 찾고, 접기 기능을 활용해 나만의 신문을 만들어 보세요!

도움이 필요하시면 언제든 말씀해 주세요. 수고 많으셨습니다!
