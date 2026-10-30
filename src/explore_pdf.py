"""
explore_pdf.py
Print the raw text of one PDF so we can see what we're dealing with.

Usage:  python src/explore_pdf.py data/raw/SOME_FILE.pdf
"""

import sys
import pymupdf

pdf_path = sys.argv[1]  # the file name you type after the command
pdf = pymupdf.open(pdf_path)

print(f"File: {pdf_path}")
print(f"Number of pages: {len(pdf)}")

# Show the first 3 pages
for page_number in range(min(3, len(pdf))):
    page = pdf[page_number]
    text = page.get_text("text")
    print("\n" + "=" * 30 + f" PAGE {page_number + 1} " + "=" * 30)
    print(text)