# Paper Playground

A Streamlit app that explains one public research paper at a time: a short lesson,
key facts with page references, and cited answers to follow-up questions.

Status: in development (Week 1 project, GenAI Academy).

## Run locally

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your key
    streamlit run app.py

## Run the tests (no API key needed)

    python -m pytest

The tests build small PDFs in code and use a fake model, so they cost nothing.
`tests/redteam/` attacks the app with hidden text, injected instructions and
fabricated quotes.

## How it works

1. Input checks: size, page count, public-paper checkbox, confidential markings, hidden-text removal.
2. The paper is wrapped as untrusted data in a random tag; the model returns JSON.
3. The JSON is validated and cleaned (no links or HTML).
4. Every key fact's quote is matched, word for word, against the cited PDF page. Unmatched facts are dropped.

**What "Quote matched" means:** those exact words are on that page. Digits, decimal points and signs are never
loosened, so 28.4 cannot match 98.4. It does not prove the claim is a fair reading of the quote. The app flags
claims that mention a number missing from their quote; judging support properly needs a separate check.

## Keeping the free tier alive

- One generation at a time, a per-visit allowance, daily caps on lessons, questions and API requests.
- Every API attempt is counted (a retry counts as a request), every call has a 60 s timeout.
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
