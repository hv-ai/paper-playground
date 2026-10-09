"""Paper Playground: upload a public research paper, get a lesson whose facts are checked.

Every piece of text that came from the paper or the model goes through md_safe() and is
shown in its own st.markdown call without HTML enabled. The only raw HTML is static: our
own CSS/markup in ui/style.py, plus small badges built from a page number we computed.
"""
from __future__ import annotations

import os
import sys
import tempfile

import streamlit as st

from safety.input_checks import MAX_PAGES
from services.ai_client import GeminiClient
from services.arxiv import ArxivClient, ArxivError
from services.cache import CachedLesson, LessonCache, make_key
from services.errors import ModelError, QuotaExceeded
from services.examples import list_examples, load_example
from services.lesson import LENGTHS, LEVELS, TONES, LessonError, LessonOptions, generate_lesson
from services.topic import load_topic
from services.limits import SessionUsage, UsageLimiter
from services.pipeline import PaperRejected, PreparedPaper, prepare_paper
from ui import style
from ui.safe_text import md_safe

st.set_page_config(page_title="Paper Playground", page_icon="🤓", layout="wide")
st.markdown(style.CSS, unsafe_allow_html=True)


def secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


@st.cache_resource
def get_limiter() -> UsageLimiter:
    # Daily counters are also saved to a small temp file so a rerun does not reset them (best effort).
    return UsageLimiter(state_path=os.path.join(tempfile.gettempdir(), "paper_playground_usage.json"))


@st.cache_resource
def get_cache() -> LessonCache:
    return LessonCache(max_entries=20, ttl_seconds=24 * 3600)  # bounded: 20 lessons, 24 hours, memory only


@st.cache_resource
def get_client(api_key: str, model: str, _limiter: UsageLimiter) -> GeminiClient:
    # Every API attempt is counted by the limiter, and refused during a cooldown.
    return GeminiClient(api_key=api_key, model=model, timeout_seconds=90, before_attempt=_limiter.begin_api_attempt,
                        on_quota_error=_limiter.note_quota_error, on_success=_limiter.note_api_success)


@st.cache_resource
def get_arxiv() -> ArxivClient:
    return ArxivClient()  # one shared client, so arXiv requests from all visitors stay spaced out


ARXIV_CALLS_PER_VISIT = 12

# Plain-language labels for the sidebar. The keys are the real option names used everywhere else.
LEVEL_LABELS = {"Beginner": "🌱 Beginner: no background needed",
                "Some background": "📘 Some background: knows basic stats or code",
                "Technical": "🔬 Technical: expert, precise terms"}
TONE_LABELS = {"Playful": "😄 Playful: friendly, a little humour",
               "Neutral": "🎓 Neutral: calm and professional"}


def arxiv_search(query: str) -> None:
    calls = st.session_state.get("arxiv_calls", 0)
    if calls >= ARXIV_CALLS_PER_VISIT:
        st.warning("You have used the arXiv lookups for this visit. Please upload the PDF instead.")
        return
    st.session_state["arxiv_calls"] = calls + 1
    st.session_state["arxiv_matches"] = []
    try:
        found = get_arxiv().find(query)
    except ArxivError as error:
        st.error(str(error))
        return
    if not found:
        st.warning("No match on arXiv. Try the exact title, or paste the arXiv link or ID.")
    st.session_state["arxiv_matches"] = found


def arxiv_fetch(match) -> None:
    calls = st.session_state.get("arxiv_calls", 0)
    if calls >= ARXIV_CALLS_PER_VISIT:
        st.warning("You have used the arXiv lookups for this visit. Please upload the PDF instead.")
        return
    st.session_state["arxiv_calls"] = calls + 1
    try:
        with st.spinner("Downloading from arXiv..."):
            data = get_arxiv().download(match.arxiv_id)
    except ArxivError as error:
        st.error(str(error))
        return
    st.session_state["fetched"] = (data, match)
    st.session_state["arxiv_matches"] = []


