import os
import re
import sys
from src.document_reader import read_documents
from src.tokenizer import tokenize
from src.inverted_index import build_inverted_index
from src.search import search_documents
from src.ranking import compute_idf, rank_documents


def get_snippet(text: str, query_tokens: list[str], max_len: int = 160) -> str:
    """Return the best matching line/sentence for the query tokens."""
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
        return {"summary": "", "bullets": [], "sources": []}

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
        return {"summary": "", "bullets": [], "sources": []}

    # Include lead definition sentence of top document if not already selected
    top_doc = ranked_results[0]["document"]
    lead_sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", documents[top_doc]) if s.strip()]
    selected_texts = [s for _, s, _ in top]
    if lead_sents and lead_sents[0] not in selected_texts:
        summary = f"{lead_sents[0]} {top[0][1]}"
    else:
        summary = " ".join(s for _, s, _ in top[:2])

    bullets = [{"text": sent, "source": doc} for _, sent, doc in top]
    sources = list(dict.fromkeys(doc for _, _, doc in top))
    return {"summary": summary, "bullets": bullets, "sources": sources}


class MiniSearchEngine:
    def __init__(self, doc_dir: str = "documents"):
        self.documents = read_documents(doc_dir)
        self.tokenized_docs = {name: tokenize(text) for name, text in self.documents.items()}
        self.inverted_index = build_inverted_index(self.tokenized_docs)
        self.idf = compute_idf(self.tokenized_docs, self.inverted_index)

    def query(self, query_str: str) -> list[dict]:
        query_tokens, matching_docs = search_documents(query_str, self.inverted_index)
        ranked = rank_documents(query_tokens, matching_docs, self.tokenized_docs, self.inverted_index)
        q_set = set(query_tokens)
        return [
            {
                "document": doc_name,
                "score": round(score, 4),
                "snippet": get_snippet(self.documents[doc_name], query_tokens),
                "matched_terms": sorted(q_set & set(self.tokenized_docs[doc_name])),
            }
            for doc_name, score in ranked
        ]

    def answer(self, query_str: str) -> dict:
        query_tokens, _ = search_documents(query_str, self.inverted_index)
        results = self.query(query_str)
        synthesis = synthesize_answer(query_tokens, results, self.documents, self.idf)
        return {"query": query_str, "answer": synthesis, "results": results}


def display_results(payload: dict) -> None:
    results = payload["results"]
    ans = payload["answer"]
    if not results:
        print("No matching documents found.\n")
        return
    if ans["summary"]:
        print(f"\n[Smart Answer] {ans['summary']}")
        print(f"  Sources: {', '.join(ans['sources'])}")
    print(f"\nFound {len(results)} relevant document(s):")
    for idx, res in enumerate(results, 1):
        print(f"  {idx}. {res['document']} (Score: {res['score']:.4f})")
        print(f"     Snippet: {res['snippet']}")
    print()


def _self_check() -> None:
    from src.web import render_page

    engine = MiniSearchEngine("documents")
    assert len(engine.documents) == 3, "Expected 3 sample documents"
    res = engine.query("python data science")
    assert res and res[0]["document"] == "python.txt", f"Expected python.txt first, got {res}"
    ans = engine.answer("python data science")
    assert "Python" in ans["answer"]["summary"], "Expected synthesized answer to mention Python"
    res_js = engine.query("nodejs web html")
    assert res_js and res_js[0]["document"] == "javascript.txt", f"Expected javascript.txt first, got {res_js}"
    assert engine.query("nonexistentxyztoken") == []
    html_out = render_page(engine, "python")
    assert "python.txt" in html_out and "<mark>Python</mark>" in html_out
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
