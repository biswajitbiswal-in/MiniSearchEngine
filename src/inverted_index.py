from collections import defaultdict


def build_inverted_index(tokenized_docs: dict[str, list[str]]) -> dict[str, list[str]]:
    """Map each unique token to a sorted list of document names containing it."""
    index: dict[str, set[str]] = defaultdict(set)
    for doc_name, tokens in tokenized_docs.items():
        for token in set(tokens):
            index[token].add(doc_name)
    return {term: sorted(docs) for term, docs in index.items()}
