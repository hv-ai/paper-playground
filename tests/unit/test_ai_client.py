import pytest
from google.genai import errors

from services.ai_client import GeminiClient, ModelError, QuotaExceeded, parse_json


def test_parse_json_variants():
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    for bad in (None, "", "not json", "[1, 2]"):
        with pytest.raises(ModelError):
            parse_json(bad)


class Models:
    def __init__(self, behaviours):
        self.behaviours, self.calls = list(behaviours), 0

    def generate_content(self, **kwargs):
        self.calls += 1
        item = self.behaviours.pop(0)
        if isinstance(item, Exception):
            raise item
        return type("R", (), {"text": item})()


def make_client(behaviours, **hooks):
    client = GeminiClient(api_key="test-key", model="m", sleep=lambda s: None, **hooks)
    models = Models(behaviours)
    client._client = type("C", (), {"models": models})()
    return client, models


E429 = errors.ClientError(429, {"error": {"message": "slow down"}})


def test_retries_rate_limit_once_then_succeeds():
    client, models = make_client([E429, '{"ok": true}'])
    assert client.generate_json("s", "u") == {"ok": True}
    assert models.calls == 2


def test_stops_after_one_retry_with_quota_exceeded():
    client, models = make_client([E429, E429, E429])
    with pytest.raises(QuotaExceeded):
        client.generate_json("s", "u")
    assert models.calls == 2  # first try + one retry, then stop (no paid fallback)


def test_every_attempt_is_announced_and_the_outcome_reported():
    log = []
    client, _ = make_client([E429, E429], before_attempt=lambda: log.append("attempt"),
                            on_quota_error=lambda: log.append("quota"), on_success=lambda: log.append("ok"))
    with pytest.raises(QuotaExceeded):
        client.generate_json("s", "u")
    assert log == ["attempt", "attempt", "quota"]
    log.clear()
    client, _ = make_client(['{"a": 1}'], before_attempt=lambda: log.append("attempt"), on_success=lambda: log.append("ok"))
    client.generate_json("s", "u")
    assert log == ["attempt", "ok"]


def test_a_refusing_hook_stops_the_call_before_it_reaches_the_api():
    def refuse():
        raise QuotaExceeded("paused")
    client, models = make_client(['{"a": 1}'], before_attempt=refuse)
    with pytest.raises(QuotaExceeded):
        client.generate_json("s", "u")
    assert models.calls == 0


def test_other_errors_become_safe_messages():
    err = errors.ClientError(400, {"error": {"message": "secret internal detail"}})
    client, _ = make_client([err])
    with pytest.raises(ModelError) as info:
        client.generate_json("s", "u")
    assert "secret internal detail" not in str(info.value)


def test_timeouts_and_network_errors_become_safe_messages():
    class ReadTimeout(Exception):
        pass
    client, _ = make_client([ReadTimeout("socket details here")])
    with pytest.raises(ModelError) as info:
        client.generate_json("s", "u")
    assert "too long" in str(info.value) and "socket" not in str(info.value)
    client, _ = make_client([RuntimeError("dns secret")])
    with pytest.raises(ModelError) as info:
        client.generate_json("s", "u")
    assert "dns secret" not in str(info.value)


def test_an_explicit_timeout_is_configured():
    client = GeminiClient(api_key="k", model="m", timeout_seconds=42)
    assert client.timeout_seconds == 42
