"""Make model- or paper-written text safe to show.

Rule: nothing the model or the paper wrote is ever rendered as HTML, a link or
LaTeX. We escape markdown so it shows up as plain words.
"""
from __future__ import annotations

import re

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-!|<>~$&])")


def md_safe(text: object) -> str:
    """Escape markdown so text is displayed literally (no links, images, math, HTML)."""
    return _MD_SPECIAL.sub(r"\\\1", str(text))
