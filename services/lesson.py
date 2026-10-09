"""Turn a prepared paper into a verified lesson.

Pipeline: wrap paper as data -> ask the model for JSON -> validate the shape ->
check every fact's quote against the paper -> keep only what is supported.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path

from safety.input_checks import MAX_PROMPT_CHARS, wrap_untrusted
from services.pdf_reader import Page
from services.schema import SchemaError, validate_lesson
from services.verify import FactResult, verify_facts

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "lesson_system.txt"
MIN_VERIFIED_FACTS = 3

LENGTHS = {
    "Short": "explanation 60 to 90 words; why_it_matters 1 or 2 sentences and 1 or 2 uses; example 40 to 70 words; "
             "3 or 4 key_facts; 2 or 3 things_to_know; 3 or 4 key_terms.",
    "Medium": "explanation 120 to 220 words; why_it_matters 2 or 3 sentences and 2 or 3 uses; example 90 to 150 words; "
              "4 to 6 key_facts; 3 to 5 things_to_know; 4 to 8 key_terms.",
    "Detailed": "explanation 250 to 400 words covering problem, idea, method, results and limits; why_it_matters 4 or 5 "
                "sentences and 3 or 4 uses; example 180 to 280 words; 6 to 8 key_facts; 4 to 6 things_to_know; 6 to 8 key_terms.",
}
LEVELS = {
    "Beginner": "assume no background. Use everyday words and define every technical term. EXAMPLE: an everyday story "
                "a school student could follow (like sorting notes, a group chat or cooking), with no formulas.",
    "Some background": "assume the reader knows basic statistics or programming. Explain only the specialised terms. "
                       "EXAMPLE: a short worked scenario with small, simple made-up numbers or a tiny dataset.",
    "Technical": "assume an expert reader. Use precise terminology and say how the method works and what was measured. "
                 "EXAMPLE: a concrete worked case of the method on a small input, naming each step and what is computed.",
}
TONES = {
    "Playful": "friendly and lively, light humour allowed in the explanation, example and things_to_know. Facts stay plain.",
    "Neutral": "calm, clear and professional.",
}
BEYOND_ON = ('also add a key "beyond_the_paper": a list of 2 or 3 short strings about related work, later developments or '
             "other uses from your general knowledge. Keep them general: no specific numbers, dates, names of papers or links, "
             "and say when you are unsure. These are NOT from the paper.")
BEYOND_OFF = 'do not include the key "beyond_the_paper".'


SCHEMA_VERSION = "2"  # bump when the lesson shape or the checks change, so old cached lessons are not reused


def prompt_fingerprint() -> str:
    """Changes whenever the prompt, the setting rules or the schema version change."""
    material = json.dumps([PROMPT_FILE.read_text(encoding="utf-8"), LENGTHS, LEVELS, TONES, BEYOND_ON, BEYOND_OFF,
                           SCHEMA_VERSION], sort_keys=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class LessonOptions:
    length: str = "Medium"
    level: str = "Beginner"
    tone: str = "Playful"
    beyond: bool = False  # add related work / uses from the model's own knowledge (not checked)

    def normalised(self) -> "LessonOptions":
        """Unknown values fall back to the defaults, so nothing unexpected reaches the prompt."""
        return LessonOptions(
            self.length if self.length in LENGTHS else "Medium",
            self.level if self.level in LEVELS else "Beginner",
            self.tone if self.tone in TONES else "Playful",
            self.beyond is True,
        )


class LessonError(Exception):
    """No safe lesson could be produced. The message is safe to show the visitor."""


@dataclass
class LessonResult:
    lesson: dict
    dropped: list[FactResult] = field(default_factory=list)
    pages_used: int = 0
    truncated: bool = False
    low_confidence: bool = False


def paper_text_for_prompt(pages: list[Page], max_chars: int = MAX_PROMPT_CHARS) -> tuple[str, list[Page], bool]:
    """Join pages with [PAGE n] tags, stopping before the size cap. Returns (text, pages_used, truncated)."""
    parts, used, total = [], [], 0
    for page in pages:
        block = f"[PAGE {page.number}]\n{page.text}"
        if total + len(block) > max_chars:
            return "\n\n".join(parts), used, True
        parts.append(block)
        used.append(page)
        total += len(block) + 2
    return "\n\n".join(parts), used, False


def build_messages(paper_text: str, options: LessonOptions | None = None) -> tuple[str, str, str]:
    """Returns (system, user, canary). The tag and the canary are random for every request."""
    options = (options or LessonOptions()).normalised()
    tag, wrapped = wrap_untrusted(paper_text)
    canary = "CANARY-" + secrets.token_hex(8)
    system = PROMPT_FILE.read_text(encoding="utf-8").replace("{{TAG}}", tag).replace("{{CANARY}}", canary)
    system = (system.replace("{{LEVEL_RULES}}", LEVELS[options.level])
              .replace("{{LENGTH_RULES}}", LENGTHS[options.length])
              .replace("{{TONE_RULES}}", TONES[options.tone])
              .replace("{{BEYOND_RULES}}", BEYOND_ON if options.beyond else BEYOND_OFF))
    user = "Explain this paper. Return only the JSON object.\n\n" + wrapped
    return system, user, canary


def generate_lesson(pages: list[Page], client, options: LessonOptions | None = None) -> LessonResult:
    paper_text, used, truncated = paper_text_for_prompt(pages)
    system, user, canary = build_messages(paper_text, options)
    lesson, reason = None, ""
    for attempt in range(2):  # one retry if the answer has the wrong shape
        raw = client.generate_json(system, user)
        if canary in str(raw):  # output guard: the secret marker must never come back
            raise LessonError("The answer was blocked by a safety check. Please try a different paper.")
        try:
            lesson = validate_lesson(raw, page_count=len(used))
            break
        except SchemaError as error:
            reason = str(error)
            keys = list(raw)[:8] if isinstance(raw, dict) else type(raw).__name__
            print(f"lesson attempt {attempt + 1}: {reason}; top-level keys: {keys}", file=sys.stderr)
    if lesson is None:
        raise LessonError(f"The model's answer did not have the expected shape ({reason}), so I did not show it.")

    if not (options and options.normalised().beyond):
        lesson["beyond_the_paper"] = []

    kept, dropped = verify_facts(lesson["key_facts"], used)
    if not kept:
        raise LessonError("None of the facts could be checked against the paper, so I did not show a lesson.")
    lesson["key_facts"] = kept
    return LessonResult(lesson=lesson, dropped=dropped, pages_used=len(used), truncated=truncated,
                        low_confidence=len(kept) < MIN_VERIFIED_FACTS)
