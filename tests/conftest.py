"""Shared helpers: build small PDFs in code so tests need no real papers and no API."""
import io

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

FILLER = [
    "We study how attention layers combine information from different positions in a sequence.",
    "The model is trained on a large corpus and evaluated on two standard translation benchmarks.",
    "Our experiments show consistent gains over recurrent baselines while using less training time.",
    "We also report an ablation that removes one component at a time to measure its contribution.",
    "All hyperparameters were chosen on the development set and kept fixed for the final runs.",
]


def make_pdf(pages, filler_lines=28):
    """pages: list of dicts with optional keys:
       unique   - list of visible sentences to print
       white    - text drawn in white
       tiny     - text drawn at 1pt
       offpage  - text drawn outside the page
       filler   - set False to skip the filler paragraph
    """
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for page in pages:
        y = 800
        pdf.setFont("Helvetica", 10)
        pdf.setFillColorRGB(0, 0, 0)
        for sentence in page.get("unique", []):
            pdf.drawString(50, y, sentence)
            y -= 14
        if page.get("filler", True):
            for i in range(filler_lines):
                pdf.drawString(50, y, FILLER[i % len(FILLER)] + f" ({i})")
                y -= 14
        if page.get("white"):
            pdf.setFillColorRGB(1, 1, 1)
            pdf.drawString(50, 60, page["white"])
            pdf.setFillColorRGB(0, 0, 0)
        if page.get("tiny"):
            pdf.setFont("Helvetica", 1)
            pdf.drawString(50, 40, page["tiny"])
            pdf.setFont("Helvetica", 10)
        if page.get("offpage"):
            pdf.drawString(-900, 30, page["offpage"])
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.fixture
def paper_pdf():
    return make_pdf([
        {"unique": ["Attention Is All You Need (test copy)",
                    "We propose a new simple network architecture based solely on attention mechanisms."]},
        {"unique": ["The Transformer reaches 28.4 BLEU on the English to German translation task."]},
        {"unique": ["Training took 3.5 days on eight GPUs, a small fraction of the cost of earlier models."]},
    ])


class FakeClient:
    """Stands in for the Gemini client. Returns a fixed answer and records what it was sent."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def generate_json(self, system, user):
        self.calls.append((system, user))
        return self.answer(system, user) if callable(self.answer) else self.answer


def good_answer(**overrides):
    answer = {
        "title": "Attention Is All You Need",
        "what_this_paper_is": {"one_line": "It proposes the Transformer.", "explanation": "A new architecture based on attention."},
        "key_facts": [
            {"fact": "The model uses only attention.", "page": 1,
             "quote": "We propose a new simple network architecture based solely on attention mechanisms."},
            {"fact": "It reaches 28.4 BLEU.", "page": 2,
             "quote": "The Transformer reaches 28.4 BLEU on the English to German translation task."},
            {"fact": "Training is cheap.", "page": 3,
             "quote": "Training took 3.5 days on eight GPUs, a small fraction of the cost of earlier models."},
        ],
        "things_to_know": [
            {"point": "Tested on translation only.", "why_it_matters": "Other tasks are not shown."},
            {"point": "Needs a lot of memory for long inputs.", "why_it_matters": "Cost grows with length."},
        ],
        "key_terms": [{"term": "Attention", "definition": "A way to weigh which words matter."}],
    }
    answer.update(overrides)
    return answer
