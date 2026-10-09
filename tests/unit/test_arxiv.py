import urllib.error

import pytest

from services import arxiv
from services.arxiv import ArxivClient, ArxivError, is_arxiv_id, parse_query, parse_results

ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <id>http://arxiv.org/abs/1706.03762v7</id>
  <published>2017-06-12T17:57:34Z</published>
  <title>Attention Is All
   You Need</title>
  <author><name>Ashish Vaswani</name></author><author><name>Noam Shazeer</name></author>
  <author><name>Niki Parmar</name></author><author><name>Jakob Uszkoreit</name></author>
 </entry>
 <entry>
  <id>http://evil.example/abs/not-an-id</id>
  <title>Dropped: bad id</title>
 </entry>
 <entry>
  <id>http://arxiv.org/abs/2101.00001v1</id>
  <published>2021-01-01T00:00:00Z</published>
  <title>Click &lt;b&gt;here&lt;/b&gt; https://evil.example/x now</title>
  <author><name>A. Author</name></author>
 </entry>
</feed>"""
EMPTY = b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'


class FakeFetch:
    def __init__(self, *replies):
        self.replies, self.urls = list(replies), []

    def __call__(self, url, max_bytes):
        self.urls.append(url)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def client(*replies):
    fetch = FakeFetch(*replies)
    return ArxivClient(fetch=fetch, min_gap=0, sleep=lambda s: None), fetch


@pytest.mark.parametrize("text,kind,value", [
    ("1706.03762", "id", "1706.03762"),
    ("arXiv:1706.03762v7", "id", "1706.03762v7"),
    ("https://arxiv.org/abs/1706.03762", "id", "1706.03762"),
    ("https://arxiv.org/pdf/1706.03762v7.pdf", "id", "1706.03762v7"),
    ("hep-th/9901001", "id", "hep-th/9901001"),
    ("  Attention   Is All You Need ", "title", "Attention Is All You Need"),
])
def test_parse_query_accepts(text, kind, value):
    q = parse_query(text)
    assert (q.kind, q.value) == (kind, value)


@pytest.mark.parametrize("text", [
    "", "   ", "https://example.com/paper.pdf", "https://arxiv.org.evil.com/abs/1706.03762",
    "http://localhost:8501/abs/1706.03762", "ftp://arxiv.org/abs/1706.03762",
    "https://arxiv.org/list/cs.AI/recent", "x" * 400,
])
def test_parse_query_rejects(text):
    with pytest.raises(ArxivError):
        parse_query(text)


def test_id_pattern_is_strict():
    assert is_arxiv_id("1706.03762") and not is_arxiv_id("1706.03762/../../etc/passwd")
    assert not is_arxiv_id("../1706.03762") and not is_arxiv_id("1706.03762 ")


def test_parse_results_cleans_and_filters():
    found = parse_results(ATOM)
    assert [m.arxiv_id for m in found] == ["1706.03762v7", "2101.00001v1"]
    assert found[0].title == "Attention Is All You Need"
    assert found[0].authors == "Ashish Vaswani, Noam Shazeer, Niki Parmar and 1 more"
    assert found[0].year == "2017"
    assert "<" not in found[1].title and "http" not in found[1].title


def test_parse_results_refuses_entities_and_garbage():
    with pytest.raises(ArxivError):
        parse_results(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><feed>&a;</feed>')
    with pytest.raises(ArxivError):
        parse_results(b"not xml at all")


def test_find_by_id_uses_id_list_on_the_arxiv_host():
    c, fetch = client(ATOM)
    c.find("https://arxiv.org/abs/1706.03762")
    assert fetch.urls[0].startswith("https://export.arxiv.org/api/query?") and "id_list=1706.03762" in fetch.urls[0]


def test_title_search_falls_back_to_looser_search():
    c, fetch = client(EMPTY, ATOM)
    assert c.find("attention need")
    assert len(fetch.urls) == 2 and "ti%3A" in fetch.urls[0] and "all%3Aattention" in fetch.urls[1]


def test_download_builds_its_own_url_and_checks_pdf():
    c, fetch = client(b"%PDF-1.7 data")
    assert c.download("1706.03762v7").startswith(b"%PDF-")
    assert fetch.urls == ["https://arxiv.org/pdf/1706.03762v7"]
    with pytest.raises(ArxivError):
        c.download("https://evil.example/x")
    c2, _ = client(b"<html>not a pdf</html>")
    with pytest.raises(ArxivError):
        c2.download("1706.03762")


def test_network_errors_become_safe_messages():
    err404 = urllib.error.HTTPError("u", 404, "nf", {}, None)
    c, _ = client(err404)
    with pytest.raises(ArxivError, match="could not find"):
        c.download("1706.03762")
    c, _ = client(TimeoutError("secret internal detail"))
    with pytest.raises(ArxivError) as info:
        c.download("1706.03762")
    assert "secret" not in str(info.value)


def test_requests_are_spaced_out():
    now, slept = [100.0], []
    c = ArxivClient(fetch=FakeFetch(EMPTY, EMPTY), min_gap=3.0, clock=lambda: now[0], sleep=slept.append)
    c.find("1706.03762")
    now[0] += 1.0
    c.find("1706.03762")
    assert slept and 1.9 < slept[0] < 2.1

