"""Exercise navigation and explicit preference updates without model calls."""
from pathlib import Path

import pytest
from services.news import NewsFeed

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / 'app.py'


@pytest.fixture(autouse=True)
def offline_news(monkeypatch):
    original_init = NewsFeed.__init__
    monkeypatch.setattr(NewsFeed, '__init__', lambda self: original_init(self, fetcher=lambda *args: []))


def test_example_navigation_and_preferences():
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    next(b for b in app.button if b.label == 'Open example').click().run()
    assert [tab.label for tab in app.tabs] == ['Overview', 'Key findings', 'Limitations', 'Key terms']
    original = app.session_state['shown'][2]
    app.button(key='edit_preferences').click().run()
    app.radio(key='pref_tone').set_value('Neutral').run()
    assert app.session_state['shown'][2] == original
    assert next(b for b in app.button if b.label == 'Update explanation').disabled
    next(b for b in app.button if b.label == '＋ Explore another paper').click().run()
    assert 'shown' not in app.session_state
    assert any(b.label == 'Explain this paper →' for b in app.button)
    assert not app.exception


def test_cached_update_requires_button_and_keeps_pdf():
    # Seed a generated-paper session and its cache with verified example content.
    source = APP.read_text()
    seed = '''
if "seeded" not in st.session_state:
    example = load_example(list(list_examples())[0][0])
    st.session_state["shown"] = (example.result, example.prepared, example.options)
    st.session_state["active_pdf"] = b"test-paper-identity"
    st.session_state["seeded"] = True
    options = LessonOptions("Medium", "Beginner", "Neutral", False)
    key = make_key(b"test-paper-identity", options, secret("GEMINI_MODEL", "gemini-3.5-flash-lite"))
    get_cache().put(key, CachedLesson(example.result, [], 0, example.prepared.total_pages))
main()
'''
    app = AppTest.from_string(source.rsplit('main()', 1)[0] + seed).run()
    app.button(key='edit_preferences').click().run()
    before = app.session_state['shown'][2]
    app.radio(key='pref_tone').set_value('Neutral').run()
    app.select_slider(key='pref_length').set_value('Medium').run()
    app.radio(key='pref_level').set_value('Beginner').run()
    app.toggle(key='pref_beyond').set_value(False).run()
    assert app.session_state['shown'][2] == before
    next(b for b in app.button if b.label == 'Update explanation').click().run()
    assert not app.exception
    assert app.session_state['shown'][2].tone == 'Neutral'
    assert app.session_state['active_pdf'] == b'test-paper-identity'
    assert app.session_state['editing_preferences'] is False
    assert app.session_state['from_cache'] is True

