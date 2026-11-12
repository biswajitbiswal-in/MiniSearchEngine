import difflib
import re
from src.tokenizer import tokenize


def parse_advanced_query(query: str) -> tuple[list[str], list[str], list[str]]:
    """Extract quoted phrases, excluded terms (-term), and regular tokens."""
    phrases = [p.strip().lower() for p in re.findall(r'"([^"]+)"', query) if p.strip()]
    rest = re.sub(r'"[^"]+"', " ", query)
    excluded = [m.lower() for m in re.findall(r"(?:^|\s)-(\w+)", rest)]
    rest = re.sub(r"(?:^|\s)-\w+", " ", rest)
    tokens = tokenize(rest, remove_stopwords=True)
    for phrase in phrases:
        tokens.extend(tokenize(phrase, remove_stopwords=False))
    return list(dict.fromkeys(tokens)), phrases, excluded


def search_documents(
    query: str,
    inverted_index: dict[str, list[str]],
    raw_documents: dict[str, str] | None = None,
    fuzzy: bool = True,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Search index with phrase, exclusion, and fuzzy typo correction support."""
    query_tokens, phrases, excluded = parse_advanced_query(query)
    vocab = list(inverted_index.keys())
    corrections: dict[str, str] = {}
    resolved_tokens: list[str] = []

    for token in query_tokens:
        if token in inverted_index:
            resolved_tokens.append(token)
        elif fuzzy and vocab:
            matches = difflib.get_close_matches(token, vocab, n=1, cutoff=0.72)
            if matches:
                corrections[token] = matches[0]
                resolved_tokens.append(matches[0])
            else:
                resolved_tokens.append(token)
        else:
            resolved_tokens.append(token)

    matched_docs: set[str] = set()
    for token in resolved_tokens:
        if token in inverted_index:
            matched_docs.update(inverted_index[token])

    for ex in excluded:
        if ex in inverted_index:
            matched_docs.difference_update(inverted_index[ex])

    if phrases and raw_documents:
         matched_docs = {
             doc for doc in matched_docs
             if all(phrase in raw_documents.get(doc, "").lower() for phrase in phrases)
         }

    return resolved_tokens, sorted(matched_docs), corrections
