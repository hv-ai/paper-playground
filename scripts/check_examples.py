"""Check every example lesson against its real PDF.

Usage (from the project folder, venv active):
    python scripts/check_examples.py

PDFs are not stored in the repo. Put each one in uploads/ under the file name given by
"pdf_filename" in the example's JSON. Exit code 0 means every quote was matched exactly.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.examples import EXAMPLES_DIR  # noqa: E402
from safety.input_checks import clean_text  # noqa: E402
from services.pdf_reader import Page, read_pdf  # noqa: E402
from services.schema import validate_lesson  # noqa: E402
from services.verify import verify_fact  # noqa: E402


def check_one(path: Path) -> list[str]:
    """Return a list of problems (empty = all good). Raises FileNotFoundError if the PDF is missing."""
    data = json.loads(path.read_text(encoding="utf-8"))
    pdf = ROOT / "uploads" / data["pdf_filename"]
    # Read every page. The live app limits uploads to 40 pages; examples may come from longer papers.
    pages = [Page(p.number, clean_text(p.text)) for p in read_pdf(pdf.read_bytes(), max_pages=500)]
    problems = []
    if len(pages) != int(data["page_count"]):
        problems.append(f"page_count is {data['page_count']} but the PDF has {len(pages)} pages")
    lesson = validate_lesson(data["lesson"], page_count=len(pages))
    for i, fact in enumerate(lesson["key_facts"], 1):
        result = verify_fact(fact, pages)
        if result.status != "matched":
            problems.append(f"fact {i}: {result.status} ({result.reason}) on cited page {fact['page']}")
        if result.numbers_not_in_quote:
            problems.append(f"fact {i}: numbers {result.numbers_not_in_quote} are not in the quote")
    if len(lesson["key_facts"]) != len(data["lesson"]["key_facts"]):
        problems.append("some facts were dropped by validation")
    return problems


def main() -> int:
    bad = 0
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        try:
            problems = check_one(path)
        except FileNotFoundError:
            print(f"SKIP  {path.name}: PDF not found in uploads/")
            continue
        print(("OK    " if not problems else "FAIL  ") + path.name)
        for problem in problems:
            print("      -", problem)
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
