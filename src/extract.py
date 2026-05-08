"""Extract clean text from an academic PDF.

Strategy:
  - pymupdf (fast, accurate on most papers)
  - heuristic to drop References/Bibliography section (saves ~30% tokens, rarely useful for dialogue)
  - preserve section structure with simple headings so the LLM has anchors

Usage:
  python -m src.extract papers/foo.pdf > extracted.txt
"""

import re
import sys
from pathlib import Path

import fitz  # pymupdf


# Headings that typically mark the start of content we don't want in the dialogue
STOP_HEADINGS = re.compile(
    r"^\s*(references|bibliography|works cited|acknowledg(e)?ments?|"
    r"author contributions|funding|conflict[s]? of interest|"
    r"supplementary (materials?|information))\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def extract_pdf(path: Path) -> dict:
    """Return {title, text, num_pages}. Title is best-effort from page 1."""
    doc = fitz.open(path)
    pages = [page.get_text("text") for page in doc]
    full_text = "\n\n".join(pages)

    # Best-effort title: first non-empty line of page 1 that looks title-ish
    # (not all caps, not a single word, between 4 and 200 chars)
    title = path.stem  # fallback
    for line in pages[0].splitlines():
        line = line.strip()
        if 4 <= len(line) <= 200 and not line.isupper() and len(line.split()) >= 2:
            title = line
            break

    # Truncate at first stop heading
    match = STOP_HEADINGS.search(full_text)
    if match:
        full_text = full_text[: match.start()]

    # Light cleanup: collapse triple+ newlines, strip page-number-only lines
    full_text = re.sub(r"\n\s*\d+\s*\n", "\n", full_text)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)

    return {
        "title": title,
        "text": full_text.strip(),
        "num_pages": len(pages),
    }


def main():
    if len(sys.argv) != 2:
        print("usage: python -m src.extract <pdf_path>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        sys.exit(1)

    result = extract_pdf(path)
    # Write to stdout in a simple delimited format the next stage can parse
    print(f"TITLE: {result['title']}")
    print(f"PAGES: {result['num_pages']}")
    print("---")
    print(result["text"])


if __name__ == "__main__":
    main()
