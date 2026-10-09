"""The only place that talks to the model. Keys stay server-side.

Every API attempt is announced through hooks (so the limiter can count it and can refuse it
during a cooldown), every call has an explicit timeout, and when the free quota runs out we
back off briefly, then stop. There is no paid fallback by design.
"""
from __future__ import annotations

import json
import re
import time

from google import genai
from google.genai import errors, types

from services.errors import ModelError, QuotaExceeded  # re-exported for callers and tests

__all__ = ["GeminiClient", "ModelError", "QuotaExceeded", "parse_json"]


def parse_json(text: str | None) -> dict:
    if not text:
        raise ModelError("The model returned an empty answer.")
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ModelError("The model did not return valid JSON.") from None
    if not isinstance(data, dict):
        raise ModelError("The model did not return a JSON object.")
    return data


def _noop(*args, **kwargs):
    return None


class GeminiClient:
    def __init__(self, api_key: str, model: str, max_retries: int = 1, timeout_seconds: float = 60.0,
                 max_output_tokens: int = 6000, system_as_content: bool = False, sleep=time.sleep,
                 before_attempt=_noop, on_quota_error=_noop, on_success=_noop):
        self._client = genai.Client(api_key=api_key,
                                    http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)))
        self.model = model
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.system_as_content = system_as_content  # for models that reject system instructions
        self._sleep = sleep
        self._before_attempt = before_attempt  # called before EVERY api call; may raise QuotaExceeded
        self._on_quota_error = on_quota_error
        self._on_success = on_success

    def generate_json(self, system: str, user: str) -> dict:
        config = {"response_mime_type": "application/json", "temperature": 0.2,
                  "max_output_tokens": self.max_output_tokens}
        if self.system_as_content:
            contents = system + "\n\n" + user
        else:
            contents, config["system_instruction"] = user, system
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            self._before_attempt()  # counts this attempt; refuses it if we are cooling down or out of budget
            try:
                response = self._client.models.generate_content(
                    model=self.model, contents=contents, config=types.GenerateContentConfig(**config))
                data = parse_json(response.text)
                self._on_success()
                return data
            except ModelError:
                raise
            except errors.APIError as error:
                code = getattr(error, "code", None)
                if code in (429, 503) and attempt < self.max_retries:
                    self._sleep(delay)
                    delay *= 3
                    continue
                if code == 429:
                    self._on_quota_error()
                    raise QuotaExceeded("The free quota is used up for now.") from None
                raise ModelError(f"The model service returned an error ({code}).") from None
            except Exception as error:  # timeouts, network problems: never show internals
                name = type(error).__name__.lower()
                if "timeout" in name or "timedout" in name:
                    raise ModelError("The model took too long to answer. Please try again.") from None
                raise ModelError("The model service could not be reached.") from None
        raise ModelError("The model service did not respond.")
