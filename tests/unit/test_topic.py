import json
from datetime import date

from services.topic import MAX_AGE_DAYS, load_topic

GOOD = {"as_of": "2026-10-09", "title": "T", "hook": "H", "explain": "E",
        "source_title": "S", "source_url": "https://example.com/x"}


def write(tmp_path, data):
    path = tmp_path / "t.json"
    path.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")
    return path


def test_fresh_topic_loads(tmp_path):
    topic = load_topic(date(2026, 10, 12), write(tmp_path, GOOD))
    assert topic and topic.title == "T" and topic.as_of == date(2026, 10, 9)


def test_stale_future_or_broken_topics_are_hidden(tmp_path):
    assert load_topic(date(2026, 10, 9) + __import__("datetime").timedelta(days=MAX_AGE_DAYS + 1), write(tmp_path, GOOD)) is None
    assert load_topic(date(2026, 10, 1), write(tmp_path, GOOD)) is None  # dated in the future
    assert load_topic(date(2026, 10, 9), write(tmp_path, "not json")) is None
    assert load_topic(date(2026, 10, 9), tmp_path / "missing.json") is None
    assert load_topic(date(2026, 10, 9), write(tmp_path, {**GOOD, "title": " "})) is None
    assert load_topic(date(2026, 10, 9), write(tmp_path, {**GOOD, "source_url": "javascript:alert(1)"})) is None
    assert load_topic(date(2026, 10, 9), write(tmp_path, {**GOOD, "hook": 5})) is None


def test_the_shipped_file_is_valid_when_fresh():
    from services.topic import TOPIC_FILE
    data = json.loads(TOPIC_FILE.read_text(encoding="utf-8"))
    assert load_topic(date.fromisoformat(data["as_of"])) is not None
