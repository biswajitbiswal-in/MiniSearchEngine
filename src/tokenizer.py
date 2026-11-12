from src.text_processor import preprocess_text


def tokenize(text: str) -> list[str]:
    """Split preprocessed text into individual word tokens."""
    cleaned = preprocess_text(text)
    return cleaned.split() if cleaned else []
