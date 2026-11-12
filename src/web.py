import html
import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from main import MiniSearchEngine

DEFAULT_THEME = os.environ.get("DEFAULT_THEME", "copper")
DEFAULT_MODE = os.environ.get("DEFAULT_MODE", "tfidf")
DEFAULT_FUZZY = os.environ.get("FUZZY_SEARCH", "1") != "0"


def highlight_tokens(text: str, tokens: list[str]) -> str:
    escaped = html.escape(text)
    if not tokens:
        return escaped
    valid = [re.escape(t) for t in set(tokens) if t]
    if not valid:
        return escaped
    pattern = re.compile(r"\b(" + "|".join(valid) + r")\b", re.IGNORECASE)
    return pattern.sub(r"<mark>\1</mark>", escaped)


def render_page(
    engine: MiniSearchEngine,
    query: str = "",
    mode: str = DEFAULT_MODE,
    fuzzy: bool = DEFAULT_FUZZY,
    notice: str = "",
) -> str:
    payload = (
        engine.answer(query, mode=mode, fuzzy=fuzzy)
        if query.strip()
        else {
            "results": [],
            "resolved_tokens": [],
            "corrections": {},
            "elapsed_ms": 0.0,
            "mode": mode,
            "answer": {"summary": "", "bullets": [], "sources": [], "confidence": 0},
        }
    )
    stats = engine.index_stats()
    initial_json = json.dumps({
        "query": query,
        "mode": mode,
        "fuzzy": fuzzy,
        "notice": notice,
        "payload": payload,
        "stats": stats,
    }).replace("</", "<\\/")

    ssr_markers = ""
    if query.strip() and payload["results"]:
        top_doc = html.escape(payload["results"][0]["document"])
        ssr_snip = highlight_tokens(payload["results"][0]["snippet"], payload["resolved_tokens"])
        ssr_markers = f"<!-- SSR:{top_doc}:{ssr_snip} -->"

    return f"""<!doctype html>
<html lang="en" data-theme="{html.escape(DEFAULT_THEME)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MiniSearch &mdash; Editorial Knowledge Studio</title>
  {ssr_markers}
  <style>
    /* 1. Warm Espresso & Terracotta Copper (Default Senior Editorial Dark) */
    :root, [data-theme="copper"] {{
      --bg: #0e0d0b;
      --bg-elevated: #141210;
      --card: #181613;
      --card-subtle: #211e1a;
      --border: #2c2823;
      --border-hover: #463f36;
      --text: #f4f0e8;
      --text-sec: #a69f91;
      --text-muted: #6e685c;
      --accent: #e06d53;
      --accent-fg: #ffffff;
      --accent-soft: rgba(224, 109, 83, 0.14);
      --ok: #52b788;
      --mark-bg: rgba(224, 109, 83, 0.22);
      --mark-text: #f7a08b;
      --shadow: 0 14px 34px -12px rgba(0, 0, 0, 0.6);
    }}

    /* 2. Warm Archival Paper (Editorial Light) */
    [data-theme="paper"] {{
      --bg: #f6f3ec;
      --bg-elevated: #efeae0;
      --card: #ffffff;
      --card-subtle: #f4f0e6;
      --border: #e2dcd0;
      --border-hover: #c5bdb0;
      --text: #1a1815;
      --text-sec: #5c564d;
      --text-muted: #948c7f;
      --accent: #c85a32;
      --accent-fg: #ffffff;
      --accent-soft: rgba(200, 90, 50, 0.1);
      --ok: #2d6a4f;
      --mark-bg: rgba(200, 90, 50, 0.16);
      --mark-text: #8c3718;
      --shadow: 0 8px 24px -8px rgba(26, 24, 21, 0.07);
    }}

    /* 3. Nordic Pine & Sage (Forest Dark) */
    [data-theme="forest"] {{
      --bg: #090d0b;
      --bg-elevated: #0e1411;
      --card: #121a16;
      --card-subtle: #18231e;
      --border: #22312a;
      --border-hover: #354d42;
      --text: #ebf2ee;
      --text-sec: #8fa69a;
      --text-muted: #566b60;
      --accent: #34d399;
      --accent-fg: #062419;
      --accent-soft: rgba(52, 211, 153, 0.13);
      --ok: #34d399;
      --mark-bg: rgba(52, 211, 153, 0.18);
      --mark-text: #6ee7b7;
      --shadow: 0 14px 34px -12px rgba(0, 0, 0, 0.65);
    }}

    /* 4. Graphite & Amber (Technical Dark) */
    [data-theme="graphite"] {{
      --bg: #0b0c0e;
      --bg-elevated: #101216;
      --card: #15171c;
      --card-subtle: #1c1f26;
      --border: #262a34;
      --border-hover: #3d4352;
      --text: #f1f3f5;
      --text-sec: #949ba6;
      --text-muted: #5c6370;
      --accent: #f59e0b;
      --accent-fg: #141109;
      --accent-soft: rgba(245, 158, 11, 0.13);
      --ok: #10b981;
      --mark-bg: rgba(245, 158, 11, 0.2);
      --mark-text: #fcd34d;
      --shadow: 0 14px 34px -12px rgba(0, 0, 0, 0.65);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
      min-height: 100vh;
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
      transition: background .25s ease, color .25s ease;
    }}

    .serif-heading {{
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      font-weight: 500;
      letter-spacing: -0.02em;
    }}

    .mono {{
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-variant-numeric: tabular-nums;
    }}

    .shell {{
      max-width: 1140px;
      margin: 0 auto;
      padding: 1.75rem 1.5rem 5rem;
    }}

    /* Top Navigation & Theme Swatches */
    .navbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
      padding-bottom: 1.25rem;
      margin-bottom: 2.5rem;
      border-bottom: 1px solid var(--border);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: .65rem;
      cursor: pointer;
    }}
    .brand-badge {{
      width: 28px;
      height: 28px;
      border-radius: 7px;
      background: var(--accent);
      color: var(--accent-fg);
      display: grid;
      place-items: center;
      font-family: Georgia, serif;
      font-weight: 700;
      font-size: .95rem;
    }}
    .brand-title {{
      font-family: Georgia, serif;
      font-size: 1.15rem;
      font-weight: 600;
      letter-spacing: -0.02em;
    }}

    .nav-dock {{
      display: flex;
      gap: .25rem;
      background: var(--card);
      border: 1px solid var(--border);
      padding: .25rem;
      border-radius: 11px;
    }}
    .nav-pill {{
      border: none;
      background: transparent;
      color: var(--text-sec);
      padding: .4rem .9rem;
      border-radius: 8px;
      font-size: .82rem;
      font-weight: 500;
      cursor: pointer;
      transition: all .15s;
    }}
    .nav-pill:hover {{ color: var(--text); }}
    .nav-pill.active {{
      background: var(--accent);
      color: var(--accent-fg);
      font-weight: 600;
    }}

    /* Theme Palette Swatch Selector */
    .theme-Dock {{
      display: flex;
      align-items: center;
      gap: .4rem;
      background: var(--card);
      border: 1px solid var(--border);
      padding: .3rem .55rem;
      border-radius: 999px;
    }}
    .swatch {{
      width: 18px;
      height: 18px;
      border-radius: 50%;
      border: 2px solid transparent;
      cursor: pointer;
      transition: transform .15s;
    }}
    .swatch:hover {{ transform: scale(1.18); }}
    .swatch.active {{ border-color: var(--text); transform: scale(1.12); }}

    /* Editorial Search Focal Area */
    .hero {{
      max-width: 740px;
      margin: 0 auto 2.6rem;
      text-align: center;
      position: relative;
    }}
    .hero-title {{
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
      font-size: clamp(2rem, 3.8vw, 2.75rem);
      font-weight: 400;
      letter-spacing: -0.025em;
      margin-bottom: 1.25rem;
      color: var(--text);
    }}
    .search-bar {{
      display: flex;
      align-items: center;
      gap: .65rem;
      background: var(--card);
      border: 1.5px solid var(--border);
      border-radius: 16px;
      padding: .55rem .6rem .55rem 1.2rem;
      box-shadow: var(--shadow);
      transition: border-color .2s;
    }}
    .search-bar:focus-within {{
      border-color: var(--accent);
    }}
    .search-bar input {{
      flex: 1;
      border: none;
      background: transparent;
      color: var(--text);
      font-size: 1rem;
      padding: .42rem 0;
      outline: none;
    }}
    .search-bar input::placeholder {{ color: var(--text-muted); }}
    .kbd-hint {{
      font-size: .7rem;
      color: var(--text-muted);
      background: var(--card-subtle);
      border: 1px solid var(--border);
      padding: .15rem .45rem;
      border-radius: 5px;
    }}
    .btn-primary {{
      background: var(--accent);
      color: var(--accent-fg);
      border: none;
      padding: .55rem 1.15rem;
      border-radius: 11px;
      font-weight: 600;
      font-size: .84rem;
      cursor: pointer;
      transition: opacity .15s;
    }}
    .btn-primary:hover {{ opacity: 0.9; }}
    .btn-secondary {{
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid transparent;
      padding: .55rem .95rem;
      border-radius: 11px;
      font-weight: 600;
      font-size: .84rem;
      cursor: pointer;
      transition: border-color .15s;
    }}
    .btn-secondary:hover {{ border-color: var(--accent); }}
    .btn-ghost {{
      background: transparent;
      color: var(--text-sec);
      border: 1px solid var(--border);
      padding: .36rem .75rem;
      border-radius: 9px;
      font-size: .78rem;
      font-weight: 500;
      cursor: pointer;
      transition: all .15s;
    }}
    .btn-ghost:hover {{ color: var(--text); border-color: var(--border-hover); background: var(--card-subtle); }}

    .suggest-dropdown {{
      position: absolute;
      left: 0;
      right: 0;
      top: calc(100% + 6px);
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: var(--shadow);
      z-index: 50;
      display: none;
      overflow: hidden;
      text-align: left;
    }}
    .suggest-row {{
      padding: .6rem 1.15rem;
      display: flex;
      justify-content: space-between;
      cursor: pointer;
      font-size: .88rem;
    }}
    .suggest-row:hover {{ background: var(--card-subtle); color: var(--accent); }}

    /* Asymmetrical Bento Grid */
    .bento-grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 1.1rem;
    }}
    .bento-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 1.5rem 1.6rem;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: border-color .18s ease, transform .18s ease;
    }}
    .bento-card:hover {{ border-color: var(--border-hover); }}
    .bento-card.clickable {{ cursor: pointer; }}
    .bento-card.clickable:hover {{ transform: translateY(-2px); border-color: var(--accent); }}

    .span-12 {{ grid-column: span 12; }}
    .span-8 {{ grid-column: span 8; }}
    .span-7 {{ grid-column: span 7; }}
    .span-6 {{ grid-column: span 6; }}
    .span-5 {{ grid-column: span 5; }}
    .span-4 {{ grid-column: span 4; }}
    .span-3 {{ grid-column: span 3; }}

    @media (max-width: 920px) {{
      .span-8, .span-7, .span-6, .span-5, .span-4, .span-3 {{ grid-column: span 12; }}
    }}

    .card-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: .9rem;
    }}
    .card-title {{
      font-family: "Iowan Old Style", Georgia, serif;
      font-size: 1.15rem;
      font-weight: 500;
      letter-spacing: -0.01em;
    }}
    .label {{
      font-size: .74rem;
      color: var(--text-muted);
    }}
    .clamp-2 {{
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      color: var(--text-sec);
      font-size: .88rem;
      line-height: 1.6;
    }}
    .badge {{
      font-size: .68rem;
      font-weight: 600;
      padding: .18rem .5rem;
      border-radius: 6px;
      background: var(--accent-soft);
      color: var(--accent);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    .pulse-ok {{
      display: inline-flex;
      align-items: center;
      gap: .38rem;
      font-size: .74rem;
      color: var(--text-sec);
    }}
    .pulse-ok::before {{
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--ok);
    }}

    /* Rows, Chips, Dropzone */
    .row-list {{ display: flex; flex-direction: column; gap: .45rem; }}
    .row-item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: .65rem .9rem;
      border-radius: 11px;
      background: var(--card-subtle);
      border: 1px solid transparent;
      cursor: pointer;
      transition: border-color .15s;
    }}
    .row-item:hover {{ border-color: var(--accent); }}

    .chip-wrap {{ display: flex; flex-wrap: wrap; gap: .45rem; }}
    .chip {{
      background: var(--card-subtle);
      border: 1px solid var(--border);
      color: var(--text-sec);
      padding: .38rem .8rem;
      border-radius: 999px;
      font-size: .8rem;
      cursor: pointer;
      transition: all .15s;
    }}
    .chip:hover {{ color: var(--text); border-color: var(--accent); }}

    .dropzone {{
      border: 1.5px dashed var(--border-hover);
      border-radius: 13px;
      padding: 1.45rem 1rem;
      text-align: center;
      cursor: pointer;
      background: var(--bg-elevated);
      transition: border-color .15s, background .15s;
    }}
    .dropzone:hover, .dropzone.dragover {{
      border-color: var(--accent);
      background: var(--accent-soft);
    }}

    .spark-bars {{
      display: flex;
      align-items: flex-end;
      gap: 6px;
      height: 46px;
      margin-top: .75rem;
    }}
    .spark-col {{
      flex: 1;
      border-radius: 4px 4px 1px 1px;
      background: var(--accent);
      opacity: 0.65;
      transition: opacity .15s;
    }}
    .bento-card:hover .spark-col {{ opacity: 1; }}

    .ring-wrap {{
      position: relative;
      width: 44px;
      height: 44px;
      display: grid;
      place-items: center;
    }}
    .ring-wrap svg {{ transform: rotate(-90deg); }}
    .ring-num {{
      position: absolute;
      font-size: .68rem;
      font-weight: 600;
      color: var(--text);
    }}

    mark {{
      background: var(--mark-bg);
      color: var(--mark-text);
      padding: .04rem .26rem;
      border-radius: 4px;
      font-weight: 600;
    }}

    .modal-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(4px);
      display: none;
      place-items: center;
      z-index: 100;
      padding: 1rem;
    }}
    .modal-card {{
      background: var(--card);
      border: 1px solid var(--border-hover);
      border-radius: 18px;
      padding: 1.6rem;
      width: 100%;
      max-width: 460px;
      box-shadow: var(--shadow);
    }}
    .field {{
      width: 100%;
      background: var(--card-subtle);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 10px;
      padding: .62rem .82rem;
      font-family: inherit;
      font-size: .88rem;
      margin: .35rem 0 .85rem;
      outline: none;
    }}
    .field:focus {{ border-color: var(--accent); }}
    .toast {{
      position: fixed;
      bottom: 1.5rem;
      right: 1.5rem;
      background: var(--card);
      border: 1px solid var(--accent);
      color: var(--text);
      padding: .65rem 1.15rem;
      border-radius: 11px;
      box-shadow: var(--shadow);
      display: none;
      font-size: .84rem;
      z-index: 95;
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="navbar">
      <div class="brand" onclick="setView('home')">
        <div class="brand-badge">M</div>
        <span class="brand-title">MiniSearch</span>
      </div>

      <nav class="nav-dock">
        <button class="nav-pill active" data-view="home" onclick="setView('home')">Home</button>
        <button class="nav-pill" data-view="results" onclick="setView('results')">Search</button>
        <button class="nav-pill" data-view="ask" onclick="setView('ask')">Ask AI</button>
        <button class="nav-pill" data-view="library" onclick="setView('library')">Library</button>
        <button class="nav-pill" data-view="viewer" onclick="setView('viewer')">Viewer</button>
      </nav>

      <div class="theme-Dock" title="Choose UI Theme">
        <span class="label" style="margin-right:.2rem;">Theme</span>
        <button class="swatch active" data-t="copper" style="background:#e06d53" onclick="setTheme('copper')" title="Warm Espresso & Copper"></button>
        <button class="swatch" data-t="paper" style="background:#f6f3ec;border-color:#c85a32" onclick="setTheme('paper')" title="Archival Paper Light"></button>
        <button class="swatch" data-t="forest" style="background:#34d399" onclick="setTheme('forest')" title="Nordic Pine & Jade"></button>
        <button class="swatch" data-t="graphite" style="background:#f59e0b" onclick="setTheme('graphite')" title="Graphite & Amber"></button>
      </div>
    </header>

    <section class="hero" id="heroSection">
      <h1 class="hero-title" id="heroHeading">What would you like to find?</h1>
      <form class="search-bar" onsubmit="handleSearchSubmit(event)">
        <input type="search" id="globalSearchInput" autocomplete="off" placeholder="Search documents, phrases, or ask a question..." autofocus>
        <span class="kbd-hint mono">/</span>
        <button type="submit" class="btn-primary">Search</button>
        <button type="button" class="btn-secondary" onclick="triggerAskAI()">Ask AI</button>
      </form>
      <div class="suggest-dropdown" id="suggestDropdown"></div>
    </section>

    <main id="bentoViewport"></main>
  </div>

  <div class="modal-backdrop" id="uploadModal" onclick="if(event.target===this)closeModal()">
    <div class="modal-card">
      <div class="card-head">
        <span class="card-title">Add Document</span>
        <button class="btn-ghost" onclick="closeModal()">Esc</button>
      </div>
      <form onsubmit="submitNewDoc(event)">
        <input class="field" id="newDocName" required placeholder="Filename (e.g. architecture.txt)">
        <textarea class="field" id="newDocContent" rows="5" required placeholder="Paste document text..."></textarea>
        <div style="display:flex;justify-content:flex-end;">
          <button type="submit" class="btn-primary">Save &amp; Index</button>
        </div>
      </form>
    </div>
  </div>

  <input type="file" id="hiddenFileInput" accept=".txt,.md,.csv,.json,.docx" multiple style="display:none" onchange="handleFilesSelected(this.files)">
  <div class="toast" id="toastBanner"></div>

  <script>
    const STATE = {initial_json};
    let currentView = STATE.query ? 'results' : 'home';
    let activeDocName = (STATE.stats.documents[0] && STATE.stats.documents[0].name) || '';

    const DEFAULT_RECENT = [
      "What is Python used for?",
      "neural networks RAG",
      "sql vs nosql databases",
      "java virtual machine",
      "javascript nodejs"
    ];

    function getRecentSearches() {{
      try {{
        const s = JSON.parse(localStorage.getItem('mse_recent') || 'null');
        return Array.isArray(s) && s.length ? s : DEFAULT_RECENT;
      }} catch {{ return DEFAULT_RECENT; }}
    }}

    function saveRecentSearch(q) {{
      if (!q || !q.trim()) return;
      const clean = q.trim();
      const list = [clean, ...getRecentSearches().filter(x => x.toLowerCase() !== clean.toLowerCase())].slice(0, 6);
      try {{ localStorage.setItem('mse_recent', JSON.stringify(list)); }} catch {{}}
    }}

    function esc(str) {{
      const d = document.createElement('div');
      d.textContent = str ?? '';
      return d.innerHTML;
    }}

    function highlightHTML(text, tokens) {{
      let safe = esc(text);
      if (!tokens || !tokens.length) return safe;
      const valid = [...new Set(tokens)].filter(Boolean).map(t => t.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&'));
      if (!valid.length) return safe;
      const re = new RegExp('\\\\b(' + valid.join('|') + ')\\\\b', 'gi');
      return safe.replace(re, '<mark>$1</mark>');
    }}

    function scoreRingSVG(pct, label) {{
      const r = 18;
      const c = 2 * Math.PI * r;
      const offset = c - (pct / 100) * c;
      return `
        <div class="ring-wrap mono" title="Score: ${{label}}">
          <svg width="44" height="44">
            <circle cx="22" cy="22" r="${{r}}" fill="none" stroke="var(--border)" stroke-width="3"/>
            <circle cx="22" cy="22" r="${{r}}" fill="none" stroke="var(--accent)" stroke-width="3"
                    stroke-dasharray="${{c.toFixed(1)}}" stroke-dashoffset="${{offset.toFixed(1)}}" stroke-linecap="round"/>
          </svg>
          <span class="ring-num">${{pct}}%</span>
        </div>
      `;
    }}

    function showToast(msg) {{
      const el = document.getElementById('toastBanner');
      el.textContent = msg;
      el.style.display = 'block';
      setTimeout(() => {{ el.style.display = 'none'; }}, 2600);
    }}

    function setTheme(name) {{
      document.documentElement.setAttribute('data-theme', name);
      document.querySelectorAll('.swatch').forEach(s => s.classList.toggle('active', s.dataset.t === name));
      try {{ localStorage.setItem('mse_palette', name); }} catch {{}}
    }}

    function setView(view) {{
      currentView = view;
      document.querySelectorAll('.nav-pill').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.view === view);
      }});
      const hero = document.getElementById('heroSection');
      const heading = document.getElementById('heroHeading');
      hero.style.display = (view === 'viewer' || view === 'library') ? 'none' : 'block';
      if (view === 'home') heading.textContent = 'What would you like to find?';
      else if (view === 'results') heading.textContent = 'Ranked Documents';
      else if (view === 'ask') heading.textContent = 'Ask AI';
      render();
    }}

    async function runQuery(q, targetView = 'results') {{
      document.getElementById('globalSearchInput').value = q;
      if (q.trim()) saveRecentSearch(q);
      const res = await fetch(`/api/search?q=${{encodeURIComponent(q)}}&mode=${{encodeURIComponent(STATE.mode)}}&fuzzy=${{STATE.fuzzy ? '1' : '0'}}`);
      STATE.payload = await res.json();
      STATE.query = q;
      setView(targetView);
    }}

    function handleSearchSubmit(e) {{
      e.preventDefault();
      const q = document.getElementById('globalSearchInput').value.trim();
      document.getElementById('suggestDropdown').style.display = 'none';
      if (!q) {{ setView('home'); return; }}
      runQuery(q, currentView === 'ask' ? 'ask' : 'results');
    }}

    function triggerAskAI() {{
      const q = document.getElementById('globalSearchInput').value.trim() || 'What is Python used for?';
      runQuery(q, 'ask');
    }}

    function openViewer(docName) {{
      activeDocName = docName;
      setView('viewer');
    }}

    /* 1. MAIN SEARCH PAGE */
    function renderHome() {{
      const docs = STATE.stats.documents.slice(0, 4);
      const maxTok = Math.max(...STATE.stats.documents.map(d => d.tokens), 1);

      const recentDocs = docs.map(d => `
        <div class="row-item" onclick="openViewer('${{esc(d.name)}}')">
          <div style="display:flex;align-items:center;gap:.65rem;">
            <span class="badge">${{esc(d.ext)}}</span>
            <span style="font-size:.9rem;font-weight:500;">${{esc(d.name)}}</span>
          </div>
          <span class="pulse-ok mono">${{esc(d.uploaded_at)}}</span>
        </div>
      `).join('');

      const bars = STATE.stats.documents.slice(0, 8).map(d => {{
        const h = Math.max(22, Math.round((d.tokens / maxTok) * 100));
        return `<div class="spark-col" style="height:${{h}}%" title="${{esc(d.name)}}: ${{d.tokens}} words"></div>`;
      }}).join('');

      const recentChips = getRecentSearches().map(q => `
        <button class="chip" onclick="runQuery('${{esc(q).replace(/'/g, "\\'")}}', 'results')">${{esc(q)}}</button>
      `).join('');

      return `
        <div class="bento-grid">
          <div class="bento-card span-7">
            <div>
              <div class="card-head">
                <span class="card-title">Recent Documents</span>
                <button class="btn-ghost" onclick="setView('library')">All (${{STATE.stats.total_docs}}) &rarr;</button>
              </div>
              <div class="row-list">${{recentDocs}}</div>
            </div>
          </div>

          <div class="bento-card span-5">
            <div>
              <div class="card-head">
                <span class="card-title">Upload Document</span>
                <button class="btn-ghost" onclick="openModal()">Paste text</button>
              </div>
              <div class="dropzone"
                   onclick="document.getElementById('hiddenFileInput').click()"
                   ondragover="event.preventDefault();this.classList.add('dragover')"
                   ondragleave="this.classList.remove('dragover')"
                   ondrop="handleDrop(event)">
                <div style="font-size:.9rem;font-weight:500;">Drop files or click to browse</div>
                <div class="label" style="margin-top:.25rem;">.TXT, .MD, .DOCX, .CSV, .JSON</div>
              </div>
            </div>
          </div>

          <div class="bento-card span-5">
            <div>
              <div class="card-head"><span class="card-title">Recent Searches</span></div>
              <div class="chip-wrap">${{recentChips}}</div>
            </div>
          </div>

          <div class="bento-card clickable span-4" onclick="setView('results')">
            <div class="card-head">
              <span class="card-title">Corpus Index</span>
              <span class="badge">${{STATE.stats.unique_terms}} terms</span>
            </div>
            <div class="spark-bars">${{bars}}</div>
          </div>

          <div class="bento-card clickable span-3" onclick="triggerAskAI()">
            <div class="card-head"><span class="badge">AI</span></div>
            <div>
              <div class="card-title" style="margin-bottom:.15rem;">Ask AI &rarr;</div>
              <div class="label">Synthesized answers</div>
            </div>
          </div>
        </div>
      `;
    }}

    /* 2. DOCUMENT LIBRARY */
    function renderLibrary() {{
      const cards = STATE.stats.documents.map((d, i) => `
        <div class="bento-card ${{i < 2 ? 'span-6' : 'span-4'}}">
          <div>
            <div class="card-head">
              <span class="badge">${{esc(d.ext)}}</span>
              <span class="pulse-ok">${{esc(d.status)}}</span>
            </div>
            <div class="card-title" style="margin-bottom:.35rem;">${{esc(d.name)}}</div>
            <p class="clamp-2">${{esc(d.preview)}}</p>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:1.25rem;padding-top:.85rem;border-top:1px solid var(--border);">
            <span class="label mono">${{esc(d.uploaded_at)}}</span>
            <div style="display:flex;gap:.4rem;">
              <button class="btn-ghost" onclick="openViewer('${{esc(d.name)}}')">Open</button>
              <button class="btn-ghost" onclick="deleteDoc('${{esc(d.name)}}')">Delete</button>
            </div>
          </div>
        </div>
      `).join('');

      return `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">
          <h2 class="serif-heading" style="font-size:1.65rem;">Document Library</h2>
          <button class="btn-primary" onclick="openModal()">+ New Document</button>
        </div>
        <div class="bento-grid">
          <div class="bento-card span-4">
            <div class="card-head"><span class="card-title">Upload</span></div>
            <div class="dropzone"
                 onclick="document.getElementById('hiddenFileInput').click()"
                 ondragover="event.preventDefault();this.classList.add('dragover')"
                 ondragleave="this.classList.remove('dragover')"
                 ondrop="handleDrop(event)">
              <div style="font-size:.88rem;font-weight:500;">Drop file to index</div>
              <div class="label" style="margin-top:.2rem;">Instant indexing</div>
            </div>
          </div>
          ${{cards}}
        </div>
      `;
    }}

    /* 3. SEARCH RESULTS */
    function renderResults() {{
      const p = STATE.payload;
      const results = p.results || [];
      const qTokens = p.resolved_tokens || [];
      const maxScore = Math.max(...results.map(r => r.score), 0.0001);

      const listHTML = results.length ? results.map(r => {{
        const pct = Math.min(99, Math.max(18, Math.round((r.score / maxScore) * 100)));
        return `
          <div class="bento-card clickable" style="margin-bottom:.9rem;" onclick="openViewer('${{esc(r.document)}}')">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;">
              <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:.55rem;margin-bottom:.35rem;">
                  <span class="badge">${{esc(r.ext || 'TXT')}}</span>
                  <span class="card-title">${{esc(r.document)}}</span>
                </div>
                <p class="clamp-2">${{highlightHTML(r.snippet, qTokens)}}</p>
              </div>
              ${{scoreRingSVG(pct, r.score.toFixed(4))}}
            </div>
          </div>
        `;
      }}).join('') : `
        <div class="bento-card">
          <div class="card-title" style="margin-bottom:.3rem;">No matching documents</div>
          <p class="clamp-2">Try searching for Python, Java, JavaScript, neural networks, or databases.</p>
        </div>
      `;

      return `
        <div class="bento-grid">
          <div class="span-8">${{listHTML}}</div>

          <div class="span-4">
            <div class="bento-card">
              <div class="card-head">
                <span class="card-title">Retrieval</span>
                <span class="badge">${{p.elapsed_ms || 0}} ms</span>
              </div>
              <div style="display:flex;flex-direction:column;gap:.8rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <span class="label">Algorithm</span>
                  <div style="display:flex;gap:.35rem;">
                    <button class="btn-ghost" style="${{STATE.mode==='tfidf'?'border-color:var(--accent);color:var(--text);':''}}" onclick="STATE.mode='tfidf';runQuery(STATE.query,'results')">TF-IDF</button>
                    <button class="btn-ghost" style="${{STATE.mode==='bm25'?'border-color:var(--accent);color:var(--text);':''}}" onclick="STATE.mode='bm25';runQuery(STATE.query,'results')">BM25</button>
                  </div>
                </div>
                <label style="display:flex;justify-content:space-between;align-items:center;cursor:pointer;">
                  <span class="label">Fuzzy typo match</span>
                  <input type="checkbox" ${{STATE.fuzzy?'checked':''}} onchange="STATE.fuzzy=this.checked;runQuery(STATE.query,'results')">
                </label>
              </div>
            </div>
          </div>
        </div>
      `;
    }}

    /* 4. ASK AI */
    function renderAskAI() {{
      const p = STATE.payload;
      const qTokens = p.resolved_tokens || [];
      const ans = p.answer || {{ summary: '', bullets: [], sources: [], confidence: 0 }};
      const sources = p.results || [];

      const suggestions = [
        "What is Python used for?",
        "How do LLMs use RAG?",
        "SQL vs NoSQL databases",
        "How does JVM work?"
      ];

      const sourcesHTML = sources.length ? sources.map(r => `
        <div class="row-item" onclick="openViewer('${{esc(r.document)}}')">
          <div>
            <div style="font-size:.86rem;font-weight:500;">${{esc(r.document)}}</div>
            <div class="clamp-2" style="font-size:.78rem;">${{highlightHTML(r.snippet, qTokens)}}</div>
          </div>
        </div>
      `).join('') : `<div class="label">Ask a question to view sources.</div>`;

      return `
        <div class="bento-grid">
          <div class="bento-card span-8">
            <div>
              <div class="card-head">
                <span class="badge">Synthesized Answer</span>
                ${{ans.confidence ? `<span class="pulse-ok mono">${{ans.confidence}}% confidence</span>` : ''}}
              </div>
              <div class="card-title" style="font-size:1.3rem;margin-bottom:.75rem;">
                ${{STATE.query ? esc(STATE.query) : 'Select a question below'}}
              </div>
              <p style="font-size:.98rem;line-height:1.75;margin-bottom:1rem;">
                ${{ans.summary ? highlightHTML(ans.summary, qTokens) : 'Type any question above to synthesize an answer directly from your indexed corpus.'}}
              </p>
              ${{(ans.bullets || []).length ? `
                <ul style="padding-left:1.15rem;color:var(--text-sec);font-size:.88rem;display:flex;flex-direction:column;gap:.45rem;">
                  ${{ans.bullets.map(b => `<li>${{highlightHTML(b.text, qTokens)}} <span class="badge" style="cursor:pointer;" onclick="openViewer('${{esc(b.source)}}')">${{esc(b.source)}}</span></li>`).join('')}}
                </ul>
              ` : ''}}
            </div>
          </div>

          <div class="bento-card span-4">
            <div>
              <div class="card-head">
                <span class="card-title">Sources</span>
                <span class="badge">${{sources.length}}</span>
              </div>
              <div class="row-list">${{sourcesHTML}}</div>
            </div>
          </div>

          ${{suggestions.map(q => `
            <div class="bento-card clickable span-3" onclick="runQuery('${{esc(q).replace(/'/g, "\\'")}}', 'ask')">
              <span class="label" style="margin-bottom:.3rem;">Suggested</span>
              <div style="font-size:.88rem;font-weight:500;">${{esc(q)}}</div>
            </div>
          `).join('')}}
        </div>
      `;
    }}

    /* 5. DOCUMENT VIEWER */
    function renderViewer() {{
      const docs = STATE.stats.documents;
      const doc = docs.find(d => d.name === activeDocName) || docs[0];
      if (!doc) return `<div class="bento-card">No document selected.</div>`;

      const qTokens = STATE.payload.resolved_tokens || [];
      const sections = (doc.sections && doc.sections.length) ? doc.sections : [doc.content];

      return `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem;flex-wrap:wrap;gap:.6rem;">
          <button class="btn-ghost" onclick="setView('results')">&larr; Back</button>
          <div class="chip-wrap">
            ${{docs.map(d => `<button class="chip" style="${{d.name===doc.name?'border-color:var(--accent);color:var(--text);':''}}" onclick="openViewer('${{esc(d.name)}}')">${{esc(d.name)}}</button>`).join('')}}
          </div>
        </div>

        <div class="bento-grid">
          <div class="bento-card span-8">
            <div>
              <div class="card-head">
                <span class="badge">${{esc(doc.ext)}}</span>
                <span class="pulse-ok">${{esc(doc.status)}}</span>
              </div>
              <h2 class="serif-heading" style="font-size:1.65rem;margin-bottom:1.25rem;">${{esc(doc.name)}}</h2>
              <div style="display:flex;flex-direction:column;gap:.8rem;">
                ${{sections.map((s, idx) => `
                  <p id="sec-${{idx}}" style="font-size:.96rem;line-height:1.78;padding:.8rem 1.05rem;border-radius:11px;background:var(--card-subtle);">
                    ${{highlightHTML(s, qTokens)}}
                  </p>
                `).join('')}}
              </div>
            </div>
          </div>

          <div class="span-4" style="display:flex;flex-direction:column;gap:1rem;">
            <div class="bento-card">
              <div class="card-head"><span class="card-title">Metadata</span></div>
              <div style="display:flex;flex-direction:column;gap:.5rem;font-size:.84rem;">
                <div style="display:flex;justify-content:space-between;"><span class="label">Uploaded</span><span class="mono">${{esc(doc.uploaded_at)}}</span></div>
                <div style="display:flex;justify-content:space-between;"><span class="label">Tokens</span><span class="mono">${{doc.tokens}}</span></div>
                <div style="display:flex;justify-content:space-between;"><span class="label">Unique terms</span><span class="mono">${{doc.unique_terms}}</span></div>
              </div>
              <div style="margin-top:1rem;">
                <div class="label" style="margin-bottom:.45rem;">Top Keywords</div>
                <div class="chip-wrap">
                  ${{(doc.top_terms || []).map(t => `<button class="chip" onclick="runQuery('${{esc(t)}}','results')">${{esc(t)}}</button>`).join('')}}
                </div>
              </div>
            </div>

            <div class="bento-card">
              <div class="card-head"><span class="card-title">Sections</span></div>
              <div class="row-list">
                ${{sections.map((s, idx) => `
                  <div class="row-item" onclick="document.getElementById('sec-${{idx}}').scrollIntoView({{behavior:'smooth',block:'center'}})">
                    <span style="font-size:.8rem;color:var(--text-sec);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">§${{idx + 1}} ${{esc(s.slice(0, 36))}}...</span>
                  </div>
                `).join('')}}
              </div>
            </div>
          </div>
        </div>
      `;
    }}

    function render() {{
      const vp = document.getElementById('bentoViewport');
      if (currentView === 'home') vp.innerHTML = renderHome();
      else if (currentView === 'library') vp.innerHTML = renderLibrary();
      else if (currentView === 'results') vp.innerHTML = renderResults();
      else if (currentView === 'ask') vp.innerHTML = renderAskAI();
      else if (currentView === 'viewer') vp.innerHTML = renderViewer();
    }}

    function openModal() {{ document.getElementById('uploadModal').style.display = 'grid'; }}
    function closeModal() {{ document.getElementById('uploadModal').style.display = 'none'; }}

    async function refreshStats() {{
      const res = await fetch('/api/index');
      STATE.stats = await res.json();
    }}

    async function submitNewDoc(e) {{
      e.preventDefault();
      const filename = document.getElementById('newDocName').value.trim();
      const content = document.getElementById('newDocContent').value.trim();
      if (!filename || !content) return;
      await fetch('/api/documents', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ filename, content }})
      }});
      document.getElementById('newDocName').value = '';
      document.getElementById('newDocContent').value = '';
      closeModal();
      await refreshStats();
      showToast(`Indexed ${{filename}}`);
      render();
    }}

    async function handleFilesSelected(fileList) {{
      for (const file of fileList) {{
        const text = await file.text();
        await fetch('/api/documents', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ filename: file.name, content: text }})
        }});
        showToast(`Indexed ${{file.name}}`);
      }}
      await refreshStats();
      render();
    }}

    function handleDrop(e) {{
      e.preventDefault();
      e.currentTarget.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length) handleFilesSelected(e.dataTransfer.files);
    }}

    async function deleteDoc(name) {{
      await fetch(`/api/documents?name=${{encodeURIComponent(name)}}`, {{ method: 'DELETE' }});
      await refreshStats();
      showToast(`Deleted ${{name}}`);
      render();
    }}

    const sInput = document.getElementById('globalSearchInput');
    const sDrop = document.getElementById('suggestDropdown');
    let sTimer = null;
    sInput.addEventListener('input', () => {{
      clearTimeout(sTimer);
      const q = sInput.value.trim();
      if (q.length < 2) {{ sDrop.style.display = 'none'; return; }}
      sTimer = setTimeout(async () => {{
        const res = await fetch('/api/suggest?q=' + encodeURIComponent(q));
        const data = await res.json();
        if (!data.suggestions.length) {{ sDrop.style.display = 'none'; return; }}
        sDrop.innerHTML = data.suggestions.map(s => `
          <div class="suggest-row" onclick="sInput.value='${{esc(s.term).replace(/'/g,"\\'")}}';sDrop.style.display='none';runQuery(sInput.value, currentView==='ask'?'ask':'results')">
            <span>${{esc(s.term)}}</span>
            <span class="label mono">${{s.df}} docs</span>
          </div>
        `).join('');
        sDrop.style.display = 'block';
      }}, 90);
    }});

    document.addEventListener('keydown', e => {{
      if (e.key === '/' && document.activeElement !== sInput && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) {{
        e.preventDefault();
        sInput.focus();
      }}
      if (e.key === 'Escape') closeModal();
    }});

    document.addEventListener('click', e => {{
      if (!e.target.closest('.hero')) sDrop.style.display = 'none';
    }});

    try {{
      const saved = localStorage.getItem('mse_palette');
      if (saved) setTheme(saved);
    }} catch {{}}
    if (STATE.query) sInput.value = STATE.query;
    setView(currentView);
  </script>
</body>
</html>"""


