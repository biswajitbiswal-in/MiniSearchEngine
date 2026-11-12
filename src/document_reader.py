import os
import xml.etree.ElementTree as ET
import zipfile

SUPPORTED_EXTENSIONS = (".txt", ".md", ".csv", ".json", ".docx")


def _read_docx(filepath: str) -> str:
    """Extract plain text from a .docx file using stdlib zipfile + XML parser."""
    with zipfile.ZipFile(filepath) as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    return " ".join(node.text for node in root.iter() if node.tag.endswith("}t") and node.text)


def read_documents(directory: str = "documents") -> dict[str, str]:
    """Read supported documents (.txt, .md, .csv, .json, .docx) from directory."""
    docs: dict[str, str] = {}
    if not os.path.isdir(directory):
        return docs
    for filename in sorted(os.listdir(directory)):
        if filename.lower().endswith(SUPPORTED_EXTENSIONS):
            filepath = os.path.join(directory, filename)
            if not os.path.isfile(filepath):
                continue
            if filename.lower().endswith(".docx"):
                docs[filename] = _read_docx(filepath)
            else:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    docs[filename] = f.read()
    return docs
