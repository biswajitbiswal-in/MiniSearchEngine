# Mini Search Engine – System Architecture

## 1. Project Overview

The Mini Search Engine is a Python-based document retrieval system that searches through a collection of text documents and returns the most relevant results based on user queries.

The system uses document reading, text preprocessing, tokenization, inverted indexing, TF-IDF scoring, and result ranking to retrieve relevant information efficiently.

## 2. System Architecture

The application follows a modular architecture in which each component performs a specific task.

```text
                 USER
                   |
                   v
             SEARCH QUERY
                   |
                   v
          +------------------+
          |  Search Engine   |
          +------------------+
                   |
                   v
          +------------------+
          | Text Processing  |
          +------------------+
                   |
                   v
          +------------------+
          | Inverted Index   |
          +------------------+
                   |
                   v
          +------------------+
          | TF-IDF Ranking   |
          +------------------+
                   |
                   v
          +------------------+
          | Result Display   |
          +------------------+
                   |
                   v
             SEARCH RESULTS


       DOCUMENT PROCESSING PIPELINE

          +------------------+
          |  Text Documents  |
          +------------------+
                   |
                   v
          +------------------+
          | Document Reader  |
          +------------------+
                   |
                   v
          +------------------+
          | Text Processing  |
          +------------------+
                   |
                   v
          +------------------+
          |   Tokenization   |
          +------------------+
                   |
                   v
          +------------------+
          |  Inverted Index  |
          +------------------+
```

## 3. Main Components

### 3.1 Document Reader

**Purpose:** Reads text from multiple `.txt` documents.

**Technologies:**
- Python `os` module
- Python `open()` function

**Responsibilities:**
- Access the document directory.
- Identify available text files.
- Read document contents.
- Pass extracted text to the preprocessing module.

### 3.2 Text Preprocessing

**Purpose:** Cleans the extracted text before indexing.

**Technologies:**
- `re`
- `string`

**Responsibilities:**
- Convert text into lowercase.
- Remove punctuation and unnecessary symbols.
- Normalize text.
- Prepare text for tokenization.

### 3.3 Tokenization

**Purpose:** Breaks the processed text into individual words or tokens.

**Responsibilities:**
- Split text into tokens.
- Prepare tokens for indexing.
- Maintain consistent word representation.

### 3.4 Inverted Index

**Purpose:** Creates a mapping between words and the documents containing them.

**Data Structure:** Python Dictionary.

**Example:**

```python
{
    "python": ["doc1", "doc3"],
    "java": ["doc2", "doc3"],
    "programming": ["doc1", "doc2"]
}
```

**Responsibilities:**
- Store unique terms.
- Maintain document references.
- Support efficient keyword lookup.

### 3.5 Search Module

**Purpose:** Processes user queries and retrieves matching documents.

**Responsibilities:**
- Accept search keywords.
- Process the search query.
- Look up keywords in the inverted index.
- Retrieve matching documents.

### 3.6 TF-IDF Ranking Module

**Purpose:** Calculates the relevance of documents against a search query.

**Algorithm:** Term Frequency–Inverse Document Frequency (TF-IDF).

**Responsibilities:**
- Calculate term frequency.
- Calculate inverse document frequency.
- Generate TF-IDF vectors.
- Calculate document-query similarity using cosine similarity.
- Assign relevance scores.

### 3.7 Result Display Module

**Purpose:** Displays search results in ranked order.

**Responsibilities:**
- Sort documents by relevance score.
- Display document names.
- Display relevance scores.
- Show relevant text snippets where available.

## 4. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| File Handling | os, open() |
| Text Processing | re, string |
| Data Structures | Lists, Dictionaries |
| Indexing | Inverted Index |
| Ranking Algorithm | TF-IDF |
| Similarity Calculation | Cosine Similarity |
| Storage | Local Text Files |

## 5. Data Flow

1. The system loads text documents from the document directory.
2. The document reader extracts the text.
3. The preprocessing module cleans the extracted text.
4. Tokenization converts the text into individual words.
5. The inverted index maps each word to its corresponding documents.
6. The user enters a search query.
7. The search module identifies matching documents.
8. TF-IDF calculates document-query relevance scores.
9. Cosine similarity helps compare the query with document vectors.
10. The ranking module sorts the results.
11. The system displays the most relevant documents first.

## 6. Project Directory Structure

```text
Mini-Search-Engine/
│
├── documents/
│   ├── python.txt
│   ├── java.txt
│   └── javascript.txt
│
├── src/
│   ├── document_reader.py
│   ├── text_processor.py
│   ├── tokenizer.py
│   ├── inverted_index.py
│   ├── search.py
│   └── ranking.py
│
├── main.py
├── requirements.txt
├── PS.md
├── ARCHITECTURE.md
└── README.md
```

## 7. Future Architecture Enhancements

The system can be extended with the following features:

- PDF and DOCX document support.
- Web-based search interface.
- Natural language question answering.
- LLM integration for AI-generated answers.
- Retrieval-Augmented Generation (RAG).
- Source-based answer generation.

## 8. Conclusion

The proposed architecture provides a modular and scalable structure for developing a Mini Search Engine using Python.

Each module performs an independent task, making the application easier to develop, test, maintain, and extend. The combination of inverted indexing and TF-IDF-based ranking enables efficient document retrieval and relevance-based search results.
