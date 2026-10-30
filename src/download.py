"""
download.py
Downloads CBSL Annual Reports (2019-2022) and Annual Economic Reviews (2023-2025)
into data/raw/, and writes data/metadata.csv describing every file.

Run from the project root:  python src/download.py
"""

import csv
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ---------- Settings ----------

BASE = "https://www.cbsl.gov.lk/en/publications/economic-and-financial-reports"

# (document type, year, web page that lists that year's PDFs)
REPORTS = [
    ("annual_report", 2019, f"{BASE}/annual-reports/annual-report-2019"),
    ("annual_report", 2020, f"{BASE}/annual-reports/annual-report-2020"),
    ("annual_report", 2021, f"{BASE}/annual-reports/annual-report-2021"),
    ("annual_report", 2022, f"{BASE}/annual-reports/annual-report-2022"),
    ("economic_review", 2023, f"{BASE}/annual-economic-review/annual-economic-review-2023"),
    ("economic_review", 2024, f"{BASE}/annual-economic-review/annual-economic-review-2024"),
    ("economic_review", 2025, f"{BASE}/annual-economic-review/annual-economic-review-2025"),
]

# We only keep PDFs whose file name contains one of these words
KEEP_WORDS = ["Chapter", "Box", "Executive_Summary"]

RAW_DIR = Path("data/raw")
METADATA_FILE = Path("data/metadata.csv")
HEADERS = {"User-Agent": "Mozilla/5.0 (student research project)"}


# ---------- Helper functions ----------

def get_section_type(filename):
    """Turn a file name like '6_Chapter_02.pdf' into 'chapter'."""
    if "Chapter" in filename:
        return "chapter"
    if "Box" in filename:
        return "box"
    return "executive_summary"


def find_pdf_links(page_url, year):
    """Open a report page and return the PDF links we want to keep."""
    response = requests.get(page_url, headers=HEADERS, timeout=30)
    response.raise_for_status()  # stop with an error if the page didn't load
    soup = BeautifulSoup(response.text, "html.parser")

    found = {}  # url -> title (a dict, so the same link is never added twice)
    for a in soup.find_all("a", href=True):
        url = urljoin(page_url, a["href"])
        filename = url.split("/")[-1]

        if not url.lower().endswith(".pdf"):
            continue
        if f"/{year}/" not in url:  # skip sidebar links to other reports
            continue
        if not any(word in filename for word in KEEP_WORDS):
            continue

        found[url] = a.get_text(strip=True)
    return found


def download_pdf(url, save_path):
    """Download one PDF. Skip it if we already have it."""
    if save_path.exists():
        print(f"   already have {save_path.name}")
        return True

    response = requests.get(url, headers=HEADERS, timeout=120)
    response.raise_for_status()

    if not response.content.startswith(b"%PDF"):  # every real PDF starts with %PDF
        print(f"   WARNING: {url} is not a PDF, skipping")
        return False

    save_path.write_bytes(response.content)
    print(f"   saved {save_path.name}")
    time.sleep(1)  # be polite: wait 1 second between downloads
    return True


# ---------- Main program ----------

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for doc_type, year, page_url in REPORTS:
        print(f"\n=== {doc_type} {year} ===")
        links = find_pdf_links(page_url, year)
        print(f"Found {len(links)} PDFs")
        if len(links) == 0:
            print("   WARNING: nothing found for this year - tell your advisor!")

        for url, title in links.items():
            original_name = url.split("/")[-1]
            # e.g. annual_report_2022_6_Chapter_02.pdf
            new_name = f"{doc_type}_{year}_{original_name}"

            if download_pdf(url, RAW_DIR / new_name):
                rows.append({
                    "filename": new_name,
                    "doc_type": doc_type,
                    "year": year,
                    "section_type": get_section_type(original_name),
                    "title": title,
                    "url": url,
                })

    # Write metadata.csv
    with open(METADATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Downloaded {len(rows)} files. Metadata saved to {METADATA_FILE}")


if __name__ == "__main__":
    main()