def show_lesson(result, prepared, options: LessonOptions) -> None:
    lesson = result.lesson
    st.markdown(f'<span class="pp-chip">Level: {options.level}</span><span class="pp-chip">Length: {options.length}</span>'
                f'<span class="pp-chip">Tone: {options.tone}</span>'
                + ('<span class="pp-chip">+ Beyond the paper</span>' if options.beyond else ""), unsafe_allow_html=True)  # values are our own fixed choices

    st.markdown(style.section("a", "📖 What this paper is"), unsafe_allow_html=True)
    st.markdown("### " + md_safe(lesson["title"]))
    st.markdown("**" + md_safe(lesson["what_this_paper_is"]["one_line"]) + "**")
    st.markdown(md_safe(lesson["what_this_paper_is"]["explanation"]))

    if lesson.get("why_it_matters"):
        st.markdown(style.subhead("🌍 Why it matters and where it is used"), unsafe_allow_html=True)
        st.markdown(md_safe(lesson["why_it_matters"]["summary"]))
        for use in lesson["why_it_matters"]["uses"]:
            st.markdown("- " + md_safe(use))
    if lesson.get("example"):
        st.markdown(style.subhead("🧩 Example"), unsafe_allow_html=True)
        st.markdown("**" + md_safe(lesson["example"]["title"]) + "**")
        st.markdown(md_safe(lesson["example"]["walkthrough"]))

    st.markdown(style.section("b", "🔎 Key facts"), unsafe_allow_html=True)
    st.caption("“Quote matched” means those exact words are on that page of the paper. "
               "It does not prove the claim is a fair reading of the quote, so judge that yourself.")
    for i, fact in enumerate(lesson["key_facts"]):
        with st.container(border=True):
            left, right = st.columns([1, 14])
            left.markdown(f'<span class="pp-num c{i % 4}">{i + 1}</span>', unsafe_allow_html=True)
            right.markdown("**" + md_safe(fact["fact"]) + "**")
            right.markdown("> " + md_safe(fact["quote"]))
            note = " · page number corrected" if fact.get("status") == "page_corrected" else ""
            css = "pp-badge warn" if note else "pp-badge"
            right.markdown(f'<span class="{css}">✓ Quote matched · PDF page {int(fact["page"])}{note}</span>',
                           unsafe_allow_html=True)
            if fact.get("numbers_not_in_quote"):
                numbers = ", ".join(md_safe(n) for n in fact["numbers_not_in_quote"][:4])
                right.warning(f"The claim mentions {numbers}, which is not in the quote. Check this one against the paper.",
                              icon="⚠️")

    st.markdown(style.section("c", "💡 Key things to know"), unsafe_allow_html=True)
    for i, item in enumerate(lesson["things_to_know"]):
        left, right = st.columns([1, 14])
        left.markdown(f'<span class="pp-dot c{i % 4}">{"◆✦●★"[i % 4]}</span>', unsafe_allow_html=True)
        right.markdown("**" + md_safe(item["point"]) + "**  \n" + md_safe(item["why_it_matters"]))

    if lesson.get("beyond_the_paper"):
        st.markdown(style.subhead("🔭 Beyond the paper"), unsafe_allow_html=True)
        for point in lesson["beyond_the_paper"]:
            st.markdown("- " + md_safe(point))

    if lesson["key_terms"]:
        st.markdown("##### 🔤 Key terms (tap one)")
        cols = st.columns(min(4, len(lesson["key_terms"])))
        for i, entry in enumerate(lesson["key_terms"]):
            with cols[i % len(cols)]:
                with st.popover(md_safe(entry["term"]), use_container_width=True):
                    st.markdown(md_safe(entry["definition"]))

    notes = []
    if result.dropped:
        notes.append(f"{len(result.dropped)} draft fact(s) were dropped because their quote was not found in the paper.")
    if prepared.held_out:
        notes.append(f"{len(prepared.held_out)} sentence(s) looked like instructions to an AI and were ignored.")
    if prepared.hidden_chars_removed:
        notes.append(f"{prepared.hidden_chars_removed} invisible or tiny character(s) were left out "
                     "(white, microscopic or off-page text, often figure labels).")
    if prepared.total_pages > MAX_PAGES:
        notes.append(f"This file has {prepared.total_pages} pages. Only the first {MAX_PAGES} were read, so later sections are not covered.")
    if result.truncated:
        notes.append(f"Only the first {result.pages_used} pages were used because the paper is long.")
    if result.low_confidence:
        st.warning("Only a few facts could be verified, so treat this lesson with extra care.")
    if notes:
        with st.expander("🛡️ Safety and accuracy notes"):
            for note in notes:
                st.markdown("- " + note)
            for held in prepared.held_out[:5]:
                st.markdown(f"- Ignored on page {int(held['page'])}: *{md_safe(held['snippet'])}*")


