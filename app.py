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
from services.news import NewsFeed, PACIFIC
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

    overview, findings, limitations, terms = st.tabs(["Overview", "Key findings", "Limitations", "Key terms"])
    with overview:
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

    with findings:
        st.caption("“Quote matched” means those exact words are on that page of the paper. "
                   "It does not prove the claim is a fair reading of the quote, so judge that yourself.")
        for i, fact in enumerate(lesson["key_facts"]):
            with st.container(border=True):
                left, right = st.columns([1, 14])
                left.markdown(f'<span class="pp-num c{i % 4}">{i + 1}</span>', unsafe_allow_html=True)
                right.markdown("**" + md_safe(fact["fact"]) + "**")
                with right.expander(f"Read supporting passage · PDF page {int(fact['page'])}"):
                    st.markdown("> " + md_safe(fact["quote"]))
                note = " · page number corrected" if fact.get("status") == "page_corrected" else ""
                css = "pp-badge warn" if note else "pp-badge"
                right.markdown(f'<span class="{css}">✓ Quote matched · PDF page {int(fact["page"])}{note}</span>',
                               unsafe_allow_html=True)
                if fact.get("numbers_not_in_quote"):
                    numbers = ", ".join(md_safe(n) for n in fact["numbers_not_in_quote"][:4])
                    right.warning(f"The claim mentions {numbers}, which is not in the quote. Check this one against the paper.",
                                  icon="⚠️")

    with limitations:
        st.caption("Limitations, assumptions, and caveats from the explanation. These items are not independently quote-checked.")
        for i, item in enumerate(lesson["things_to_know"]):
            left, right = st.columns([1, 14])
            left.markdown(f'<span class="pp-dot c{i % 4}">{"◆✦●★"[i % 4]}</span>', unsafe_allow_html=True)
            right.markdown("**" + md_safe(item["point"]) + "**  \n" + md_safe(item["why_it_matters"]))

        if lesson.get("beyond_the_paper"):
            st.markdown(style.subhead("🔭 Beyond the paper"), unsafe_allow_html=True)
            for point in lesson["beyond_the_paper"]:
                st.markdown("- " + md_safe(point))

    with terms:
        if lesson["key_terms"]:
            for entry in lesson["key_terms"]:
                with st.expander(md_safe(entry["term"])):
                    st.markdown(md_safe(entry["definition"]))
        else:
            st.info("No key terms were extracted for this paper.")

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
    with st.status("Preparing your explanation...", expanded=True) as status:
        st.write("Checking the file...")
        prepared = prepare_paper(pdf_bytes)  # raises PaperRejected before any model call
        st.write("Writing the lesson, then checking every quote against the paper...")
        result = generate_lesson(prepared.pages, client, options)
        status.update(label="Explanation ready", state="complete", expanded=False)
    return result, prepared


@st.cache_resource
def get_news_feed() -> NewsFeed:
    return NewsFeed()


@st.fragment(run_every="1h")
def sidebar_news() -> None:
    st.markdown("### Latest AI news")
    snapshot = get_news_feed().latest()
    if snapshot.items:
        for item in snapshot.items:
            st.link_button(item.title, item.url, use_container_width=True)
            st.caption(f"{item.source} · {item.published.astimezone(PACIFIC):%b %d, %Y}")
        label = "Last successful refresh" if snapshot.stale else "Checked"
        st.caption(f"{label}: {snapshot.checked.astimezone(PACIFIC):%b %d, %I:%M %p} PT")
        if snapshot.partial:
            st.caption("Some news sources are temporarily unavailable.")
    else:
        st.caption("News is temporarily unavailable." if snapshot.partial else "No headlines published in the last 14 days.")
    st.caption("Refreshes daily when the app is in use · Publisher headlines")


