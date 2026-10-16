from datetime import datetime, timedelta, timezone
from services.news import NewsFeed, Headline, parse_feed

NOW = datetime(2026, 10, 16, 3, tzinfo=timezone.utc)


def test_feed_filters_unsafe_links_future_and_old_dates():
    def entry(link, date):
        return f'<item><title>AI update</title><link>{link}</link><pubDate>{date}</pubDate></item>'
    xml = '<rss><channel>' + ''.join([
        entry('https://openai.com/news/update', 'Thu, 15 Oct 2026 12:00:00 GMT'),
        entry('https://evil.example/news', 'Thu, 15 Oct 2026 12:00:00 GMT'),
        entry('https://openai.com/future', 'Thu, 15 Oct 2027 12:00:00 GMT'),
        entry('https://openai.com/old', 'Thu, 01 Jan 2026 12:00:00 GMT'),
    ]) + '</channel></rss>'
    parsed = parse_feed(xml.encode(), 'OpenAI', 'openai.com', NOW)
    assert [x.url for x in parsed] == ['https://openai.com/news/update']


def test_refresh_follows_pacific_day_and_recovers_from_outage():
    now = [NOW]
    calls, fail = [], [False]
    def fetch(spec, date):
        calls.append(spec)
        if fail[0]:
            raise OSError('offline')
        return [Headline('Latest update', f'https://{spec[2]}/update', spec[0], NOW-timedelta(hours=1))]
    feed = NewsFeed(fetch, clock=lambda: now[0])
    first = feed.latest()
    assert len(calls) == 2
    now[0] += timedelta(hours=1)
    assert feed.latest() is first
    assert len(calls) == 2
    now[0] += timedelta(hours=5)  # next Pacific day
    fail[0] = True
    old = feed.latest()
    assert old.stale and old.checked == NOW and old.items
    assert len(calls) == 4
    feed.latest()
    assert len(calls) == 4
    now[0] += timedelta(minutes=16)
    fail[0] = False
    assert not feed.latest().stale
    assert len(calls) == 6
