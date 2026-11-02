"""
search.py
Search the vector database with a question.

Usage:
  python src/search.py "your question"
  python src/search.py "your question" 2022      <- only search one year
"""

import sys

import chromadb
import torch
from sentence_transformers import SentenceTransformer

DB_DIR = "data/vectordb"
COLLECTION_NAME = "cbsl_chunks"
MODEL_NAME = "BAAI/bge-base-en-v1.5"
TOP_K = 5  # how many results to show

# The bge model works best when questions start with this instruction
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

question = sys.argv[1]
year = int(sys.argv[2]) if len(sys.argv) > 2 else None

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer(MODEL_NAME, device=device)
collection = chromadb.PersistentClient(path=DB_DIR).get_collection(COLLECTION_NAME)

query_vector = model.encode(QUERY_PREFIX + question, normalize_embeddings=True)

results = collection.query(
    query_embeddings=[query_vector.tolist()],
    n_results=TOP_K,
    where={"year": year} if year else None,  # optional filter by year
)

print(f"\nQUESTION: {question}" + (f"   (year = {year})" if year else ""))
for rank in range(len(results["ids"][0])):
    meta = results["metadatas"][0][rank]
    similarity = 1 - results["distances"][0][rank]  # 1.0 = identical meaning
    text = results["documents"][0][rank]
    print("\n" + "-" * 80)
    print(f"#{rank + 1}  similarity {similarity:.3f}  |  {meta['year']}  |  {meta['title']}  "
          f"|  pages {meta['page_start']}-{meta['page_end']}")
    print(text[:400] + "...")