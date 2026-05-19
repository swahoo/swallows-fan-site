'use strict';

// ============================================================
// RSS ソース設定
// ============================================================
const SOURCES = [
  {
    id: 'nhk',
    name: 'NHK',
    feeds: [
      { url: 'https://www.nhk.or.jp/rss/news/cat0.xml', cat: 'top' },
      { url: 'https://www.nhk.or.jp/rss/news/cat4.xml', cat: 'politics' },
      { url: 'https://www.nhk.or.jp/rss/news/cat5.xml', cat: 'economy' },
      { url: 'https://www.nhk.or.jp/rss/news/cat6.xml', cat: 'international' },
      { url: 'https://www.nhk.or.jp/rss/news/cat7.xml', cat: 'society' },
      { url: 'https://www.nhk.or.jp/rss/news/cat2.xml', cat: 'sports' },
      { url: 'https://www.nhk.or.jp/rss/news/cat3.xml', cat: 'science' },
    ],
  },
  {
    id: 'bbc',
    name: 'BBC',
    feeds: [
      { url: 'https://feeds.bbci.co.uk/japanese/rss.xml', cat: 'international' },
    ],
  },
  {
    id: 'asahi',
    name: '朝日新聞',
    feeds: [
      { url: 'https://rss.asahi.com/rss/asahi/newsheadlines.rdf', cat: 'top' },
    ],
  },
  {
    id: 'sankei',
    name: '産経新聞',
    feeds: [
      { url: 'https://www.sankei.com/rss/flash.xml', cat: 'top' },
    ],
  },
  {
    id: 'tbs',
    name: 'TBS',
    feeds: [
      { url: 'https://news.tbs.co.jp/rss/topics.rdf', cat: 'top' },
    ],
  },
];

// ============================================================
// カテゴリ定義
// ============================================================
const CATS = {
  politics:      { label: '政治',         icon: '🏛',  css: 'cb-politics' },
  economy:       { label: '経済',         icon: '📈',  css: 'cb-economy' },
  society:       { label: '社会',         icon: '👥',  css: 'cb-society' },
  international: { label: '国際',         icon: '🌍',  css: 'cb-international' },
  sports:        { label: 'スポーツ',     icon: '⚽',  css: 'cb-sports' },
  science:       { label: '科学・テク',   icon: '🔬',  css: 'cb-science' },
  entertainment: { label: 'エンタメ',     icon: '🎬',  css: 'cb-entertainment' },
  top:           { label: 'ニュース',     icon: '📰',  css: 'cb-default' },
  default:       { label: 'ニュース',     icon: '📰',  css: 'cb-default' },
};

const CAT_GRADIENTS = {
  politics:      'linear-gradient(135deg,#b71c1c,#e53935)',
  economy:       'linear-gradient(135deg,#1b5e20,#388e3c)',
  society:       'linear-gradient(135deg,#0d47a1,#1976d2)',
  international: 'linear-gradient(135deg,#4a148c,#7b1fa2)',
  sports:        'linear-gradient(135deg,#bf360c,#e64a19)',
  science:       'linear-gradient(135deg,#004d40,#00796b)',
  entertainment: 'linear-gradient(135deg,#880e4f,#ad1457)',
  top:           'linear-gradient(135deg,#1a237e,#283593)',
  default:       'linear-gradient(135deg,#263238,#455a64)',
};

// ============================================================
// CORS プロキシ
// ============================================================
const PROXIES = [
  u => `https://api.allorigins.win/get?url=${encodeURIComponent(u)}`,
  u => `https://corsproxy.io/?${encodeURIComponent(u)}`,
];

async function fetchViaProxy(url) {
  for (const proxy of PROXIES) {
    try {
      const res = await fetch(proxy(url), { signal: AbortSignal.timeout(9000) });
      if (!res.ok) continue;
      const json = await res.json();
      const text = json.contents ?? json;
      if (typeof text === 'string' && (text.includes('<rss') || text.includes('<rdf') || text.includes('<feed'))) {
        return text;
      }
    } catch (_) { /* try next */ }
  }
  throw new Error('fetch failed: ' + url);
}

