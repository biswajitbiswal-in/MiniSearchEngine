import html
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from main import MiniSearchEngine
from src.tokenizer import tokenize


def highlight_tokens(text: str, tokens: list[str]) -> str:
    escaped = html.escape(text)
    if not tokens:
        return escaped
    pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in set(tokens)) + r")\b", re.IGNORECASE)
    return pattern.sub(r"<mark>\1</mark>", escaped)


def render_page(engine: MiniSearchEngine, query: str = "") -> str:
    payload = engine.answer(query) if query.strip() else {"results": [], "answer": {"summary": "", "bullets": [], "sources": []}}
    results = payload["results"]
    ans = payload["answer"]
    q_tokens = tokenize(query)
    escaped_q = html.escape(query)

    sample_queries = [
        "python machine learning frameworks",
        "java enterprise jvm",
        "javascript web nodejs",
        "object oriented programming",
    ]
    chips_html = "".join(
        f'<a class="chip" href="/?q={html.escape(q)}">{html.escape(q)}</a>' for q in sample_queries
    )

    content_html = ""
    if query.strip():
        if results:
            # Synthesized Answer Card
            answer_html = ""
            if ans["summary"]:
                summary_hl = highlight_tokens(ans["summary"], q_tokens)
                bullets_hl = "".join(
                    f"<li>{highlight_tokens(b['text'], q_tokens)} <span class='cite'>{html.escape(b['source'])}</span></li>"
                    for b in ans["bullets"]
                )
                sources_badges = "".join(
                    f"<span class='source-pill'>{html.escape(src)}</span>" for src in ans["sources"]
                )
                answer_html = f"""
                <section class="answer-card">
                  <div class="answer-header">
                    <span class="sparkle">&#10024; Synthesized Answer</span>
                    <div class="sources">{sources_badges}</div>
                  </div>
                  <p class="answer-summary">{summary_hl}</p>
                  <ul class="answer-bullets">{bullets_hl}</ul>
                </section>
                """

            max_score = max((r["score"] for r in results), default=1.0) or 1.0
            items = []
            for rank, r in enumerate(results, 1):
                doc = r["document"]
                score = r["score"]
                pct = min(100, max(12, int((score / max_score) * 100)))
                snippet = highlight_tokens(r["snippet"], q_tokens)
                full_text = highlight_tokens(engine.documents.get(doc, ""), q_tokens)
                matched_tags = "".join(
                    f"<span class='term-tag'>{html.escape(t)}</span>" for t in r.get("matched_terms", [])
                )
                items.append(
                    f"<article class='card'>"
                    f"  <div class='card-top'>"
                    f"    <div class='doc-title'><span class='rank'>#{rank}</span> <strong>{html.escape(doc)}</strong></div>"
                    f"    <div class='score-wrap' title='Cosine Similarity Score'>"
                    f"      <div class='score-bar'><div class='score-fill' style='width:{pct}%'></div></div>"
                    f"      <span class='badge'>TF-IDF {score:.4f}</span>"
                    f"    </div>"
                    f"  </div>"
                    f"  <p class='snippet'>{snippet}</p>"
                    f"  <div class='card-footer'>"
                    f"    <div class='terms'>Matched: {matched_tags}</div>"
                    f"    <details><summary>Read full document</summary><pre>{full_text}</pre></details>"
                    f"  </div>"
                    f"</article>"
                )
            content_html = (
                answer_html
                + f"<div class='results-header'>Ranked Documents ({len(results)} match{'es' if len(results) != 1 else ''})</div>"
                + "".join(items)
            )
        else:
            content_html = (
                f"<div class='empty-state'>"
                f"  <h3>No matching documents for &ldquo;{escaped_q}&rdquo;</h3>"
                f"  <p>Try searching for keywords like <code>python</code>, <code>java</code>, <code>javascript</code>, <code>web</code>, or <code>frameworks</code>.</p>"
                f"</div>"
            )
    else:
        doc_cards = "".join(
            f"<div class='corpus-item'><strong>{html.escape(name)}</strong><span>{len(engine.tokenized_docs[name])} tokens</span></div>"
            for name in engine.documents
        )
        content_html = f"""
        <div class="welcome-card">
          <h3>Indexed Corpus Overview</h3>
          <p>Enter any keyword or natural question above. The engine tokenizes your query, looks up postings in the inverted index, ranks documents by TF-IDF Cosine Similarity, and synthesizes a direct answer.</p>
          <div class="corpus-grid">{doc_cards}</div>
        </div>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mini Search Engine</title>
  <style>
    :root {{
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-hover: #263449;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.15);
      --answer-bg: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95));
      --mark-bg: rgba(250, 204, 21, 0.25);
      --mark-text: #fde047;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top, #1e293b 0%, var(--bg) 55%);
      color: var(--text);
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      min-height: 100vh;
      line-height: 1.6;
    }}
    .container {{ max-width: 840px; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }}
    header.hero {{ text-align: center; margin-bottom: 1.75rem; }}
    .title {{
      font-size: 2.25rem;
      font-weight: 800;
      margin: 0 0 .4rem;
      background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.02em;
    }}
    .subtitle {{ color: var(--muted); font-size: .95rem; margin: 0; }}
    .search-box {{
      display: flex;
      gap: .6rem;
      background: var(--surface);
      padding: .5rem;
      border-radius: 14px;
      border: 1px solid var(--border);
      box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
      transition: border-color .2s, box-shadow .2s;
    }}
    .search-box:focus-within {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }}
    .search-box input {{
      flex: 1;
      background: transparent;
      border: none;
      color: var(--text);
      font-size: 1.05rem;
      padding: .6rem .9rem;
      outline: none;
    }}
    .search-box button {{
      background: linear-gradient(135deg, #0284c7, #4f46e5);
      color: #fff;
      border: none;
      padding: .65rem 1.4rem;
      border-radius: 10px;
      font-weight: 600;
      font-size: .95rem;
      cursor: pointer;
    }}
    .search-box button:hover {{ opacity: .92; }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: .5rem;
      margin: .9rem 0 1.75rem;
      align-items: center;
    }}
    .chips span {{ font-size: .8rem; color: var(--muted); }}
    .chip {{
      font-size: .8rem;
      color: #cbd5e1;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border);
      padding: .25rem .7rem;
      border-radius: 999px;
      text-decoration: none;
      transition: all .15s;
    }}
    .chip:hover {{ border-color: var(--accent); color: var(--accent); background: var(--accent-glow); }}
    .answer-card {{
      background: var(--answer-bg);
      border: 1px solid rgba(56, 189, 248, 0.4);
      border-radius: 16px;
      padding: 1.35rem 1.5rem;
      margin-bottom: 1.75rem;
      box-shadow: 0 12px 32px -12px rgba(56, 189, 248, 0.2);
    }}
    .answer-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: .5rem;
      margin-bottom: .75rem;
    }}
    .sparkle {{
      font-size: .85rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--accent);
    }}
    .source-pill {{
      font-size: .75rem;
      font-family: monospace;
      background: rgba(56, 189, 248, 0.14);
      color: #7dd3fc;
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: .15rem .55rem;
      border-radius: 999px;
      margin-left: .35rem;
    }}
    .answer-summary {{
      font-size: 1.05rem;
      color: #f1f5f9;
      margin: 0 0 .85rem;
      line-height: 1.65;
    }}
    .answer-bullets {{
      margin: 0;
      padding-left: 1.2rem;
      color: #cbd5e1;
      font-size: .92rem;
    }}
    .answer-bullets li {{ margin-bottom: .4rem; }}
    .cite {{
      font-size: .72rem;
      font-family: monospace;
      color: #94a3b8;
      background: rgba(255,255,255,0.06);
      padding: .1rem .4rem;
      border-radius: 4px;
      margin-left: .3rem;
    }}
    .results-header {{
      font-size: .85rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--muted);
      margin-bottom: .75rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.15rem 1.35rem;
      margin-bottom: .9rem;
      transition: transform .15s, border-color .15s;
    }}
    .card:hover {{ border-color: #475569; }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      margin-bottom: .5rem;
    }}
    .doc-title {{ font-size: 1.05rem; display: flex; align-items: center; gap: .5rem; }}
    .rank {{
      font-size: .78rem;
      font-weight: 700;
      color: var(--accent);
      background: var(--accent-glow);
      padding: .1rem .45rem;
      border-radius: 6px;
    }}
    .score-wrap {{ display: flex; align-items: center; gap: .6rem; }}
    .score-bar {{
      width: 72px;
      height: 6px;
      background: rgba(255,255,255,0.08);
      border-radius: 999px;
      overflow: hidden;
    }}
    .score-fill {{
      height: 100%;
      background: linear-gradient(90deg, #38bdf8, #818cf8);
      border-radius: 999px;
    }}
    .badge {{
      font-family: monospace;
      font-size: .8rem;
      background: rgba(129, 140, 248, 0.15);
      color: #a5b4fc;
      padding: .15rem .55rem;
      border-radius: 6px;
    }}
    .snippet {{ color: #cbd5e1; margin: .5rem 0 .85rem; font-size: .95rem; }}
    .card-footer {{
      display: flex;
      flex-direction: column;
      gap: .5rem;
      border-top: 1px solid rgba(255,255,255,0.06);
      padding-top: .65rem;
      font-size: .85rem;
    }}
    .terms {{ color: var(--muted); display: flex; align-items: center; gap: .35rem; flex-wrap: wrap; }}
    .term-tag {{
      font-family: monospace;
      font-size: .75rem;
      background: rgba(255,255,255,0.06);
      color: #e2e8f0;
      padding: .1rem .45rem;
      border-radius: 4px;
    }}
    mark {{
      background: var(--mark-bg);
      color: var(--mark-text);
      padding: .05rem .25rem;
      border-radius: 4px;
      font-weight: 600;
    }}
    details summary {{
      cursor: pointer;
      color: var(--accent);
      font-weight: 500;
      user-select: none;
    }}
    pre {{
      white-space: pre-wrap;
      font-size: .85rem;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--border);
      padding: .85rem;
      border-radius: 8px;
      color: #e2e8f0;
      margin-top: .5rem;
    }}
    .welcome-card, .empty-state {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.5rem;
      color: #cbd5e1;
    }}
    .welcome-card h3, .empty-state h3 {{ margin-top: 0; color: var(--text); }}
    .corpus-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: .75rem;
      margin-top: 1rem;
    }}
    .corpus-item {{
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border);
      padding: .75rem 1rem;
      border-radius: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .corpus-item span {{ font-size: .8rem; color: var(--muted); }}
  </style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <h1 class="title">Mini Search Engine</h1>
      <p class="subtitle">Inverted Index &middot; TF-IDF Cosine Ranking &middot; Extractive Answer Synthesis ({len(engine.documents)} docs, {len(engine.inverted_index)} terms)</p>
    </header>
    <form class="search-box" method="GET" action="/">
      <input type="search" name="q" value="{escaped_q}" placeholder="Ask a question or search keywords (e.g. What is Python used for?)..." autofocus>
      <button type="submit">Search</button>
    </form>
    <div class="chips">
      <span>Try:</span> {chips_html}
    </div>
    {content_html}
  </div>
</body>
</html>"""


def make_handler(engine: MiniSearchEngine):
    class SearchHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]

            if parsed.path == "/api/search":
                payload = json.dumps(engine.answer(query)).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            body = render_page(engine, query).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

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
