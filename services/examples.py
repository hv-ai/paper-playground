"""Pre-made example lessons that work with no upload, no API key and no quota.

Each file in examples/ is a complete lesson written from a public paper. Every quote in it was
checked against the real PDF by scripts/check_examples.py (and by a test whenever the PDF is
available locally). When loaded, a lesson goes through the same validation as a live answer.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from services.lesson import LessonOptions, LessonResult
from services.pipeline import PreparedPaper
from services.schema import validate_lesson
from services.verify import numbers_missing_from_quote

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
_SLUG = re.compile(r"^[a-z0-9-]{1,60}$")


@dataclass
class Example:
    slug: str
    label: str
    source: dict
    options: LessonOptions
    result: LessonResult
    prepared: PreparedPaper


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def list_examples() -> list[tuple[str, str]]:
    """(slug, label) for every example file, sorted by label."""
    found = []
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        if _SLUG.match(path.stem):
            try:
                found.append((path.stem, _read(path)["label"]))
            except (OSError, ValueError, KeyError):
                continue
    return sorted(found, key=lambda item: item[1])


def load_example(slug: str) -> Example:
    """Load one example by slug. Only slugs that match an existing file are accepted."""
    if slug not in {s for s, _ in list_examples()}:
        raise KeyError("unknown example")
    data = _read(EXAMPLES_DIR / f"{slug}.json")
    lesson = validate_lesson(data["lesson"], page_count=int(data["page_count"]))
    for fact in lesson["key_facts"]:
        fact["status"] = "matched"  # verified against the PDF when the example was built
        fact["numbers_not_in_quote"] = numbers_missing_from_quote(fact["fact"], fact["quote"])
    s = data.get("settings", {})
    options = LessonOptions(s.get("length", "Medium"), s.get("level", "Beginner"), s.get("tone", "Playful"),
                            bool(s.get("beyond", False))).normalised()
    lesson["beyond_the_paper"] = lesson["beyond_the_paper"] if options.beyond else []
    return Example(slug, data["label"], data.get("source", {}), options,
                   LessonResult(lesson=lesson, pages_used=int(data["page_count"])),
                   PreparedPaper(pages=[], held_out=[], hidden_chars_removed=0))