// ============================================================
// XML パーサー（RSS 2.0 / RDF 1.0 / Atom 対応）
// ============================================================
function parseXML(xmlText, sourceId, defaultCat) {
  const doc = new DOMParser().parseFromString(xmlText, 'application/xml');
  const items = [...doc.querySelectorAll('item, entry')];
  const articles = [];

  for (const item of items) {
    const title = text(item, 'title');
    if (!title) continue;

    // link
    let link = text(item, 'link') ||
               item.querySelector('link[href]')?.getAttribute('href') || '';
    link = link.trim();
    if (link.startsWith('//')) link = 'https:' + link;
    if (!link) continue;

    // description / summary / content
    const desc = stripHTML(
      text(item, 'description') ||
      text(item, 'summary') ||
      text(item, 'content') || ''
    ).slice(0, 220);

    // pubDate / dc:date / updated
    const rawDate =
      text(item, 'pubDate') ||
      itemNS(item, 'http://purl.org/dc/elements/1.1/', 'date') ||
      text(item, 'updated') ||
      text(item, 'published') || '';
    const pubDate = rawDate ? new Date(rawDate) : new Date();

    // image
    const image = extractImage(item);

    // category from feed tags
    const cat = detectCategory(title + ' ' + desc, defaultCat);

    articles.push({ id: link, title, link, desc, image, pubDate, source: sourceId, cat });
  }

  return articles;
}

function text(el, tag) {
  return el.querySelector(tag)?.textContent?.trim() || '';
}
function itemNS(el, ns, local) {
  return el.getElementsByTagNameNS(ns, local)[0]?.textContent?.trim() || '';
}
function stripHTML(s) {
  return s.replace(/<[^>]+>/g, '').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&').replace(/&nbsp;/g,' ').trim();
}
function extractImage(item) {
  const enc = item.querySelector('enclosure[type^="image"]');
  if (enc) return enc.getAttribute('url');
  const mc = item.querySelector('content[url]');
  if (mc) return mc.getAttribute('url');
  const thumb = item.querySelector('thumbnail[url]');
  if (thumb) return thumb.getAttribute('url');
  const m = (text(item,'description') || '').match(/<img[^>]+src=["']([^"']+)["']/i);
  return m ? m[1] : null;
}

// キーワードからカテゴリ推定
const CAT_KEYWORDS = {
  politics: /政治|国会|首相|議員|閣僚|自民|公明|立憲|選挙|内閣|外交|条約|法案|衆議院|参議院|大統領|ホワイトハウス|NATO|G7|G20/,
  economy: /経済|株|円|GDP|物価|景気|企業|貿易|貿易収支|輸出|輸入|日銀|財政|金利|インフレ|デフレ|市場|半導体|AI|テクノロジー|起業|IPO|決算/,
  society: /事件|事故|火災|地震|台風|洪水|災害|気候|環境|教育|医療|福祉|少子|高齢|人口|交通|犯罪|逮捕|裁判|判決/,
  international: /海外|米国|中国|ロシア|ウクライナ|欧州|EU|中東|アフリカ|国連|外相|summit|世界|国際/i,
  sports: /野球|サッカー|テニス|バスケ|ラグビー|陸上|水泳|オリンピック|W杯|リーグ|優勝|敗退|選手|監督|得点|ホームラン/,
  science: /科学|宇宙|NASA|JAXA|AI|人工知能|ロボット|研究|発見|医学|薬|ワクチン|気候変動|再生可能|原子力|技術|iPS|ゲノム/,
  entertainment: /映画|音楽|ドラマ|芸能|タレント|俳優|歌手|アニメ|漫画|ゲーム|賞|受賞|コンサート|公演|出演/,
};
function detectCategory(text, fallback) {
  for (const [cat, re] of Object.entries(CAT_KEYWORDS)) {
    if (re.test(text)) return cat;
  }
  return fallback || 'top';
}

// ============================================================
// アプリ状態
// ============================================================
let allArticles = [];
let filtered   = [];
let shown      = 0;
const PAGE     = 12;
let activeCat  = 'all';
let activeSrc  = 'all';
let query      = '';

// ============================================================
// フィード取得
// ============================================================
async function fetchFeed(sourceId, feedCfg) {
  try {
    const xml = await fetchViaProxy(feedCfg.url);
    return parseXML(xml, sourceId, feedCfg.cat);
  } catch (e) {
    console.warn(`[${sourceId}] ${feedCfg.url} →`, e.message);
    return [];
  }
}

