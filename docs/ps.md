# PS-01: Mini Search Engine Using Python

## 1. Problem Statement

Develop a Mini Search Engine using Python that can search through a collection of text documents and retrieve the most relevant documents based on user queries.

The system should efficiently process text documents, create an inverted index, perform keyword-based searches, and rank the search results using the TF-IDF (Term Frequency–Inverse Document Frequency) algorithm.

## 2. Objectives

- Read and process multiple text documents.
- Extract and tokenize text into individual words.
- Create an inverted index to map keywords to their corresponding documents.
- Allow users to search documents using keywords.
- Rank search results based on relevance using TF-IDF.
- Display the most relevant documents first.

## 3. Functional Requirements

1. **Document Reader:** Read and extract text from multiple text documents.
2. **Text Processing:** Convert text into lowercase, remove punctuation, and tokenize words.
3. **Inverted Index Creation:** Build an index that maps each word to the documents containing it.
4. **Keyword Search:** Accept user queries and retrieve matching documents.
5. **TF-IDF Ranking:** Calculate relevance scores for matching documents.
6. **Search Results:** Display ranked documents with their relevance scores.

## 4. Technology Stack

- Programming Language: Python
- Libraries: re, os, math, collections
- Ranking Algorithm: TF-IDF
- Data Structure: Dictionary (Inverted Index)
- Document Format: TXT

## 5. Expected Outcome

A functional mini search engine that allows users to search through a collection of text documents and retrieves relevant results efficiently.

The system should demonstrate the working of information retrieval concepts, inverted indexing, keyword searching, and TF-IDF-based document ranking.

## 6. Future Enhancements

- Support for PDF and DOCX documents.
- Web-based user interface.
- Natural language question answering.
- AI-powered answer generation using Large Language Models (LLMs).
- Display relevant text snippets from documents.

## 7. Conclusion

The Mini Search Engine demonstrates the fundamental principles of information retrieval using Python. It provides an efficient way to search and retrieve relevant information from a collection of documents using inverted indexing and TF-IDF ranking.
