# Paper Playground

A Streamlit app that explains one public research paper at a time: a short lesson in
three sections (what the paper is, key facts with page references, key things to know)
plus key-term cards. You can set the level, length and tone, and upload a PDF or find a
paper on arXiv.

Status: research-studio interface with personalized paper explanations. Follow-up Q&A is not included.

Choose level, tone, and length before generating an explanation. Results are organized into Overview, Key findings, Limitations, and Key terms. Supporting passages expand inside findings. Changing preferences requires an explicit Update explanation action.

Limits: 5 explanation attempts per visit, with shared daily caps of 100 explanations and 400 model requests. Cached results and prewritten examples do not consume another explanation allowance. Failed reserved model attempts also count.

## Run locally

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt   # app + test tools (the deployed app only needs requirements.txt)
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your key
    streamlit run app.py

## Run the tests (no API key needed)

    python -m pytest

The tests build small PDFs in code and use a fake model, so they cost nothing.
`tests/redteam/` attacks the app with hidden text, injected instructions and
fabricated quotes.

## How it works

1. Input checks: file size, readable text, page limit, public-paper checkbox, confidential markings, hidden-text removal.
2. The paper is wrapped as untrusted data in a random tag; the model returns JSON.
3. The JSON is validated and cleaned (no links or HTML).
4. Every key fact's quote is matched, word for word, against the cited PDF page. Unmatched facts are dropped.

**What "Quote matched" means:** those exact words are on that page. Digits, decimal points and signs are never
loosened, so 28.4 cannot match 98.4. It does not prove the claim is a fair reading of the quote. The app flags
claims that mention a number missing from their quote; judging support properly needs a separate check.

## Keeping the free tier alive

- One generation at a time, a per-visit allowance, and daily caps on lessons and API requests
  (a question cap is also built in, ready for the follow-up feature).
- Every API attempt is counted (a retry counts as a request), every call has a 90 s timeout.
- After 3 quota errors within 10 minutes, generation pauses for 15 minutes. Examples still work.
- The same file with the same settings is served from a small cache (20 lessons, 24 hours) with no model call.
- These limits protect availability. They are not a guarantee against abuse: a visitor can open a new session, and the
  daily counters live in the running app (a small temp file keeps them across reruns, not across a fresh deploy).

## Examples (no upload, no API key, no quota)

`examples/*.json` are complete lessons. Check them against the real PDFs (kept out of git) with:

    python scripts/check_examples.py

## Notes

- Uses a free-tier model API with billing disabled. Free-tier limits are shared and can change.
- Use public papers only. Free-tier content may be used by the provider to improve its products.
- Do not commit API keys or uploaded PDFs.
- The active PDF stays in server session memory until replaced or the session ends so preferences can be updated; it is not saved as a user library.

## Find a paper on arXiv

Instead of uploading, paste a title, an arXiv link or an arXiv ID. The app searches arXiv, shows up to three matches,
and downloads the one you pick. It never fetches a link you typed: it extracts an arXiv ID, checks it against a strict
pattern and builds the `arxiv.org` address itself. The downloaded PDF goes through exactly the same checks as an upload.

## Length limits

Files up to 15 MB are accepted. Only the first 80 pages are read (longer files are trimmed, and the lesson says so),
and at most about 300,000 characters are sent to the model. Files over 300 pages, scanned or image-only PDFs,
confidential-looking files and files full of instruction-like text are refused with a friendly message.

## Sidebar AI news

Displays up to three recent headlines from official OpenAI and Hugging Face RSS feeds.
Refreshes on the next app visit or hourly open-session check after the Pacific date changes.
This is an in-app refresh, not a scheduled job while the app is asleep. Dates and source links
are shown; headlines older than 14 days or in the future are excluded. Feed failures retry
after 15 minutes when checked and label retained results with their last successful refresh.
No model call, API key, paper upload, or explanation allowance is used for news.

## Waiting experience

When a visitor submits a new explanation, an in-memory FIFO waiting room starts
it automatically when the single generation slot becomes available. The waiting
panel refreshes every two seconds, shows its one-based waiting position, and offers
cancellation. The queue holds at most eight waiting tickets; a full queue asks the
visitor to retry without consuming an explanation allowance. Daily and per-visit
limits are checked when generation starts. Matching cached completions stay free.

Visitors must keep the page open. Tickets that receive no heartbeat for three
minutes expire, allowing others to proceed. The queue is scoped to the running app
process; a restart clears it. PDFs and settings stay in each session, not in the
shared ticket list. This is a small-app queue, not a durable distributed job system.