async function fetchAllFeeds() {
  showState('loading');

  const tasks = SOURCES.flatMap(s => s.feeds.map(f => fetchFeed(s.id, f)));
  const results = await Promise.allSettled(tasks);
  const raw = results.filter(r => r.status === 'fulfilled').flatMap(r => r.value);

  // 重複排除・日時ソート
  const seen = new Set();
  allArticles = raw
    .filter(a => { if (seen.has(a.link)) return false; seen.add(a.link); return true; })
    .sort((a, b) => b.pubDate - a.pubDate);

  if (allArticles.length === 0) {
    showState('error');
    return;
  }

  setLastUpdated();
  applyFilters();
  renderTrending();
  renderBreaking();
  showState('feed');
}

// ============================================================
// フィルタリング
// ============================================================
function applyFilters() {
  const q = query.toLowerCase();
  filtered = allArticles.filter(a => {
    if (activeCat !== 'all' && a.cat !== activeCat) return false;
    if (activeSrc !== 'all' && a.source !== activeSrc) return false;
    if (q && !a.title.toLowerCase().includes(q) && !a.desc.toLowerCase().includes(q)) return false;
    return true;
  });
  shown = 0;
  document.getElementById('featuredWrap').innerHTML = '';
  document.getElementById('newsGrid').innerHTML = '';
  renderArticles();
  renderTrending();
}

// ============================================================
// レンダリング
// ============================================================
function renderArticles() {
  const grid = document.getElementById('newsGrid');
  const featWrap = document.getElementById('featuredWrap');

  if (filtered.length === 0) {
    grid.innerHTML = `<p style="color:#888;text-align:center;padding:40px;grid-column:1/-1">該当するニュースが見つかりませんでした</p>`;
    document.getElementById('loadMoreWrap').style.display = 'none';
    return;
  }

  // 特集記事（最初の1件）
  if (shown === 0 && filtered.length > 0) {
    featWrap.innerHTML = featuredHTML(filtered[0]);
    shown = 1;
  }

  const slice = filtered.slice(shown, shown + PAGE);
  for (const a of slice) {
    const el = document.createElement('a');
    el.href = esc(a.link);
    el.target = '_blank';
    el.rel = 'noopener';
    el.className = 'news-card';
    el.innerHTML = cardInnerHTML(a);
    grid.appendChild(el);
  }
  shown += slice.length;

  document.getElementById('loadMoreWrap').style.display =
    shown < filtered.length ? 'block' : 'none';
}

function featuredHTML(a) {
  const cat = CATS[a.cat] || CATS.default;
  const gradient = CAT_GRADIENTS[a.cat] || CAT_GRADIENTS.default;
  const imgTag = a.image
    ? `<img src="${esc(a.image)}" alt="" loading="lazy" onerror="this.remove()">`
    : `<span class="featured-img-icon">${cat.icon}</span>`;
  return `
    <a href="${esc(a.link)}" target="_blank" rel="noopener" class="featured-card">
      <div class="featured-img" style="background:${gradient}">${imgTag}</div>
      <div class="featured-body">
        <div class="featured-meta">
          <span class="cat-badge ${cat.css}">${cat.icon} ${cat.label}</span>
          <span class="src-badge ${srcCSS(a.source)}">${srcName(a.source)}</span>
          <span style="font-size:11px;color:#999;margin-left:auto;">${timeAgo(a.pubDate)}</span>
        </div>
        <h2 class="featured-title">${esc(a.title)}</h2>
        ${a.desc ? `<p class="featured-desc">${esc(a.desc)}</p>` : ''}
        <span class="featured-readmore">続きを読む →</span>
      </div>
    </a>`;
}

function cardInnerHTML(a) {
  const cat = CATS[a.cat] || CATS.default;
  const gradient = CAT_GRADIENTS[a.cat] || CAT_GRADIENTS.default;
  const imgTag = a.image
    ? `<img src="${esc(a.image)}" alt="" loading="lazy" onerror="this.remove()">`
    : `<span class="card-thumb-icon">${cat.icon}</span>`;
  return `
    <div class="card-thumb" style="background:${gradient}">${imgTag}</div>
    <div class="card-body">
      <div class="card-meta">
        <span class="cat-badge ${cat.css}">${cat.label}</span>
        <span class="src-badge ${srcCSS(a.source)}">${srcName(a.source)}</span>
      </div>
      <p class="card-title">${esc(a.title)}</p>
      <div class="card-foot">
        <span>${timeAgo(a.pubDate)}</span>
        <span class="card-readmore">続きを読む →</span>
      </div>
    </div>`;
}

