"""The 'AI topic of the week' card: one short item from content/ai_topic.json, edited by hand each week.

Nothing here touches the network or the model. A topic older than MAX_AGE_DAYS is hidden, so the card
never claims to be 'latest' when it is stale. A missing or broken file just hides the card.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

TOPIC_FILE = Path(__file__).resolve().parent.parent / "content" / "ai_topic.json"
MAX_AGE_DAYS = 14


@dataclass
class Topic:
    as_of: date
    title: str
    hook: str
    explain: str
    source_title: str
    source_url: str


def load_topic(today: date | None = None, path: Path = TOPIC_FILE) -> Topic | None:
    today = today or date.today()
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        as_of = date.fromisoformat(data["as_of"])
        fields = {k: data[k].strip() for k in ("title", "hook", "explain", "source_title", "source_url")}
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        return None
    if not all(fields.values()) or not fields["source_url"].startswith("https://"):
        return None
    if not 0 <= (today - as_of).days <= MAX_AGE_DAYS:
        return None
    return Topic(as_of=as_of, **fields)
