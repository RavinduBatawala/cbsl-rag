"""
extract.py
Extract the text of every page of every PDF in metadata.csv
and save it to data/processed/pages.jsonl (one line per page).

Run from the project root:  python src/extract.py
"""

import csv
import json
from pathlib import Path

import pymupdf

RAW_DIR = Path("data/raw")
METADATA_FILE = Path("data/metadata.csv")
OUT_FILE = Path("data/processed/pages.jsonl")


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Read metadata.csv into a list of dictionaries (one per PDF)
    with open(METADATA_FILE, encoding="utf-8") as f:
        documents = list(csv.DictReader(f))
    print(f"{len(documents)} documents listed in metadata.csv")

    total_pages = 0
    nearly_empty_pages = 0

    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for doc in documents:
            pdf_path = RAW_DIR / doc["filename"]
            if not pdf_path.exists():
                print(f"   MISSING: {pdf_path}")
                continue

            with pymupdf.open(pdf_path) as pdf:
                for page_number, page in enumerate(pdf, start=1):
                    text = page.get_text("text")

                    # Pages with almost no text are probably charts or images
                    if len(text.strip()) < 100:
                        nearly_empty_pages += 1

                    record = {
                        "filename": doc["filename"],
                        "doc_type": doc["doc_type"],
                        "year": int(doc["year"]),
                        "section_type": doc["section_type"],
                        "title": doc["title"],
                        "page": page_number,
                        "text": text,
                    }
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total_pages += 1

            print(f"   done: {doc['filename']}")

    print(f"\nTotal pages extracted: {total_pages}")
    print(f"Nearly empty pages (probably charts/images): {nearly_empty_pages}")
    print(f"Saved to {OUT_FILE}")


if __name__ == "__main__":
    main()