import re
import string


def preprocess_text(text: str) -> str:
    """Convert text to lowercase, remove punctuation, and normalize whitespace."""
    cleaned = text.lower().translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    return re.sub(r"\s+", " ", cleaned).strip()