def make_handler(engine: MiniSearchEngine):
    class SearchHandler(BaseHTTPRequestHandler):
        def _send_json(self, data: dict, status: int = 200) -> None:
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            mode = params.get("mode", ["tfidf"])[0]
            fuzzy = params.get("fuzzy", ["1"])[0] != "0"

            if parsed.path == "/api/search":
                self._send_json(engine.answer(query, mode=mode, fuzzy=fuzzy))
                return
            if parsed.path == "/api/suggest":
                self._send_json({"suggestions": engine.suggest(query)})
                return
            if parsed.path == "/api/index":
                self._send_json(engine.index_stats())
                return

            notice = params.get("notice", [""])[0]
            body = render_page(engine, query=query, mode=mode, fuzzy=fuzzy, notice=notice).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/documents":
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8", errors="ignore")
                ctype = self.headers.get("Content-Type", "")
                if "application/json" in ctype:
                    data = json.loads(raw or "{}")
                    filename = data.get("filename", "new_doc.txt")
                    content = data.get("content", "")
                    saved = engine.add_document(filename, content)
                    self._send_json({"saved": saved, "total_docs": len(engine.documents)}, 201)
                    return

                form = parse_qs(raw)
                filename = form.get("filename", ["new_doc.txt"])[0]
                content = form.get("content", [""])[0]
                saved = engine.add_document(filename, content)
                self.send_response(303)
                self.send_header("Location", f"/?notice=Indexed+{saved}+successfully")
                self.end_headers()
                return

            self._send_json({"error": "Not found"}, 404)

        def do_DELETE(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/documents":
                params = parse_qs(parsed.query)
                name = params.get("name", [""])[0]
                removed = engine.delete_document(name)
                self._send_json({"deleted": removed, "name": name})
                return
            self._send_json({"error": "Not found"}, 404)

        def log_message(self, format, *args):
            pass

    return SearchHandler


def run_server(port: int = 8000, doc_dir: str = "documents") -> None:
    engine = MiniSearchEngine(doc_dir)
    server = HTTPServer(("127.0.0.1", port), make_handler(engine))
    print(f"Serving Mini Search Engine at http://127.0.0.1:{port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
