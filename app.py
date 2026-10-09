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

from services.ai_client import GeminiClient
from services.cache import CachedLesson, LessonCache, make_key
from services.errors import ModelError, QuotaExceeded
from services.examples import list_examples, load_example
from services.lesson import LENGTHS, LEVELS, TONES, LessonError, LessonOptions, generate_lesson
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
    return GeminiClient(api_key=api_key, model=model, before_attempt=_limiter.begin_api_attempt,
                        on_quota_error=_limiter.note_quota_error, on_success=_limiter.note_api_success)


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


def run(upload, client: GeminiClient, options: LessonOptions):
    with st.status("Working on it...", expanded=True) as status:
        st.write("Checking the file...")
        prepared = prepare_paper(upload.getvalue())  # raises PaperRejected before any model call
        st.write("Writing the lesson, then checking every quote against the paper...")
        result = generate_lesson(prepared.pages, client, options)
        status.update(label="Done", state="complete", expanded=False)
    return result, prepared


def main() -> None:
    limiter = get_limiter()
    usage = st.session_state.setdefault("usage", SessionUsage())

    with st.sidebar:
        st.markdown("### 📄 Your paper")
        is_public = st.checkbox("This is a public paper I am allowed to share. It is not confidential.")
        upload = st.file_uploader("Upload a PDF", type=["pdf"], disabled=not is_public)
        st.markdown("### 🎛️ Make it yours")
        length = st.select_slider("Length", options=list(LENGTHS), value="Medium")
        level = st.radio("Level", list(LEVELS), index=0)
        tone = st.radio("Tone", list(TONES), index=0, horizontal=True)
        beyond = st.toggle("Add related work and uses beyond the paper", value=False,
                           help="Comes from the AI's general knowledge. It is NOT checked against the paper and may be out of date.")
        go = st.button("✨ Explain this paper", type="primary", use_container_width=True,
                       disabled=not (is_public and upload))
        examples = dict(list_examples())
        open_example, choice = False, None
        if examples:
            st.markdown("### 🎁 No paper handy?")
            choice = st.selectbox("Open an example lesson", list(examples), format_func=examples.get)
            open_example = st.button("📚 Open example (free, instant)", use_container_width=True)
        st.caption(f"Free capacity left today: {limiter.lessons_left_today()} papers")
        st.caption(f"This visit: {usage.papers} of {limiter.session_papers} papers used")
        st.caption("Uses a free-tier AI model. Text from your PDF is sent to the model provider, so use public papers only.")

    st.markdown(style.HERO, unsafe_allow_html=True)

    if open_example and choice:  # works with no API key, no quota and during a cooldown
        example = load_example(choice)
        st.session_state["shown"] = (example.result, example.prepared, example.options)
        st.session_state["from_cache"] = False
        st.session_state["example"] = example.source

    if go:
        options = LessonOptions(length, level, tone, beyond).normalised()
        api_key, model = secret("GEMINI_API_KEY"), secret("GEMINI_MODEL", "gemini-3.5-flash-lite")
        cache = get_cache()
        key = make_key(upload.getvalue(), options, model or "")
        cached = cache.get(key)
        if cached is not None:  # same file and settings as before: no model call, no quota, no allowance used
            st.session_state["shown"] = (cached.result, PreparedPaper([], cached.held_out, cached.hidden_chars_removed), options)
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
                    result, prepared = run(upload, get_client(api_key, model, limiter), options)
                    cache.put(key, CachedLesson(result, prepared.held_out, prepared.hidden_chars_removed))
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
