import copy

import pytest

from services.schema import SchemaError, clean_model_text, validate_lesson
from tests.conftest import good_answer


def test_valid_answer_passes():
    lesson = validate_lesson(good_answer(), page_count=3)
    assert len(lesson["key_facts"]) == 3 and lesson["title"]


def test_links_and_html_are_stripped_from_text():
    ans = good_answer(title="<b>Hello</b> see https://evil.example/x now")
    lesson = validate_lesson(ans, page_count=3)
    assert "<" not in lesson["title"] and "http" not in lesson["title"]


def test_bad_pages_are_dropped_not_fatal():
    ans = good_answer()
    ans["key_facts"].append({"fact": "x", "page": 99, "quote": "q" * 40})
    ans["key_facts"].append({"fact": "x", "page": True, "quote": "q" * 40})
    ans["key_facts"].append({"fact": "x", "page": "abc", "quote": "q" * 40})
    assert len(validate_lesson(ans, page_count=3)["key_facts"]) == 3


def test_too_few_facts_is_an_error():
    ans = good_answer()
    ans["key_facts"] = ans["key_facts"][:1]
    with pytest.raises(SchemaError):
        validate_lesson(ans, page_count=3)


@pytest.mark.parametrize("bad", [None, [], "text", 5, {}])
def test_non_object_or_empty_is_an_error(bad):
    with pytest.raises(SchemaError):
        validate_lesson(bad, page_count=3)


def test_missing_section_is_an_error():
    ans = copy.deepcopy(good_answer())
    del ans["things_to_know"]
    with pytest.raises(SchemaError):
        validate_lesson(ans, page_count=3)


def test_lengths_are_capped():
    assert len(clean_model_text("a " * 2000, 100)) <= 100


def _rich():
    ans = good_answer()
    ans["why_it_matters"] = {"summary": "Translation was slow. See https://x.example", "uses": ["Translation", "<b>Summaries</b>"]}
    ans["example"] = {"title": "Passing notes", "walkthrough": "Imagine a class where everyone can read every note."}
    ans["beyond_the_paper"] = ["Later models build on this idea."]
    return ans


def test_new_sections_are_read_and_cleaned():
    lesson = validate_lesson(_rich(), page_count=3)
    assert "http" not in lesson["why_it_matters"]["summary"]
    assert lesson["why_it_matters"]["uses"] == ["Translation", "Summaries"]
    assert lesson["example"]["title"] == "Passing notes"
    assert lesson["beyond_the_paper"] == ["Later models build on this idea."]


def test_missing_new_sections_do_not_break_the_lesson():
    lesson = validate_lesson(good_answer(), page_count=3)
    assert lesson["why_it_matters"] is None and lesson["example"] is None and lesson["beyond_the_paper"] == []


def test_garbage_in_new_sections_is_ignored():
    ans = good_answer(why_it_matters="nope", example=5, beyond_the_paper="oops")
    lesson = validate_lesson(ans, page_count=3)
    assert lesson["why_it_matters"] is None and lesson["example"] is None and lesson["beyond_the_paper"] == []