function renderTrending() {
  const list = document.getElementById('trendingList');
  const top5 = filtered.slice(0, 5);
  if (top5.length === 0) { list.innerHTML = ''; return; }
  list.innerHTML = top5.map((a, i) => `
    <li class="trending-item" onclick="window.open('${esc(a.link)}','_blank')">
      <span class="trending-num">${i + 1}</span>
      <span class="trending-text">${esc(a.title)}</span>
    </li>`).join('');
}

function renderBreaking() {
  const bar = document.getElementById('breakingBar');
  const ticker = document.getElementById('breakingTicker');
  if (allArticles.length === 0) return;
  ticker.textContent = allArticles[0].title;
  bar.style.display = 'flex';
}

// ============================================================
// UI ヘルパー
// ============================================================
function showState(state) {
  document.getElementById('loadingState').style.display = state === 'loading' ? 'block' : 'none';
  document.getElementById('errorState').style.display   = state === 'error'   ? 'block' : 'none';
  document.getElementById('feedArea').style.display     = state === 'feed'    ? 'block' : 'none';
}

function setLastUpdated() {
  const now = new Date();
  const h = now.getHours(), m = String(now.getMinutes()).padStart(2,'0');
  document.getElementById('lastUpdated').textContent = `最終更新 ${h}:${m}`;
}

function updateClock() {
  const now = new Date();
  const DOW = ['日','月','火','水','木','金','土'];
  const h = now.getHours(), m = String(now.getMinutes()).padStart(2,'0');
  document.getElementById('currentDateTime').textContent =
    `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日（${DOW[now.getDay()]}）${h}:${m}`;
}

function timeAgo(date) {
  if (!(date instanceof Date) || isNaN(date)) return '';
  const diff = Date.now() - date.getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'たった今';
  if (m < 60) return `${m}分前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}時間前`;
  const d = Math.floor(h / 24);
  if (d < 7)  return `${d}日前`;
  return `${date.getMonth()+1}/${date.getDate()}`;
}

function srcName(id) {
  return { nhk:'NHK', bbc:'BBC', asahi:'朝日', sankei:'産経', tbs:'TBS' }[id] || id.toUpperCase();
}
function srcCSS(id) {
  return { nhk:'sb-nhk', bbc:'sb-bbc', asahi:'sb-asahi', sankei:'sb-sankei', tbs:'sb-tbs' }[id] || 'sb-default';
}
function esc(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ============================================================
// イベント登録
// ============================================================

// カテゴリボタン（上部ナビ）
document.getElementById('catList').addEventListener('click', e => {
  const btn = e.target.closest('.cat-btn');
  if (!btn) return;
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeCat = btn.dataset.cat;
  applyFilters();
});

// ソースチップ
document.getElementById('sourceChips').addEventListener('click', e => {
  const chip = e.target.closest('.src-chip');
  if (!chip) return;
  document.querySelectorAll('.src-chip').forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeSrc = chip.dataset.src;
  applyFilters();
});

// サイドバー カテゴリリンク
document.querySelectorAll('.cat-side-btn').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    activeCat = link.dataset.cat;
    document.querySelectorAll('.cat-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.cat === activeCat);
    });
    applyFilters();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});

// 検索
let searchTimer;
document.getElementById('searchInput').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { query = e.target.value.trim(); applyFilters(); }, 300);
});

// 更新ボタン
document.getElementById('refreshBtn').addEventListener('click', () => {
  const btn = document.getElementById('refreshBtn');
  btn.classList.add('spinning');
  fetchAllFeeds().finally(() => btn.classList.remove('spinning'));
});

// もっと見る
document.getElementById('loadMoreBtn').addEventListener('click', renderArticles);

// ============================================================
// 初期化
// ============================================================
updateClock();
setInterval(updateClock, 60000);
fetchAllFeeds();
// 15分ごとに自動更新
setInterval(fetchAllFeeds, 15 * 60 * 1000);
