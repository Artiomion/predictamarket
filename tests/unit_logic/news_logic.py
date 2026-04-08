"""Extracted news business logic."""

import re
from html import unescape as html_unescape

_HTML_TAG_RE = re.compile(r"<[^>]+>")
AMBIGUOUS_TICKERS = {"DE", "GE", "MS", "GL", "DD", "GS", "FIX", "LOW", "HAS", "ALL", "IT", "A"}


def strip_html(text: str) -> str:
    return html_unescape(_HTML_TAG_RE.sub("", text)).strip()
