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

## Notes

- Uses a free-tier model API with billing disabled. Free-tier limits are shared and can change.
- Use public papers only. Free-tier content may be used by the provider to improve its products.
- Do not commit API keys or uploaded PDFs.
