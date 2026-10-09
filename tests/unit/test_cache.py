from services.cache import CachedLesson, LessonCache, make_key
from services.lesson import LessonOptions, LessonResult


def entry(title="t"):
    return CachedLesson(LessonResult(lesson={"title": title}), held_out=[], hidden_chars_removed=0)


def test_same_file_and_settings_give_the_same_key_and_anything_else_changes_it():
    base = make_key(b"pdf-a", LessonOptions(), "m")
    assert base == make_key(b"pdf-a", LessonOptions(), "m")
    assert base != make_key(b"pdf-b", LessonOptions(), "m")
    assert base != make_key(b"pdf-a", LessonOptions(length="Short"), "m")
    assert base != make_key(b"pdf-a", LessonOptions(level="Technical"), "m")
    assert base != make_key(b"pdf-a", LessonOptions(tone="Neutral"), "m")
    assert base != make_key(b"pdf-a", LessonOptions(beyond=True), "m")
    assert base != make_key(b"pdf-a", LessonOptions(), "other-model")


def test_hit_miss_and_isolation():
    cache = LessonCache()
    assert cache.get("k") is None
    cache.put("k", entry("original"))
    got = cache.get("k")
    got.result.lesson["title"] = "changed by a caller"
    assert cache.get("k").result.lesson["title"] == "original"


def test_cache_is_bounded_and_drops_the_least_recently_used():
    cache = LessonCache(max_entries=3)
    for name in "abc":
        cache.put(name, entry(name))
    cache.get("a")                 # a is now the most recently used
    cache.put("d", entry("d"))     # evicts b
    assert len(cache) == 3 and cache.get("b") is None and cache.get("a") and cache.get("d")


def test_entries_expire():
    now = {"t": 0.0}
    cache = LessonCache(ttl_seconds=100, clock=lambda: now["t"])
    cache.put("k", entry())
    now["t"] = 99
    assert cache.get("k") is not None
    now["t"] = 200
    assert cache.get("k") is None and len(cache) == 0
