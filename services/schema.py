"""Check the model's JSON before the app trusts it, and clean every string in it.

The model's answer is treated as untrusted input. We accept only the exact shape
we asked for, cap every length, strip links and markup, and reject anything else.
"""
from __future__ import annotations

import re
import unicodedata

MAX_LEN = {
    "title": 200, "one_line": 300, "explanation": 3200,
    "fact": 400, "quote": 500, "point": 300, "why_it_matters": 400,
    "term": 60, "definition": 300,
    "why_summary": 1200, "use": 220, "example_title": 120, "walkthrough": 2200, "beyond": 300,
}
LIMITS = {"key_facts": (2, 8), "things_to_know": (1, 6), "key_terms": (0, 8)}

_URL = re.compile(r"(https?://\S+|www\.\S+|\b[\w.-]+\.(com|org|net|io|ai|co)/\S*)", re.I)
_TAG = re.compile(r"<[^>]*>")


class SchemaError(ValueError):
    """The model's answer did not have the shape we require."""


def clean_model_text(value: object, max_len: int, strip_urls: bool = True) -> str:
    if not isinstance(value, str):
        raise SchemaError("expected text")
    text = unicodedata.normalize("NFKC", value)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf"
                   and (unicodedata.category(ch) != "Cc" or ch in "\n\t"))
    text = _TAG.sub("", text)
    if strip_urls:
        text = _URL.sub("", text)
    text = " ".join(text.split())
    if not text:
        raise SchemaError("empty text")
    return text[:max_len]


def _page_number(value: object) -> int:
    """Accept 3, "3" or "Page 3"; reject booleans and anything without a number."""
    if isinstance(value, bool):
        raise SchemaError("bad page")
    if isinstance(value, int):
        return value
    match = re.search(r"\d+", str(value))
    if not match:
        raise SchemaError("bad page")
    return int(match.group())


def _need(obj: dict, key: str):
    if not isinstance(obj, dict) or key not in obj:
        raise SchemaError(f"missing '{key}'")
    return obj[key]


def _list(obj: dict, key: str) -> list:
    value = _need(obj, key)
    if not isinstance(value, list):
        raise SchemaError(f"'{key}' must be a list")
    return value


def _optional_why(value) -> dict | None:
    try:
        uses = []
        for use in (value.get("uses") or [])[:4]:
            try:
                uses.append(clean_model_text(use, MAX_LEN["use"]))
            except SchemaError:
                continue
        return {"summary": clean_model_text(value["summary"], MAX_LEN["why_summary"]), "uses": uses}
    except (SchemaError, AttributeError, KeyError, TypeError):
        return None


def _optional_example(value) -> dict | None:
    try:
        return {"title": clean_model_text(value["title"], MAX_LEN["example_title"]),
                "walkthrough": clean_model_text(value["walkthrough"], MAX_LEN["walkthrough"])}
    except (SchemaError, AttributeError, KeyError, TypeError):
        return None


def _optional_beyond(value) -> list:
    if not isinstance(value, list):
        return []
    items = []
    for entry in value[:4]:
        try:
            items.append(clean_model_text(entry, MAX_LEN["beyond"]))
        except SchemaError:
            continue
    return items


def validate_lesson(data: object, page_count: int) -> dict:
    """Return a cleaned lesson dict, or raise SchemaError."""
    if not isinstance(data, dict):
        raise SchemaError("the answer was not a JSON object")

    intro = _need(data, "what_this_paper_is")
    lesson = {
        "title": clean_model_text(_need(data, "title"), MAX_LEN["title"]),
        "what_this_paper_is": {
            "one_line": clean_model_text(_need(intro, "one_line"), MAX_LEN["one_line"]),
            "explanation": clean_model_text(_need(intro, "explanation"), MAX_LEN["explanation"]),
        },
        "key_facts": [], "things_to_know": [], "key_terms": [],
    }

    # New sections are optional on purpose: if the model leaves one out, the rest of the lesson still shows.
    lesson["why_it_matters"] = _optional_why(data.get("why_it_matters"))
    lesson["example"] = _optional_example(data.get("example"))
    lesson["beyond_the_paper"] = _optional_beyond(data.get("beyond_the_paper"))

    for item in _list(data, "key_facts")[: LIMITS["key_facts"][1]]:
        try:
            page = _page_number(_need(item, "page"))
            if not 1 <= page <= page_count:
                raise SchemaError("page out of range")
            lesson["key_facts"].append({
                "fact": clean_model_text(_need(item, "fact"), MAX_LEN["fact"]),
                "quote": clean_model_text(_need(item, "quote"), MAX_LEN["quote"], strip_urls=False),
                "page": page,
            })
        except (SchemaError, TypeError, ValueError):
            continue  # one bad fact should not sink the lesson; it is simply not shown

    for item in _list(data, "things_to_know")[: LIMITS["things_to_know"][1]]:
        try:
            lesson["things_to_know"].append({
                "point": clean_model_text(_need(item, "point"), MAX_LEN["point"]),
                "why_it_matters": clean_model_text(_need(item, "why_it_matters"), MAX_LEN["why_it_matters"]),
            })
        except SchemaError:
            continue

    for item in (data.get("key_terms") or [])[: LIMITS["key_terms"][1]]:
        try:
            lesson["key_terms"].append({
                "term": clean_model_text(_need(item, "term"), MAX_LEN["term"]),
                "definition": clean_model_text(_need(item, "definition"), MAX_LEN["definition"]),
            })
        except SchemaError:
            continue

    if len(lesson["key_facts"]) < LIMITS["key_facts"][0]:
        raise SchemaError("too few usable key facts")
    if len(lesson["things_to_know"]) < LIMITS["things_to_know"][0]:
        raise SchemaError("too few usable 'things to know'")
    return lesson
