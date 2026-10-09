import json
import shutil
from pathlib import Path

import pytest

from services import examples as ex
from services.examples import list_examples, load_example


def test_at_least_one_example_exists_and_each_loads_through_the_normal_validation():
    items = list_examples()
    assert items
    for slug, label in items:
        example = load_example(slug)
        lesson = example.result.lesson
        assert label and lesson["title"] and len(lesson["key_facts"]) >= 3
        assert all(f["status"] == "matched" for f in lesson["key_facts"])
        assert not example.prepared.pages  # nothing from a user's file is involved


def test_example_loader_only_accepts_known_slugs():
    for bad in ("../../etc/passwd", "nope", "", "attention-is-all-you-need/../x", "ATTENTION"):
        with pytest.raises(KeyError):
            load_example(bad)


def test_examples_have_no_unflagged_number_mismatches():
    for slug, _ in list_examples():
        for fact in load_example(slug).result.lesson["key_facts"]:
            assert fact["numbers_not_in_quote"] == [], (slug, fact["fact"])


def test_example_files_are_well_formed():
    for path in Path(ex.EXAMPLES_DIR).glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("label", "source", "pdf_filename", "page_count", "settings", "lesson"):
            assert key in data, (path.name, key)
        assert "http" not in json.dumps(data["lesson"]).replace("https://arxiv.org", "")  # no links inside the lesson


def test_the_example_checker_catches_a_tampered_quote(tmp_path, monkeypatch):
    """If an example's quote is edited (28.4 -> 98.4), the checker against the real PDF must fail."""
    pdf = Path(ex.EXAMPLES_DIR).parent / "uploads" / "1706.03762v7.pdf"
    if not pdf.exists():
        pytest.skip("the Transformer PDF is not in uploads/")
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_examples", Path(ex.EXAMPLES_DIR).parent / "scripts" / "check_examples.py")
    check = importlib.util.module_from_spec(spec); spec.loader.exec_module(check)
    original = json.loads((Path(ex.EXAMPLES_DIR) / "attention-is-all-you-need.json").read_text(encoding="utf-8"))
    assert check.check_one(Path(ex.EXAMPLES_DIR) / "attention-is-all-you-need.json") == []
    original["lesson"]["key_facts"][1]["quote"] = original["lesson"]["key_facts"][1]["quote"].replace("28.4", "98.4")
    tampered = tmp_path / "t.json"
    tampered.write_text(json.dumps(original), encoding="utf-8")
    assert check.check_one(tampered)  # a non-empty list of problems
