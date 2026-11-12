import datetime
import math
import os
import re
import sys
import time
from collections import Counter
from src.document_reader import read_documents
from src.tokenizer import tokenize
from src.inverted_index import build_inverted_index
from src.search import search_documents
from src.ranking import bm25_score, compute_idf, compute_tf, term_breakdown


def get_snippet(text: str, query_tokens: list[str], max_len: int = 140) -> str:
    """Return the best matching sentence/line for the query tokens."""
    best_line, best_hits = "", -1
    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        line_tokens = set(tokenize(line_clean))
        hits = sum(1 for tok in set(query_tokens) if tok in line_tokens)
        if hits > best_hits:
            best_hits, best_line = hits, line_clean
    return best_line[:max_len] + ("..." if len(best_line) > max_len else "")


def synthesize_answer(
    query_tokens: list[str],
    ranked_results: list[dict],
    documents: dict[str, str],
    idf: dict[str, float],
) -> dict:
    """Extract and rank the most informative sentences across top documents to answer the query."""
    if not query_tokens or not ranked_results:
        return {"summary": "", "bullets": [], "sources": [], "confidence": 0}

    q_set = set(query_tokens)
    scored_sentences: list[tuple[float, str, str]] = []

    for rank_idx, res in enumerate(ranked_results):
        doc_name = res["document"]
        doc_score = res["score"]
        raw_text = documents.get(doc_name, "")
        for sent in re.split(r"(?<=[.!?])\s+|\n+", raw_text):
            sent = sent.strip()
            if not sent:
                continue
            s_tokens = set(tokenize(sent))
            matched = q_set & s_tokens
            if matched:
                idf_sum = sum(idf.get(t, 1.0) for t in matched)
                score = idf_sum * (doc_score * 4.0) - (rank_idx * 0.1)
                scored_sentences.append((score, sent, doc_name))

    scored_sentences.sort(key=lambda x: -x[0])
    top = scored_sentences[:3]
    if not top:
        return {"summary": "", "bullets": [], "sources": [], "confidence": 0}

    top_doc = ranked_results[0]["document"]
    lead_sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", documents[top_doc]) if s.strip()]
    selected_texts = [s for _, s, _ in top]
    if lead_sents and lead_sents[0] not in selected_texts:
        summary = f"{lead_sents[0]} {top[0][1]}"
    else:
        summary = " ".join(s for _, s, _ in top[:2])

    matched_union = set()
    for r in ranked_results:
        matched_union.update(r.get("matched_terms", []))
    coverage = len(matched_union) / max(1, len(q_set))
    confidence = min(99, max(45, int(coverage * 75 + min(24, ranked_results[0]["score"] * 40))))

    bullets = [{"text": sent, "source": doc} for _, sent, doc in top]
    sources = list(dict.fromkeys(doc for _, _, doc in top))
    return {"summary": summary, "bullets": bullets, "sources": sources, "confidence": confidence}


