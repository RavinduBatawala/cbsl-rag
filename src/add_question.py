"""
add_question.py
Helps you write test questions by hand - no PDF hunting needed.

  1. Type your question
  2. Type a keyword -> it shows every page that contains that word
  3. Pick the page that answers your question
  4. Type the answer in your own words

Each question is saved to data/eval/questions_manual.csv
Run from the project root:  python src/add_question.py
"""

import csv
import json
from pathlib import Path

PAGES_FILE = Path("data/processed/pages.jsonl")   # raw pages: page numbers match the PDFs
OUT_FILE = Path("data/eval/questions_manual.csv")
FIELDS = ["question", "answer", "gold_file", "gold_page_start", "gold_page_end", "origin", "keep"]
MAX_SHOWN = 15


def flatten(text):
    """Put the whole page on one line, so phrases split across lines can still be found."""
    return " ".join(text.split())


def snippet(text, keyword, width=150):
    """The text around the first place the keyword appears."""
    i = text.lower().find(keyword.lower())
    return "..." + text[max(0, i - width): i + len(keyword) + width] + "..."


def pick_page(pages):
    """Ask for keywords until the user picks a page. Returns that page."""
    while True:
        keyword = input("\nKeyword to search for: ").strip()
        if not keyword:
            continue
        matches = [p for p in pages if keyword.lower() in p["flat"].lower()]
        if not matches:
            print("   No page contains that word. Try another keyword.")
            continue

        shown = matches[:MAX_SHOWN]
        for n, p in enumerate(shown, start=1):
            print(f"\n[{n}] {p['filename']}  -  page {p['page']}")
            print(f"    {snippet(p['flat'], keyword)}")
        if len(matches) > MAX_SHOWN:
            print(f"\n(Showing {MAX_SHOWN} of {len(matches)} pages. "
                  f"A more specific keyword gives fewer results.)")

        choice = input("\nNumber of the page that answers your question "
                       "(or just press Enter to search again): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(shown):
            return shown[int(choice) - 1]


def main():
    with open(PAGES_FILE, encoding="utf-8") as f:
        pages = [json.loads(line) for line in f]
    for p in pages:
        p["flat"] = flatten(p["text"])
    print(f"Loaded {len(pages)} pages. Let's write some test questions!")

    added = 0
    while True:
        question = input("\n" + "=" * 70 + "\nYour question (or just press Enter to quit): ").strip()
        if not question:
            break

        page = pick_page(pages)
        continues = input("Does the answer continue onto the NEXT page? (y/n): ").strip().lower()
        page_end = page["page"] + 1 if continues == "y" else page["page"]
        answer = input("Now type the answer in your own words (1-2 sentences): ").strip()

        is_new = not OUT_FILE.exists()
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerow({
                "question": question,
                "answer": answer,
                "gold_file": page["filename"],
                "gold_page_start": page["page"],
                "gold_page_end": page_end,
                "origin": "manual",
                "keep": "yes",
            })
        added += 1
        print(f"   Saved! ({added} added this session)")

    print(f"\nDone. Your questions are in {OUT_FILE}")


if __name__ == "__main__":
    main()