from src.tokenizer import tokenize


def search_documents(query: str, inverted_index: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    """Tokenize query and return (query_tokens, matching_doc_names)."""
    query_tokens = tokenize(query)
    matched_docs: set[str] = set()
    for token in query_tokens:
        if token in inverted_index:
            matched_docs.update(inverted_index[token])
    return query_tokens, sorted(matched_docs)