class MiniSearchEngine:
    def __init__(self, doc_dir: str = "documents"):
        self.doc_dir = doc_dir
        self.reload()

    def reload(self) -> None:
        self.documents = read_documents(self.doc_dir)
        self.tokenized_docs = {name: tokenize(text) for name, text in self.documents.items()}
        self.doc_token_sets = {name: set(toks) for name, toks in self.tokenized_docs.items()}
        self.inverted_index = build_inverted_index(self.tokenized_docs)
        self.idf = compute_idf(self.tokenized_docs, self.inverted_index)
        self.avg_dl = sum(len(t) for t in self.tokenized_docs.values()) / max(1, len(self.tokenized_docs))

        # Precompute TF-IDF vectors and norms once on load for O(1) query scoring
        self.doc_vecs: dict[str, dict[str, float]] = {}
        self.doc_norms: dict[str, float] = {}
        for name, toks in self.tokenized_docs.items():
            tf_map = compute_tf(toks)
            vec = {term: tf * self.idf[term] for term, tf in tf_map.items() if term in self.idf}
            self.doc_vecs[name] = vec
            self.doc_norms[name] = math.sqrt(sum(v * v for v in vec.values()))

        self._cached_stats = self._build_stats()

    def add_document(self, filename: str, content: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", os.path.basename(filename.strip() or "document.txt"))
        if not safe_name.lower().endswith((".txt", ".md", ".csv", ".json")):
            safe_name += ".txt"
        os.makedirs(self.doc_dir, exist_ok=True)
        path = os.path.join(self.doc_dir, safe_name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        self.reload()
        return safe_name

    def delete_document(self, filename: str) -> bool:
        safe_name = os.path.basename(filename.strip())
        path = os.path.join(self.doc_dir, safe_name)
        if os.path.isfile(path):
            os.remove(path)
            self.reload()
            return True
        return False

    def suggest(self, prefix: str, limit: int = 6) -> list[dict]:
        p = prefix.strip().lower()
        if not p:
            return []
        tokens = p.split()
        last = tokens[-1]
        head = " ".join(tokens[:-1])
        matches = [
            (term, len(docs))
            for term, docs in self.inverted_index.items()
            if term.startswith(last) and term != last
        ]
        matches.sort(key=lambda x: (-x[1], x[0]))
        return [{"term": f"{head} {t}".strip(), "df": df} for t, df in matches[:limit]]

    def _build_stats(self) -> dict:
        docs_meta = []
        for name in self.documents:
            filepath = os.path.join(self.doc_dir, name)
            mtime = os.path.getmtime(filepath) if os.path.exists(filepath) else time.time()
            ext = os.path.splitext(name)[1].lstrip(".").upper() or "TXT"
            toks = self.tokenized_docs[name]
            counts = Counter(tokenize(self.documents[name], remove_stopwords=True))
            top_terms = [t for t, _ in counts.most_common(5)]
            lines = [ln.strip() for ln in self.documents[name].splitlines() if ln.strip()]
            docs_meta.append({
                "name": name,
                "ext": ext,
                "uploaded_at": datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y"),
                "mtime": mtime,
                "status": "Indexed",
                "tokens": len(toks),
                "unique_terms": len(set(toks)),
                "top_terms": top_terms,
                "preview": (lines[0] if lines else self.documents[name])[:110].strip(),
                "content": self.documents[name],
                "sections": lines,
            })
        docs_meta.sort(key=lambda d: (-d["mtime"], d["name"]))
        return {
            "total_docs": len(self.documents),
            "total_tokens": sum(len(t) for t in self.tokenized_docs.values()),
            "unique_terms": len(self.inverted_index),
            "documents": docs_meta,
        }

    def index_stats(self) -> dict:
        return self._cached_stats

    def query(self, query_str: str, mode: str = "tfidf", fuzzy: bool = True) -> list[dict]:
        return self.answer(query_str, mode=mode, fuzzy=fuzzy)["results"]

    def answer(self, query_str: str, mode: str = "tfidf", fuzzy: bool = True) -> dict:
        t0 = time.perf_counter()
        query_tokens, matching_docs, corrections = search_documents(
            query_str, self.inverted_index, self.documents, fuzzy=fuzzy
        )

        scores: list[tuple[str, float]] = []
        if query_tokens and matching_docs:
            if mode == "bm25":
                for doc_name in matching_docs:
                    sc = bm25_score(query_tokens, self.tokenized_docs[doc_name], self.idf, self.avg_dl)
                    if sc > 0:
                        scores.append((doc_name, sc))
            else:
                q_tf = compute_tf(query_tokens)
                q_vec = {t: tf * self.idf[t] for t, tf in q_tf.items() if t in self.idf}
                q_norm = math.sqrt(sum(v * v for v in q_vec.values()))
                if q_norm > 0:
                    for doc_name in matching_docs:
                        d_vec = self.doc_vecs[doc_name]
                        d_norm = self.doc_norms[doc_name]
                        if d_norm > 0:
                            dot = sum(val * d_vec.get(t, 0.0) for t, val in q_vec.items())
                            sc = dot / (q_norm * d_norm)
                            if sc > 0:
                                scores.append((doc_name, sc))

        ranked = sorted(scores, key=lambda item: (-item[1], item[0]))
        q_set = set(query_tokens)
        results = [
            {
                "document": doc_name,
                "ext": os.path.splitext(doc_name)[1].lstrip(".").upper() or "TXT",
                "score": round(score, 4),
                "snippet": get_snippet(self.documents[doc_name], query_tokens),
                "matched_terms": sorted(q_set & self.doc_token_sets[doc_name]),
                "breakdown": term_breakdown(query_tokens, self.tokenized_docs[doc_name], self.idf),
                "token_count": len(self.tokenized_docs[doc_name]),
            }
            for doc_name, score in ranked
        ]
        synthesis = synthesize_answer(query_tokens, results, self.documents, self.idf)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "query": query_str,
            "resolved_tokens": query_tokens,
            "corrections": corrections,
            "mode": mode,
            "elapsed_ms": elapsed_ms,
            "answer": synthesis,
            "results": results,
        }


def display_results(payload: dict) -> None:
    results = payload["results"]
    ans = payload["answer"]
    if payload.get("corrections"):
        fixes = ", ".join(f"'{k}' -> '{v}'" for k, v in payload["corrections"].items())
        print(f"\n[Auto-corrected typo] {fixes}")
    if not results:
        print("No matching documents found.\n")
        return
    if ans["summary"]:
        print(f"\n[Smart Answer ({ans['confidence']}% confidence)] {ans['summary']}")
        print(f"  Sources: {', '.join(ans['sources'])}")
    print(f"\nFound {len(results)} relevant document(s) in {payload['elapsed_ms']} ms ({payload['mode'].upper()}):")
    for idx, res in enumerate(results, 1):
        print(f"  {idx}. {res['document']} (Score: {res['score']:.4f})")
        print(f"     Snippet: {res['snippet']}")
    print()


def _self_check() -> None:
    from src.web import render_page

    engine = MiniSearchEngine("documents")
    assert len(engine.documents) >= 5, f"Expected >= 5 sample documents, got {len(engine.documents)}"
    res = engine.query("python data science")
    assert res and res[0]["document"] == "python.txt", f"Expected python.txt first, got {res}"
    res_bm25 = engine.query("python data science", mode="bm25")
    assert res_bm25 and res_bm25[0]["document"] == "python.txt", "BM25 ranking failed"
    ans_typo = engine.answer("pythn machne learning")
    assert ans_typo["corrections"].get("pythn") == "python", f"Fuzzy correction failed: {ans_typo['corrections']}"
    res_excl = engine.query("programming -python -java")
    assert all(r["document"] not in {"python.txt", "java.txt"} for r in res_excl), "Exclusion operator failed"
    assert engine.query("nonexistentxyztoken", fuzzy=False) == []
    html_out = render_page(engine, "python")
    assert "python.txt" in html_out and "bento-grid" in html_out
    print("Self-check passed.")


def main() -> None:
    if "--check" in sys.argv:
        _self_check()
        return

    doc_dir = os.environ.get("DOCUMENTS_DIR", "documents")
    if "--web" in sys.argv:
        from src.web import run_server

        idx = sys.argv.index("--web")
        default_port = int(os.environ.get("PORT", "8000"))
        port = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit() else default_port
        run_server(port=port, doc_dir=doc_dir)
        return

    engine = MiniSearchEngine(doc_dir)
    print(f"Mini Search Engine initialized with {len(engine.documents)} documents.")

    if len(sys.argv) > 1:
        query_str = " ".join(sys.argv[1:])
        display_results(engine.answer(query_str))
        return

    while True:
        try:
            query_str = input("Search (or 'exit' to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if query_str.lower() in {"exit", "quit", "q"}:
            break
        if query_str:
            display_results(engine.answer(query_str))


if __name__ == "__main__":
    main()
