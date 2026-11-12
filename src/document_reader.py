import os


def read_documents(directory: str = "documents") -> dict[str, str]:
    """Read all .txt files from the given directory and return {filename: content}."""
    docs = {}
    if not os.path.isdir(directory):
        return docs
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    docs[filename] = f.read()
    return docs
