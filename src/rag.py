"""
rag.py
The full RAG pipeline: question -> find relevant chunks -> LLM writes an answer with citations.

Usage:
  python src/rag.py "your question"
  python src/rag.py "your question" 2022      <- only use one year's reports
"""

import sys

import chromadb
import ollama
import torch
from sentence_transformers import SentenceTransformer

DB_DIR = "data/vectordb"
COLLECTION_NAME = "cbsl_chunks"
EMBED_MODEL = "BAAI/bge-base-en-v1.5"
LLM_MODEL = "qwen2.5:7b"
TOP_K = 5
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

DOC_NAMES = {
    "annual_report": "Annual Report",
    "economic_review": "Annual Economic Review",
}

# The instructions the LLM must follow. This is called the "system prompt".
SYSTEM_PROMPT = """You answer questions about the Sri Lankan economy using ONLY the numbered
excerpts from Central Bank of Sri Lanka (CBSL) reports given to you.

Rules:
- Use only information from the excerpts. Do not use outside knowledge.
- After every fact, cite the excerpt it came from in square brackets, e.g. [1] or [2][3].
- If the excerpts do not contain the answer, reply exactly:
  "I could not find this in the CBSL reports." Do not guess.
- Be clear and concise: at most 200 words."""


# ---------- Load models once ----------

print("Loading models...")
device = "cuda" if torch.cuda.is_available() else "cpu"
embedder = SentenceTransformer(EMBED_MODEL, device=device)
collection = chromadb.PersistentClient(path=DB_DIR).get_collection(COLLECTION_NAME)


# ---------- The three steps of RAG ----------

def retrieve(question, year=None, top_k=TOP_K):
    """R = Retrieval: find the chunks closest in meaning to the question."""
    vector = embedder.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    results = collection.query(
        query_embeddings=[vector.tolist()],
        n_results=top_k,
        where={"year": year} if year else None,
    )
    chunks = []
    for i in range(len(results["ids"][0])):
        chunk = dict(results["metadatas"][0][i])   # year, title, pages...
        chunk["chunk_id"] = results["ids"][0][i]
        chunk["text"] = results["documents"][0][i]
        chunk["similarity"] = 1 - results["distances"][0][i]
        chunks.append(chunk)
    return chunks


def source_label(chunk):
    """e.g. 'Annual Report 2022, Prices and Wages, pp. 8-9'"""
    return (f"{DOC_NAMES[chunk['doc_type']]} {chunk['year']}, {chunk['title']}, "
            f"pp. {chunk['page_start']}-{chunk['page_end']}")


def build_prompt(question, chunks):
    """A = Augmentation: put the retrieved chunks into the prompt, numbered [1], [2]..."""
    excerpts = "\n\n".join(
        f"[{n}] ({source_label(c)})\n{c['text']}" for n, c in enumerate(chunks, start=1)
    )
    return f"EXCERPTS:\n\n{excerpts}\n\nQUESTION: {question}"


def answer(question, year=None):
    """G = Generation: the LLM writes an answer using only the excerpts."""
    chunks = retrieve(question, year)
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(question, chunks)},
        ],
        options={
            "temperature": 0.1,  # low = more factual, less creative
            "num_ctx": 8192,     # how much text the LLM can read at once
        },
    )
    return response["message"]["content"], chunks


# ---------- Run from the command line ----------

if __name__ == "__main__":
    question = sys.argv[1]
    year = int(sys.argv[2]) if len(sys.argv) > 2 else None

    reply, sources = answer(question, year)

    print("\n" + "=" * 80)
    print(f"QUESTION: {question}" + (f"   (year = {year})" if year else ""))
    print("=" * 80)
    print(reply)
    print("\nSOURCES:")
    for n, c in enumerate(sources, start=1):
        print(f"  [{n}] {source_label(c)}   (similarity {c['similarity']:.2f})")