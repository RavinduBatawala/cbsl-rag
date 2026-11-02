"""
build_index.py
Turn every chunk into an embedding (a list of numbers that captures its meaning)
and store them in a ChromaDB vector database.

Input:  data/processed/chunks.jsonl
Output: data/vectordb/   (the database)

Run from the project root:  python src/build_index.py
"""

import json
from pathlib import Path

import chromadb
import torch
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = Path("data/processed/chunks.jsonl")
DB_DIR = "data/vectordb"
COLLECTION_NAME = "cbsl_chunks"
MODEL_NAME = "BAAI/bge-base-en-v1.5"

DOC_NAMES = {
    "annual_report": "Annual Report",
    "economic_review": "Annual Economic Review",
}


def clean_title(title):
    """Remove line breaks and double spaces from a title."""
    return " ".join(title.split())


def text_to_embed(chunk):
    """Add a short header so the model knows WHERE the text comes from.
    e.g. 'Annual Report 2022 - Prices and Wages' + the chunk text.
    This small trick usually improves search."""
    header = f"{DOC_NAMES[chunk['doc_type']]} {chunk['year']} - {clean_title(chunk['title'])}"
    return header + "\n" + chunk["text"]


def main():
    # 1. Load chunks
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]
    print(f"Loaded {len(chunks)} chunks")

    # 2. Load the embedding model (downloads ~440 MB the first time)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    model = SentenceTransformer(MODEL_NAME, device=device)

    # 3. Turn every chunk into a vector
    texts = [text_to_embed(c) for c in chunks]
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,  # makes all vectors length 1, good for cosine similarity
    )
    print(f"Each chunk is now {embeddings.shape[1]} numbers")

    # 4. Create a fresh database collection (delete the old one if it exists)
    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
        print("Deleted old collection")
    except Exception:
        pass  # it didn't exist yet - that's fine
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # measure closeness with cosine similarity
    )

    # 5. Add everything in batches of 1000
    batch = 1000
    for start in range(0, len(chunks), batch):
        part = chunks[start:start + batch]
        collection.add(
            ids=[c["chunk_id"] for c in part],
            embeddings=embeddings[start:start + batch].tolist(),
            documents=[c["text"] for c in part],
            metadatas=[{
                "doc_type": c["doc_type"],
                "year": c["year"],
                "section_type": c["section_type"],
                "title": clean_title(c["title"]),
                "filename": c["filename"],
                "page_start": c["page_start"],
                "page_end": c["page_end"],
            } for c in part],
        )
        print(f"   added {start + len(part)} / {len(chunks)}")

    print(f"\nDone! {collection.count()} chunks stored in {DB_DIR}")


if __name__ == "__main__":
    main()