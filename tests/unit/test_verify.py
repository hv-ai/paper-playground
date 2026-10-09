from services.pdf_reader import Page
from services.verify import (normalise_quote, numbers_in, numbers_missing_from_quote, quote_in_page,
                             verify_fact, verify_facts)

BLEU = "Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the best results."
PAGES = [
    Page(1, "Intro text.\nWe propose a new simple network architecture, the Transformer,\nbased solely on attention mechanisms, dis-\npensing with recurrence entirely.", 0),
    Page(2, BLEU, 0),
]
QUOTE = "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms"


def test_exact_quote_matches_despite_line_breaks_and_case():
    assert verify_fact({"fact": "f", "quote": QUOTE, "page": 1}, PAGES).status == "matched"
    assert verify_fact({"fact": "f", "quote": QUOTE.upper(), "page": 1}, PAGES).status == "matched"


def test_line_end_hyphenation_is_handled():
    q = "based solely on attention mechanisms, dispensing with recurrence entirely"
    assert verify_fact({"fact": "f", "quote": q, "page": 1}, PAGES).status == "matched"
    kept = [Page(1, "a state-\nof-the-art system that was trained for many days on large data", 0)]
    assert verify_fact({"fact": "f", "quote": "a state-of-the-art system that was trained for many days", "page": 1}, kept).status == "matched"


def test_typographic_quotes_and_dashes_are_equal_to_plain_ones():
    page = [Page(1, "The “best” model reached a score of −3.5 on the held-out test set overall.", 0)]
    q = 'The "best" model reached a score of -3.5 on the held-out test set overall.'
    assert verify_fact({"fact": "f", "quote": q, "page": 1}, page).status == "matched"


# --- the two problems found in review -------------------------------------------------
def test_changed_number_in_the_quote_is_rejected():
    altered = BLEU.replace("28.4", "98.4")
    assert verify_fact({"fact": "f", "quote": altered, "page": 2}, PAGES).status == "unmatched"


def test_signs_and_decimals_are_never_ignored():
    page = [Page(1, "The change in accuracy was 3.5 points on the validation split after tuning the model.", 0)]
    for altered in ("The change in accuracy was -3.5 points on the validation split after tuning the model.",
                    "The change in accuracy was 35 points on the validation split after tuning the model.",
                    "The change in accuracy was 3.6 points on the validation split after tuning the model."):
        assert verify_fact({"fact": "f", "quote": altered, "page": 1}, page).status == "unmatched"


def test_wrong_claim_with_a_real_quote_is_flagged_not_called_supported():
    result = verify_fact({"fact": "The model scores 98.4 BLEU.", "quote": BLEU, "page": 2}, PAGES)
    assert result.status == "matched"            # the words are in the paper...
    assert result.numbers_not_in_quote == ["98.4"]  # ...but the claim's number is not in the quote


def test_claim_whose_numbers_are_in_the_quote_is_not_flagged():
    assert verify_fact({"fact": "It reaches 28.4 BLEU.", "quote": BLEU, "page": 2}, PAGES).numbers_not_in_quote == []


# --- other behaviour -----------------------------------------------------------------
def test_wrong_page_is_corrected():
    r = verify_fact({"fact": "f", "quote": QUOTE, "page": 2}, PAGES)
    assert r.status == "page_corrected" and r.fact["page"] == 1


def test_paraphrase_fabrication_and_short_quotes_are_unmatched():
    para = "We propose a new simple network design called the Transformer that relies only on attention"
    assert verify_fact({"fact": "f", "quote": para, "page": 1}, PAGES).status == "unmatched"
    assert verify_fact({"fact": "f", "quote": "Invented sentence that is not anywhere in this paper at all", "page": 1}, PAGES).status == "unmatched"
    assert verify_fact({"fact": "f", "quote": "the model", "page": 1}, PAGES).status == "unmatched"


def test_missing_a_word_is_not_a_match():
    q = "We propose a new network architecture, the Transformer, based solely on attention mechanisms"
    assert not quote_in_page(q, PAGES[0].text)


def test_verify_facts_splits_kept_and_dropped():
    facts = [{"fact": "a", "quote": QUOTE, "page": 1},
             {"fact": "b", "quote": "Completely invented sentence that is not in the paper at all", "page": 2}]
    kept, dropped = verify_facts(facts, PAGES)
    assert len(kept) == 1 and kept[0]["status"] == "matched" and len(dropped) == 1


def test_number_helpers():
    assert numbers_in("rose by 1,200 to -3.5 and +2.0 (2014)") == {"1200", "-3.5", "2.0", "2014"}
    assert numbers_missing_from_quote("28.4 and 41.8", "scores of 28.4") == ["41.8"]
    assert normalise_quote('  "Hello   world"… ') == "hello world"


def test_a_quote_cut_off_inside_a_number_does_not_match():
    page = [Page(1, "Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task overall.", 0)]
    assert verify_fact({"fact": "f", "quote": "Our model achieves 28", "page": 1}, page).status == "unmatched"
    assert verify_fact({"fact": "f", "quote": "model achieves 28. BLEU on the WMT", "page": 1}, page).status == "unmatched"
    ok = "Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task"
    assert verify_fact({"fact": "f", "quote": ok, "page": 1}, page).status == "matched"


def test_a_quote_that_starts_after_a_minus_sign_does_not_match():
    page = [Page(1, "Accuracy dropped, giving a change of -3.5 points on the validation split after tuning.", 0)]
    assert verify_fact({"fact": "f", "quote": "3.5 points on the validation split after tuning.", "page": 1}, page).status == "unmatched"
    assert verify_fact({"fact": "f", "quote": "a change of -3.5 points on the validation split", "page": 1}, page).status == "matched"
