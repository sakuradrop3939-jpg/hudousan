"""
GitHub Pages 用 HTML 出力モジュール
docs/index.html を生成する。スマホ最適化・ソート・フィルタ機能付き。
既読管理・お気に入り機能（localStorage）付き。
"""
import json
import os
from datetime import datetime
from pathlib import Path

from .config import DEMAND_LABELS

DOCS_DIR = Path(__file__).parent.parent / "docs"


def write_html(records: list[dict]) -> str:
    DOCS_DIR.mkdir(exist_ok=True)

    rows_data = []
    for rec in records:
        p = rec["prop"]
        sr = rec["score"]
        dl = DEMAND_LABELS.get(sr.demand_level, DEMAND_LABELS[2])

        rows_data.append({
            "score":        sr.total,
            "demand_emoji": dl["emoji"],
            "demand_text":  dl["text"],
            "demand_level": sr.demand_level,
            "area":         p.area_name,
            "price":        p.price_man or (p.price // 10_000),
            "layout":       p.layout,
            "reason":       sr.reason,
            "age":          p.building_age or "",
            "land":         p.land_area or "",
            "building":     p.building_area or "",
            "parking":      "あり" if p.parking is True else ("なし" if p.parking is False else "不明"),
            "site":         p.site,
            "fetched_at":   p.fetched_at,
            "name":         p.name,
            "address":      p.address,
            "url":          p.url,
            "yield_pct":    round(sr.estimated_yield, 1),
        })

    updated = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    json_data = json.dumps(rows_data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ぼろ戸建て投資物件リスト</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Noto Sans JP', sans-serif;
      background: #f0f2f5; color: #1a1a2e; font-size: 13px;
    }}
    header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white; padding: 14px 16px; position: sticky; top: 0; z-index: 100;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }}
    header h1 {{ font-size: 16px; font-weight: 700; }}
    header .meta {{ font-size: 11px; color: #aaa; margin-top: 4px; }}
    .controls {{
      padding: 10px 12px; background: white;
      border-bottom: 1px solid #e0e0e0; display: flex; gap: 8px; flex-wrap: wrap;
      position: sticky; top: 56px; z-index: 99;
    }}
    .controls input {{
      flex: 1; min-width: 160px; padding: 7px 10px; border: 1px solid #ccc;
      border-radius: 8px; font-size: 13px; outline: none;
    }}
    .controls select {{
      padding: 7px 10px; border: 1px solid #ccc; border-radius: 8px; font-size: 13px;
      background: white; outline: none;
    }}
    .filter-btns {{
      padding: 8px 12px; background: #fafafa;
      border-bottom: 1px solid #e0e0e0; display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
    }}
    .filter-btn {{
      padding: 6px 14px; border: 1.5px solid #ccc; border-radius: 20px;
      background: white; font-size: 12px; cursor: pointer; font-weight: 600;
      transition: all 0.15s;
    }}
    .filter-btn.active {{ background: #1a73e8; color: white; border-color: #1a73e8; }}
    .filter-btn.fav-btn-toggle.active {{ background: #f5a623; border-color: #f5a623; color: white; }}
    .mark-all-btn {{
      padding: 6px 14px; border: 1.5px solid #4caf50; border-radius: 20px;
      background: white; color: #4caf50; font-size: 12px; cursor: pointer; font-weight: 600;
    }}
    .mark-all-btn:hover {{ background: #4caf50; color: white; }}
    .stats {{
      padding: 8px 12px; background: #e8f4fd; font-size: 12px; color: #555;
      border-bottom: 1px solid #ddd;
    }}
    .table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    table {{ width: 100%; border-collapse: collapse; white-space: nowrap; }}
    thead th {{
      background: #1a1a2e; color: white; padding: 10px 10px;
      text-align: left; font-size: 11px; font-weight: 600; cursor: pointer;
      user-select: none; position: sticky; top: 0;
    }}
    thead th:hover {{ background: #2d3561; }}
    thead th.sort-asc::after  {{ content: " ▲"; font-size: 9px; }}
    thead th.sort-desc::after {{ content: " ▼"; font-size: 9px; }}
    tbody tr:nth-child(even) {{ background: #f8f9fc; }}
    tbody tr:hover {{ background: #e8f0fe; }}
    td {{ padding: 9px 10px; border-bottom: 1px solid #e8e8e8; vertical-align: middle; }}

    /* 未読行 */
    tr.row-new {{ border-left: 4px solid #e53935; }}
    tr.row-new td:first-child {{ background: rgba(229,57,53,0.04); }}

    /* お気に入り行 */
    tr.row-fav {{ background: #fffde7 !important; }}

    /* NEWバッジ */
    .new-badge {{
      display: inline-block; background: #e53935; color: white;
      font-size: 9px; font-weight: 700; padding: 2px 5px;
      border-radius: 4px; margin-right: 4px; vertical-align: middle;
      letter-spacing: 0.5px;
    }}

    /* お気に入りボタン */
    .fav-star {{
      background: none; border: none; cursor: pointer;
      font-size: 18px; padding: 0 2px; line-height: 1;
      vertical-align: middle; transition: transform 0.1s;
    }}
    .fav-star:hover {{ transform: scale(1.3); }}

    /* スコア */
    .score {{
      font-weight: 700; font-size: 15px; text-align: center;
      border-radius: 6px; padding: 4px 8px; display: inline-block; min-width: 38px;
    }}
    .score-s {{ background: #1e8c2e; color: white; }}
    .score-a {{ background: #6abf69; color: white; }}
    .score-b {{ background: #f9c74f; color: #333; }}
    .score-c {{ background: #f4845f; color: white; }}

    /* 賃貸需要 */
    .demand {{ border-radius: 5px; padding: 3px 7px; font-size: 12px; font-weight: 600; white-space: nowrap; }}
    .demand-4 {{ background: #ff6347; color: white; }}
    .demand-3 {{ background: #ff8c00; color: white; }}
    .demand-2 {{ background: #ffd700; color: #333; }}
    .demand-1 {{ background: #87ceeb; color: #333; }}

    /* 直リンクボタン */
    .link-btn {{
      display: inline-block; background: #1a73e8; color: white;
      padding: 6px 12px; border-radius: 20px; text-decoration: none;
      font-size: 12px; font-weight: 600; white-space: nowrap;
      box-shadow: 0 2px 4px rgba(26,115,232,0.3);
    }}
    .link-btn:hover {{ background: #1557b0; }}
    .link-btn.seen {{ background: #888; box-shadow: none; }}

    .yield-high {{ color: #1e8c2e; font-weight: 700; }}
    .yield-mid  {{ color: #e07b00; font-weight: 600; }}
    .yield-low  {{ color: #999; }}

    .reason {{ white-space: normal; max-width: 300px; font-size: 12px; color: #444; line-height: 1.5; }}
    .no-data {{ text-align: center; padding: 40px; color: #888; font-size: 15px; }}
    .price {{ font-weight: 700; color: #c0392b; }}
    .legend {{
      padding: 10px 12px; background: white; border-top: 1px solid #eee;
      font-size: 11px; color: #666; display: flex; gap: 12px; flex-wrap: wrap;
    }}
    .legend span {{ display: flex; align-items: center; gap: 4px; }}
  </style>
</head>
<body>

<header>
  <h1>🏚️ ぼろ戸建て投資物件リスト</h1>
  <div class="meta">最終更新: {updated} ｜ スコア高い順</div>
</header>

<div class="controls">
  <input type="text" id="filterInput" placeholder="🔍 エリア・間取り・住所などで絞り込み" oninput="applyFilter()">
  <select id="areaFilter" onchange="applyFilter()">
    <option value="">全エリア</option>
  </select>
  <select id="siteFilter" onchange="applyFilter()">
    <option value="">全サイト</option>
  </select>
</div>

<div class="filter-btns">
  <button class="filter-btn" id="btnUnread" onclick="toggleUnreadFilter()">🆕 未読のみ</button>
  <button class="filter-btn fav-btn-toggle" id="btnFav" onclick="toggleFavFilter()">⭐ お気に入りのみ</button>
  <button class="mark-all-btn" onclick="markAllRead()">✓ 全て既読にする</button>
  <span id="unreadCount" style="font-size:12px;color:#e53935;font-weight:700;margin-left:4px;"></span>
</div>

<div class="stats" id="stats"></div>

<div class="table-wrap">
<table id="propTable">
  <thead>
    <tr>
      <th style="min-width:70px">状態</th>
      <th onclick="sortTable(1)">スコア</th>
      <th onclick="sortTable(2)">賃貸需要</th>
      <th onclick="sortTable(3)">エリア</th>
      <th onclick="sortTable(4)">価格(万)</th>
      <th onclick="sortTable(5)">間取り</th>
      <th onclick="sortTable(6)">利回り</th>
      <th>おすすめ理由</th>
      <th onclick="sortTable(8)">築年</th>
      <th onclick="sortTable(9)">土地㎡</th>
      <th onclick="sortTable(10)">建物㎡</th>
      <th>駐車場</th>
      <th>サイト</th>
      <th>直リンク</th>
    </tr>
  </thead>
  <tbody id="tableBody"></tbody>
</table>
</div>

<div class="legend">
  <span>スコア: <span class="score score-s">S 80+</span></span>
  <span><span class="score score-a">A 65+</span></span>
  <span><span class="score score-b">B 50+</span></span>
  <span><span class="score score-c">C -49</span></span>
  &nbsp;|&nbsp;
  <span>需要: <span class="demand demand-4">🔴高</span></span>
  <span><span class="demand demand-3">🟠中高</span></span>
  <span><span class="demand demand-2">🟡中</span></span>
  <span><span class="demand demand-1">🔵低</span></span>
  &nbsp;|&nbsp;
  <span>🆕 = 未読　⭐ = お気に入り</span>
</div>

<script>
const DATA = {json_data};

// ── localStorage ──────────────────────────────
const SEEN_KEY = 'borodate_seen_v2';
const FAV_KEY  = 'borodate_fav_v2';

function getSeen() {{ return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || '[]')); }}
function saveSeen(s) {{ localStorage.setItem(SEEN_KEY, JSON.stringify([...s])); }}
function getFavs() {{ return new Set(JSON.parse(localStorage.getItem(FAV_KEY) || '[]')); }}
function saveFavs(f) {{ localStorage.setItem(FAV_KEY, JSON.stringify([...f])); }}

function propKey(d) {{ return d.url || (d.area + '|' + d.price + '|' + d.name); }}

let seenCache = getSeen();
let favCache  = getFavs();

// ── フィルタ状態 ──────────────────────────────
let sortCol = 1;
let sortDir = -1;
let filtered = [...DATA];
let showUnreadOnly = false;
let showFavOnly    = false;

// ── スタイルヘルパー ─────────────────────────
function scoreClass(s) {{
  if (s >= 80) return 'score-s';
  if (s >= 65) return 'score-a';
  if (s >= 50) return 'score-b';
  return 'score-c';
}}
function yieldClass(y) {{
  if (y >= 10) return 'yield-high';
  if (y >= 6)  return 'yield-mid';
  return 'yield-low';
}}

// ── 行HTML生成 ───────────────────────────────
function buildRow(d) {{
  const key    = propKey(d);
  const isNew  = !seenCache.has(key);
  const isFav  = favCache.has(key);
  const keyEsc = key.replace(/'/g, "\\'");

  const newBadge = isNew ? '<span class="new-badge">NEW</span>' : '';
  const star     = `<button class="fav-star" title="お気に入り" onclick="toggleFav('${{keyEsc}}')">${{isFav ? '⭐' : '☆'}}</button>`;
  const scoreHtml  = `<span class="score ${{scoreClass(d.score)}}">${{d.score}}</span>`;
  const demandHtml = `<span class="demand demand-${{d.demand_level}}">${{d.demand_emoji}} ${{d.demand_text}}</span>`;
  const yieldHtml  = d.yield_pct > 0 ? `<span class="${{yieldClass(d.yield_pct)}}">${{d.yield_pct}}%</span>` : '-';
  const seenClass  = isNew ? '' : ' seen';
  const linkHtml   = d.url
    ? `<a class="link-btn${{seenClass}}" href="${{d.url}}" target="_blank" rel="noopener" onclick="markSeen('${{keyEsc}}')">${{isNew ? '見る' : '再確認'}}</a>`
    : '';
  const rowClass = (isNew ? 'row-new' : '') + (isFav ? ' row-fav' : '');

  return `<tr class="${{rowClass}}" data-key="${{key}}">
    <td>${{newBadge}}${{star}}</td>
    <td>${{scoreHtml}}</td>
    <td>${{demandHtml}}</td>
    <td>${{d.area}}</td>
    <td class="price">${{d.price}}万</td>
    <td>${{d.layout || '-'}}</td>
    <td>${{yieldHtml}}</td>
    <td class="reason">${{d.reason}}</td>
    <td>${{d.age ? d.age + '年' : '-'}}</td>
    <td>${{d.land || '-'}}</td>
    <td>${{d.building || '-'}}</td>
    <td>${{d.parking}}</td>
    <td style="font-size:11px">${{d.site}}</td>
    <td>${{linkHtml}}</td>
  </tr>`;
}}

// ── テーブル描画 ─────────────────────────────
function renderTable() {{
  const tbody = document.getElementById('tableBody');
  if (filtered.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="14" class="no-data">条件に合う物件が見つかりません</td></tr>';
  }} else {{
    tbody.innerHTML = filtered.map(buildRow).join('');
  }}
  const unreadAll = DATA.filter(d => !seenCache.has(propKey(d))).length;
  document.getElementById('stats').textContent =
    `${{filtered.length}}件表示 / 全${{DATA.length}}件`;
  document.getElementById('unreadCount').textContent =
    unreadAll > 0 ? `未読 ${{unreadAll}}件` : '全て既読';
}}

// ── フィルタ適用 ─────────────────────────────
function applyFilter() {{
  const text = document.getElementById('filterInput').value.toLowerCase();
  const area = document.getElementById('areaFilter').value;
  const site = document.getElementById('siteFilter').value;
  filtered = DATA.filter(d => {{
    if (showUnreadOnly && seenCache.has(propKey(d))) return false;
    if (showFavOnly    && !favCache.has(propKey(d))) return false;
    const matchText = !text || JSON.stringify(d).toLowerCase().includes(text);
    const matchArea = !area || d.area === area;
    const matchSite = !site || d.site === site;
    return matchText && matchArea && matchSite;
  }});
  renderTable();
}}

// ── 既読操作 ────────────────────────────────
function markSeen(key) {{
  seenCache.add(key);
  saveSeen(seenCache);
  // 該当行のNEWバッジとクラスを即時更新
  const row = document.querySelector(`tr[data-key="${{key}}"]`);
  if (row) {{
    row.classList.remove('row-new');
    const badge = row.querySelector('.new-badge');
    if (badge) badge.remove();
    const btn = row.querySelector('.link-btn');
    if (btn) {{ btn.classList.add('seen'); btn.textContent = '再確認'; }}
  }}
  document.getElementById('unreadCount').textContent =
    DATA.filter(d => !seenCache.has(propKey(d))).length > 0
      ? `未読 ${{DATA.filter(d => !seenCache.has(propKey(d))).length}}件` : '全て既読';
  if (showUnreadOnly) applyFilter();
}}

function markAllRead() {{
  DATA.forEach(d => seenCache.add(propKey(d)));
  saveSeen(seenCache);
  applyFilter();
}}

// ── お気に入り操作 ───────────────────────────
function toggleFav(key) {{
  if (favCache.has(key)) favCache.delete(key);
  else favCache.add(key);
  saveFavs(favCache);
  const row = document.querySelector(`tr[data-key="${{key}}"]`);
  if (row) {{
    row.classList.toggle('row-fav', favCache.has(key));
    const star = row.querySelector('.fav-star');
    if (star) star.textContent = favCache.has(key) ? '⭐' : '☆';
  }}
  if (showFavOnly) applyFilter();
}}

// ── フィルタトグル ───────────────────────────
function toggleUnreadFilter() {{
  showUnreadOnly = !showUnreadOnly;
  if (showUnreadOnly) showFavOnly = false;
  document.getElementById('btnUnread').classList.toggle('active', showUnreadOnly);
  document.getElementById('btnFav').classList.remove('active');
  applyFilter();
}}

function toggleFavFilter() {{
  showFavOnly = !showFavOnly;
  if (showFavOnly) showUnreadOnly = false;
  document.getElementById('btnFav').classList.toggle('active', showFavOnly);
  document.getElementById('btnUnread').classList.remove('active');
  applyFilter();
}}

// ── ソート ───────────────────────────────────
function sortTable(col) {{
  const headers = document.querySelectorAll('thead th');
  headers.forEach(h => h.className = '');
  if (sortCol === col) sortDir *= -1; else {{ sortCol = col; sortDir = -1; }}
  headers[col].className = sortDir === -1 ? 'sort-desc' : 'sort-asc';
  const keys = [null,'score','demand_level','area','price','layout','yield_pct','reason','age','land','building'];
  const k = keys[col];
  if (!k) return;
  filtered.sort((a, b) => {{
    const av = a[k] ?? 0;
    const bv = b[k] ?? 0;
    return typeof av === 'string'
      ? av.localeCompare(bv, 'ja') * sortDir
      : (av - bv) * sortDir;
  }});
  renderTable();
}}

// ── 初期化 ───────────────────────────────────
function buildFilters() {{
  const areas = [...new Set(DATA.map(d => d.area))].sort((a,b)=>a.localeCompare(b,'ja'));
  const sites = [...new Set(DATA.map(d => d.site))].sort();
  const areaEl = document.getElementById('areaFilter');
  areas.forEach(a => {{ const o=document.createElement('option'); o.value=a; o.text=a; areaEl.add(o); }});
  const siteEl = document.getElementById('siteFilter');
  sites.forEach(s => {{ const o=document.createElement('option'); o.value=s; o.text=s; siteEl.add(o); }});
}}

buildFilters();
sortTable(1);
</script>
</body>
</html>"""

    out_path = DOCS_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)
