"""
clean.py
Clean the raw page text from extract.py.

Problems it fixes:
  1. Headers/footers that repeat on many pages (e.g. "ANNUAL REPORT 2022")
  2. Number-only lines from tables and charts (e.g. "12.5  8.3  -2.1")
  3. Words split across lines (e.g. "infla-" / "tion")
  4. Sentences broken into many short lines -> joined back into paragraphs
  5. Odd characters (ligatures like "ﬁ", bullet symbols)

Input:  data/processed/pages.jsonl
Output: data/processed/pages_clean.jsonl

Run from the project root:  python src/clean.py
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

IN_FILE = Path("data/processed/pages.jsonl")
OUT_FILE = Path("data/processed/pages_clean.jsonl")

# A line is a "header/footer" if it appears on at least this share of a file's pages
REPEAT_THRESHOLD = 0.4

# Paragraphs with fewer words than this are dropped (mostly chart labels)
MIN_WORDS = 4


# ---------- Helper functions ----------

def normalize_line(line):
    """Lowercase and replace every number with '#', so
    'Annual Report 2022 | 45' and 'Annual Report 2022 | 46' count as the same line."""
    return re.sub(r"\d+", "#", line.strip().lower())


def find_repeated_lines(pages):
    """Find lines that appear on many pages of the same PDF (headers/footers)."""
    if len(pages) < 3:  # too few pages to tell what is "repeated"
        return set()
    counts = Counter()
    for page in pages:
        # use a set so a line is counted once per page
        lines_on_page = {normalize_line(l) for l in page["text"].splitlines() if l.strip()}
        counts.update(lines_on_page)
    min_pages = REPEAT_THRESHOLD * len(pages)
    return {line for line, count in counts.items() if count >= min_pages}


def is_numeric_junk(line):
    """True for lines that are mostly numbers/symbols, e.g. table rows or chart axes."""
    chars = line.replace(" ", "")
    if not chars:
        return True
    letters = sum(c.isalpha() for c in chars)
    return letters / len(chars) < 0.3


def join_into_paragraphs(lines):
    """PDFs break sentences into many lines. Glue a line onto the previous one
    unless the previous one ended a sentence or the new line is a bullet point."""
    paragraphs = []
    current = ""
    for line in lines:
        starts_bullet = line.startswith("•")
        if not current:
            current = line
        elif current.endswith((".", "?", "!", ":")) or starts_bullet:
            paragraphs.append(current)
            current = line
        else:
            current += " " + line
    if current:
        paragraphs.append(current)
    return paragraphs


def clean_page(text, repeated_lines, stats):
    """Clean the text of one page. Updates `stats` with what was removed."""
    text = unicodedata.normalize("NFKC", text)        # "ﬁ" -> "fi" etc.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)       # "infla-\ntion" -> "inflation"

    kept_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if normalize_line(line) in repeated_lines:
            stats["header_footer_lines"] += 1
            continue
        if is_numeric_junk(line):
            stats["numeric_lines"] += 1
            continue
        kept_lines.append(line)

    paragraphs = []
    for p in join_into_paragraphs(kept_lines):
        p = p.lstrip("•").strip()
        p = re.sub(r"\s+", " ", p)                      # squash extra spaces
        if len(p.split()) < MIN_WORDS:
            stats["short_fragments"] += 1
            continue
        paragraphs.append(p)

    return "\n\n".join(paragraphs)


# ---------- Main program ----------

def main():
    # 1. Load all pages and group them by PDF file
    pages_by_file = defaultdict(list)
    with open(IN_FILE, encoding="utf-8") as f:
        for line in f:
            page = json.loads(line)
            pages_by_file[page["filename"]].append(page)
    print(f"Loaded {sum(len(p) for p in pages_by_file.values())} pages "
          f"from {len(pages_by_file)} files")

    stats = Counter()
    chars_before = 0
    chars_after = 0
    pages_written = 0

    # 2. Clean each file's pages and write them out
    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for filename, pages in pages_by_file.items():
            repeated = find_repeated_lines(pages)
            for page in pages:
                cleaned = clean_page(page["text"], repeated, stats)
                chars_before += len(page["text"])
                chars_after += len(cleaned)
                if not cleaned:
                    stats["pages_dropped_empty"] += 1
                    continue
                page["text"] = cleaned
                out.write(json.dumps(page, ensure_ascii=False) + "\n")
                pages_written += 1

    # 3. Report what happened
    print("\nWhat was removed:")
    for reason, count in stats.items():
        print(f"   {reason}: {count}")
    print(f"\nCharacters before: {chars_before:,}")
    print(f"Characters after:  {chars_after:,}  ({chars_after / chars_before:.0%} kept)")
    print(f"Pages written: {pages_written}  ->  {OUT_FILE}")


if __name__ == "__main__":
    main()