def run(pdf_bytes: bytes, client: GeminiClient, options: LessonOptions):
    with st.status("Working on it...", expanded=True) as status:
        st.write("Checking the file...")
        prepared = prepare_paper(pdf_bytes)  # raises PaperRejected before any model call
        st.write("Writing the lesson, then checking every quote against the paper...")
        result = generate_lesson(prepared.pages, client, options)
        status.update(label="Done", state="complete", expanded=False)
    return result, prepared


def main() -> None:
    limiter = get_limiter()
    usage = st.session_state.setdefault("usage", SessionUsage())

    with st.sidebar:
        st.markdown(style.ABOUT, unsafe_allow_html=True)
        topic = load_topic()
        if topic:
            st.markdown("### 🔭 AI topic of the week")
            st.markdown("**" + md_safe(topic.title) + "**")
            st.markdown(md_safe(topic.hook))
            st.markdown("💡 " + md_safe(topic.explain))
            st.caption(f"Updated {topic.as_of:%b %d, %Y} · Source: [{md_safe(topic.source_title)}]({topic.source_url})")
        st.divider()
        st.caption(f"Free capacity left today: {limiter.lessons_left_today()} papers")
        st.caption(f"This visit: {usage.papers} of {limiter.session_papers} papers used")
        st.caption("Uses a free-tier AI model. Text from your PDF is sent to the model provider, so use public papers only.")

    st.markdown(style.HERO, unsafe_allow_html=True)
    if "shown" not in st.session_state:
        st.markdown(style.WELCOME, unsafe_allow_html=True)

    with st.container(border=True):
        left, right = st.columns([1.15, 1], gap="large")
        with left:
            st.markdown("#### 📄 1. Pick a paper")
            is_public = st.checkbox("This is a public paper I am allowed to share. It is not confidential.")
            upload = st.file_uploader("Upload a PDF", type=["pdf"], disabled=not is_public)
            st.caption("Or find a paper on arXiv (arXiv papers are public, so the box above is not needed):")
            query = st.text_input("Paper title, arXiv link or ID", max_chars=300, key="arxiv_query",
                                  placeholder="Attention Is All You Need, or 1706.03762")
            if st.button("🔎 Find on arXiv", use_container_width=True):
                arxiv_search(query)
            matches = st.session_state.get("arxiv_matches", [])
            if matches:
                pick = st.radio("Pick the right paper", range(len(matches)), key="arxiv_pick",
                                format_func=lambda i: md_safe(f"{matches[i].title} ({matches[i].authors}, {matches[i].year})"))
                if st.button("Use this paper", use_container_width=True):
                    arxiv_fetch(matches[pick])
            fetched = st.session_state.get("fetched")
            if fetched:
                st.success("Ready: " + md_safe(fetched[1].title) + (" (your upload will be used instead)" if (is_public and upload) else ""))
                if st.button("✕ Remove this paper", use_container_width=True):
                    del st.session_state["fetched"]
                    st.rerun()
            pdf_bytes = upload.getvalue() if (is_public and upload) else (fetched[0] if fetched else None)
        with right:
            st.markdown("#### 🎛️ 2. Make it yours")
            length = st.select_slider("Length", options=list(LENGTHS), value="Medium",
                                      help="Short is a quick read. Detailed covers the problem, method, results and limits.")
            level = st.radio("Level", list(LEVELS), index=0, format_func=LEVEL_LABELS.get,
                             help="Changes the words used and the example. Beginner uses an everyday story.")
            tone = st.radio("Tone", list(TONES), index=0, format_func=TONE_LABELS.get,
                            help="Only the writing style changes. The checked facts stay plain either way.")
            beyond = st.toggle("Add related work and uses beyond the paper", value=False,
                               help="Comes from the AI's general knowledge. It is NOT checked against the paper and may be out of date.")
        go = st.button("✨ Explain this paper", type="primary", use_container_width=True, disabled=pdf_bytes is None)
        examples = dict(list_examples())
        open_example, choice = False, None
        if examples:
            st.markdown("##### 🎁 No paper handy?")
            ex_left, ex_right = st.columns([2, 1], gap="medium")
            with ex_left:
                choice = st.selectbox("Open an example lesson", list(examples), format_func=examples.get,
                                      label_visibility="collapsed")
            with ex_right:
                open_example = st.button("📚 Open example", use_container_width=True, help="Free and instant: no AI call is used.")

    if open_example and choice:  # works with no API key, no quota and during a cooldown
        example = load_example(choice)
        st.session_state["shown"] = (example.result, example.prepared, example.options)
        st.session_state["from_cache"] = False
        st.session_state["example"] = example.source

    if go:
        options = LessonOptions(length, level, tone, beyond).normalised()
        api_key, model = secret("GEMINI_API_KEY"), secret("GEMINI_MODEL", "gemini-3.5-flash-lite")
        cache = get_cache()
        key = make_key(pdf_bytes, options, model or "")
        cached = cache.get(key)
        if cached is not None:  # same file and settings as before: no model call, no quota, no allowance used
            st.session_state["shown"] = (cached.result, PreparedPaper([], cached.held_out, cached.hidden_chars_removed, cached.total_pages), options)
            st.session_state["from_cache"] = True
            st.session_state["example"] = None
        elif not api_key:
            st.error("This app is not configured yet (no API key).")
        elif not limiter.try_start():  # one generation at a time
            st.info("Another paper is being explained right now. Please try again in a minute.")
        else:
            try:
                reserved, message = limiter.reserve_lesson(usage)  # check and reserve in one atomic step
                if not reserved:
                    st.warning(message)
                else:
                    result, prepared = run(pdf_bytes, get_client(api_key, model, limiter), options)
                    cache.put(key, CachedLesson(result, prepared.held_out, prepared.hidden_chars_removed, prepared.total_pages))
                    st.session_state["shown"] = (result, prepared, options)
                    st.session_state["from_cache"] = False
                    st.session_state["example"] = None
            except PaperRejected as error:
                limiter.refund_lesson(usage)  # no model call was made, so give the reservation back
                st.error(str(error))
            except QuotaExceeded as error:
                st.warning(str(error) or "The free capacity for this app is used up for now. Please try again later.")
            except (ModelError, LessonError) as error:
                st.error(str(error))
            except Exception as error:  # never show internals to a visitor
                print(f"unexpected error: {type(error).__name__}", file=sys.stderr)
                st.error("Something went wrong. Please try again.")
            finally:
                limiter.finish()

    if "shown" in st.session_state:
        source = st.session_state.get("example")
        if source:
            st.info("📚 **Example lesson.** Written in advance, so no AI call was used. Every quote was checked against the paper "
                    f"({md_safe(source.get('version', ''))}). Source: {md_safe(source.get('title', ''))}, {md_safe(source.get('authors', ''))}. "
                    f"{md_safe(source.get('note', ''))}")
        if st.session_state.get("from_cache"):
            st.info("⚡ Instant: this exact paper was explained earlier with the same settings. "
                    "This is a saved copy, so no new AI call was used.")
        show_lesson(*st.session_state["shown"])
    else:
        st.markdown(style.STEPS, unsafe_allow_html=True)


main()
