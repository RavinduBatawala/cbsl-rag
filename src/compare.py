"""
compare.py
Show one page before and after cleaning.

Usage:   python src/compare.py FILENAME PAGE
Example: python src/compare.py annual_report_2022_11_Chapter_07.pdf 5
"""

import json
import sys

filename = sys.argv[1]
page_number = int(sys.argv[2])


def find_page(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            page = json.loads(line)
            if page["filename"] == filename and page["page"] == page_number:
                return page["text"]
    return "(page not found - it may have been dropped as empty)"


print("=" * 30, "BEFORE", "=" * 30)
print(find_page("data/processed/pages.jsonl"))
print("=" * 30, "AFTER", "=" * 30)
print(find_page("data/processed/pages_clean.jsonl"))