def main() -> None:
    st.session_state.pop("question_index", None)
    st.session_state.pop("question_history", None)
    limiter = get_limiter()
    usage = st.session_state.setdefault("usage", SessionUsage())

    reading = "shown" in st.session_state
    with st.sidebar:
        st.markdown("### Paper Playground 🤓")
        st.caption("Understand the research.")
        if reading:
            if st.button("＋ Explore another paper", use_container_width=True):
                for name in ("shown", "example", "from_cache", "editing_preferences", "active_pdf", "fetched", "question_index", "question_history", "public_paper_confirmation"):
                    st.session_state.pop(name, None)
                st.session_state["upload_version"] = st.session_state.get("upload_version", 0) + 1
                st.rerun()
            with st.expander("About this explanation"):
                st.write("Key findings include page references and quotes matched against the source. A matched quote does not prove the interpretation is correct.")
        else:
            st.write("Your paper. Your level. Your tone.")
            st.caption("Start with a public PDF or find a paper on arXiv, then choose how you want it explained.")
        st.divider()
        sidebar_news()
        st.divider()
        with st.expander("Capacity and privacy"):
            st.caption(f"Capacity today: {limiter.lessons_left_today()} explanations")
            st.caption(f"This visit: {usage.papers} of {limiter.session_papers} explanations used")
            st.caption("Use public papers only. Paper text is sent to the model provider. Uploaded PDFs are not saved to disk; the active PDF is kept in this session so you can update the explanation.")

    st.markdown(style.HERO if not reading else style.WORKSPACE_HEADER, unsafe_allow_html=True)
    go, open_example, choice = False, False, None
    needs_public_confirmation = False
    pdf_bytes = st.session_state.get("active_pdf")
    length, level, tone, beyond = "Medium", "Beginner", "Playful", False

    if reading:
        shown_options = st.session_state["shown"][2]
        st.markdown("## " + md_safe(st.session_state["shown"][0].lesson["title"]))
        if st.button("Edit preferences", key="edit_preferences"):
            st.session_state["editing_preferences"] = not st.session_state.get("editing_preferences", False)
    show_form = not reading or st.session_state.get("editing_preferences", False)
    if show_form:
        with st.container(border=True, key="paper_setup"):
            if not reading:
                st.markdown("### 1. Choose your paper")
                upload_tab, arxiv_tab = st.tabs(["Upload PDF", "Find on arXiv"])
                with upload_tab:
                    upload = st.file_uploader("Choose your research paper", type=["pdf"],
                                              key=f"upload_{st.session_state.get('upload_version', 0)}")
                    st.caption("PDF · up to 15 MB · readable text required")
                    is_public = st.checkbox("I confirm this PDF is public and not confidential.", key="public_paper_confirmation")
                    if not is_public:
                        st.caption("You can select a file now. Check the confirmation above to enable its explanation; no PDF text is sent to the model until you confirm and click Explain.")
                with arxiv_tab:
                    query = st.text_input("Paper title, arXiv link or ID", max_chars=300, key="arxiv_query",
                                          placeholder="Paste an arXiv link, ID, or a paper title")
                    if st.button("Find paper", use_container_width=True):
                        arxiv_search(query)
                    matches = st.session_state.get("arxiv_matches", [])
                    if matches:
                        pick = st.radio("Choose a paper", range(len(matches)), key="arxiv_pick",
                                        format_func=lambda i: md_safe(f"{matches[i].title} ({matches[i].authors}, {matches[i].year})"))
                        if st.button("Use this paper", use_container_width=True):
                            arxiv_fetch(matches[pick])
                fetched = st.session_state.get("fetched")
                if fetched:
                    st.success("Selected from arXiv: " + md_safe(fetched[1].title))
                    if st.button("Remove arXiv selection"):
                        del st.session_state["fetched"]
                        st.rerun()
                needs_public_confirmation = upload is not None and not is_public
                pdf_bytes = upload.getvalue() if upload is not None else (fetched[0] if fetched else None)
                if upload is not None and fetched:
                    st.caption("Your uploaded PDF will be used instead of the arXiv selection.")
            defaults = shown_options if reading else LessonOptions()
            st.markdown("### " + ("Reading preferences" if reading else "2. Make it yours"))
            st.caption("Level changes the depth. Tone changes the voice. Choose them independently.")
            level = st.radio("Your level", list(LEVELS), index=list(LEVELS).index(defaults.level), horizontal=True,
                             key="pref_level", help="Beginner assumes no background; Technical uses precise methods and terminology.")
            tone_col, length_col = st.columns(2)
            with tone_col:
                tone = st.radio("Tone", list(TONES), index=list(TONES).index(defaults.tone), horizontal=True, key="pref_tone")
                st.caption("Playful: friendly, with light humour. Neutral: calm and professional.")
            with length_col:
                length = st.select_slider("Length", options=list(LENGTHS), value=defaults.length, key="pref_length",
                                          format_func=lambda value: {"Short": "Quick read", "Medium": "Balanced", "Detailed": "Detailed"}[value])
            beyond = st.toggle("Include context beyond the paper", value=defaults.beyond, key="pref_beyond",
                               help="Uses the model's general knowledge. Not checked against the paper and may be out of date.")
            go = st.button("Update explanation" if reading else "Explain this paper →", type="primary",
                           use_container_width=True, disabled=pdf_bytes is None or needs_public_confirmation)
            if needs_public_confirmation:
                st.warning("One more step: confirm that your uploaded PDF is public to enable Explain this paper.")
            if reading and pdf_bytes is None:
                st.info("This is a prewritten example. Explore another paper and upload a PDF to generate an explanation with your own preferences.")
        if not reading:
            examples = dict(list_examples())
            if examples:
                with st.expander("Preview an existing example lesson"):
                    st.caption("Prewritten lessons show the experience instantly. Their original preferences are preserved.")
                    choice = st.selectbox("Example lesson", list(examples), format_func=examples.get)
                    open_example = st.button("Open example", help="No AI call or quota is used.")

    if open_example and choice:  # works with no API key, no quota and during a cooldown
        example = load_example(choice)
        st.session_state["shown"] = (example.result, example.prepared, example.options)
        st.session_state["from_cache"] = False
        st.session_state["example"] = example.source
        st.session_state.pop("active_pdf", None)
        st.session_state.pop("question_index", None)
        st.session_state.pop("question_history", None)
        for key, value in (("pref_level", example.options.level), ("pref_tone", example.options.tone),
                           ("pref_length", example.options.length), ("pref_beyond", example.options.beyond)):
            st.session_state.pop(key, None)
        st.rerun()

    if go and needs_public_confirmation:
        st.warning("Confirm that your PDF is public before generating an explanation.")
        go = False

    if go:
        previous_result = st.session_state.get("shown")
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
            st.warning("The explanation service is busy with another visitor. Your paper and preferences are still selected. Wait a moment, then click Explain again. You can browse an example while waiting.")
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

    if go and "shown" in st.session_state and st.session_state["shown"] is not previous_result:
        st.session_state["active_pdf"] = pdf_bytes
        st.session_state["editing_preferences"] = False
        st.rerun()

    if "shown" in st.session_state:
        source = st.session_state.get("example")
        if source:
            st.info("📚 **Example lesson.** Written in advance, so no AI call was used. Every quote was checked against the paper "
                    f"({md_safe(source.get('version', ''))}). Source: {md_safe(source.get('title', ''))}, {md_safe(source.get('authors', ''))}. "
                    f"{md_safe(source.get('note', ''))}")
        if st.session_state.get("from_cache"):
            st.info("⚡ Instant: this exact paper was explained earlier with the same settings. "
                    "This is a saved copy, so no new AI call was used.")
        with st.container(key="reading_workspace"):
            show_lesson(*st.session_state["shown"])
    else:
        st.markdown(style.STEPS, unsafe_allow_html=True)


main()
