"""Errors shared by the model client and the usage limiter. Messages are safe to show visitors."""


class QuotaExceeded(Exception):
    """The free-tier quota is used up, or generation is paused to protect it."""


class ModelError(Exception):
    """The model call failed or returned something unusable."""
