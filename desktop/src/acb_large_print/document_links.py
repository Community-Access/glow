"""Recognize web and email addresses without mistaking document names for URLs."""

from __future__ import annotations

import re
from collections.abc import Iterator


_ADDRESS = re.compile(
    r"(?<![\w@/\\.-])(?:"
    r"https?://[^\s<>\"`]+|"
    r"mailto:[^\s<>\"`]+|"
    r"[\w.+-]+@(?:[\w-]+\.)+[a-z]{2,}(?:\?[^\s<>\"`]*)?|"
    r"(?:[\w-]+\.)+(?:com|org|net|edu|gov|app|dev|ai|io)"
    r"(?![\w-]|\.[\w-])(?:/[^\s<>\"`]*)?"
    r")",
    re.IGNORECASE,
)


def address_parts(text: str) -> Iterator[tuple[str, str]]:
    """Yield unchanged text and its optional absolute hyperlink target.

    Only recognized web suffixes are linked without a scheme. Trailing
    sentence punctuation and unmatched closing brackets are not part of a URL.
    """
    start = 0
    for match in _ADDRESS.finditer(text):
        address = match.group().rstrip(".,;:!?")
        for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
            while address.endswith(closing) and address.count(closing) > address.count(opening):
                address = address[:-1]
        if match.start() > start:
            yield text[start:match.start()], ""
        if address.lower().startswith(("http://", "https://", "mailto:")):
            target = address
        elif "@" in address.split("/", 1)[0]:
            target = "mailto:" + address
        else:
            target = "https://" + address
        yield address, target
        start = match.start() + len(address)
    if start < len(text):
        yield text[start:], ""
