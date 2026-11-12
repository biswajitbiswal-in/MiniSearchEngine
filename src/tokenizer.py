from src.text_processor import preprocess_text

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "or", "that", "the", "to", "was", "were",
    "will", "with", "what", "how", "why", "where", "when", "which", "who",
}


def tokenize(text: str, remove_stopwords: bool = False) -> list[str]:
    """Split preprocessed text into word tokens, optionally removing stopwords."""
    cleaned = preprocess_text(text)
    tokens = cleaned.split() if cleaned else []
    if remove_stopwords:
        filtered = [t for t in tokens if t not in STOPWORDS]
        return filtered or tokens
    return tokens
