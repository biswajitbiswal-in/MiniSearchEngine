import math
from collections import Counter


def compute_tf(tokens: list[str]) -> dict[str, float]:
    """Calculate term frequency (TF) for a token list."""
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def compute_idf(tokenized_docs: dict[str, list[str]], inverted_index: dict[str, list[str]]) -> dict[str, float]:
    """Calculate smoothed Inverse Document Frequency (IDF) for all indexed terms."""
    total_docs = len(tokenized_docs)
    return {
        term: math.log((1 + total_docs) / (1 + len(doc_list))) + 1.0
        for term, doc_list in inverted_index.items()
    }


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse TF-IDF vectors."""
    dot_product = sum(val * vec_b.get(term, 0.0) for term, val in vec_a.items())
    norm_a = math.sqrt(sum(val * val for val in vec_a.values()))
    norm_b = math.sqrt(sum(val * val for val in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    idf: dict[str, float],
    avg_dl: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Calculate Okapi BM25 relevance score for a single document."""
    if not doc_tokens or avg_dl == 0:
        return 0.0
    counts = Counter(doc_tokens)
    dl = len(doc_tokens)
    score = 0.0
    for term in set(query_tokens):
        if term not in counts:
            continue
        tf = counts[term]
        term_idf = idf.get(term, 0.0)
        denom = tf + k1 * (1.0 - b + b * (dl / avg_dl))
        score += term_idf * ((tf * (k1 + 1.0)) / denom)
    return score


def term_breakdown(
    query_tokens: list[str],
    doc_tokens: list[str],
    idf: dict[str, float],
) -> list[dict]:
    """Return per-query-term TF, IDF, and TF-IDF product for explainable ranking."""
    tf_map = compute_tf(doc_tokens)
    counts = Counter(doc_tokens)
    details = []
    for term in dict.fromkeys(query_tokens):
        if term in counts:
            tf_val = tf_map[term]
            idf_val = idf.get(term, 0.0)
            details.append({
                "term": term,
                "count": counts[term],
                "tf": round(tf_val, 4),
                "idf": round(idf_val, 4),
                "tfidf": round(tf_val * idf_val, 4),
            })
    return details


def rank_documents(
    query_tokens: list[str],
    matching_docs: list[str],
    tokenized_docs: dict[str, list[str]],
    inverted_index: dict[str, list[str]],
    mode: str = "tfidf",
) -> list[tuple[str, float]]:
    """Rank matching documents by TF-IDF cosine similarity or Okapi BM25."""
    if not query_tokens or not matching_docs:
        return []

    idf = compute_idf(tokenized_docs, inverted_index)
    scores: list[tuple[str, float]] = []

    if mode == "bm25":
        avg_dl = sum(len(t) for t in tokenized_docs.values()) / max(1, len(tokenized_docs))
        for doc_name in matching_docs:
            score = bm25_score(query_tokens, tokenized_docs[doc_name], idf, avg_dl)
            if score > 0:
                scores.append((doc_name, score))
    else:
        query_tf = compute_tf(query_tokens)
        query_vec = {term: tf * idf.get(term, 0.0) for term, tf in query_tf.items() if term in idf}
        for doc_name in matching_docs:
            doc_tf = compute_tf(tokenized_docs[doc_name])
            doc_vec = {term: tf * idf[term] for term, tf in doc_tf.items() if term in idf}
            score = cosine_similarity(query_vec, doc_vec)
            if score > 0:
                scores.append((doc_name, score))

    return sorted(scores, key=lambda item: (-item[1], item[0]))
