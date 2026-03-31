from __future__ import annotations

import re


def clean_text(raw_text: str) -> str:
    """Normalize noisy OCR legal notice text while preserving semantics."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")

    # Remove obvious line-break hyphenation artifacts.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Normalize separator spacing and trailing spaces.
    text = re.sub(r"\s*[:：]\s*", ": ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)

    # Collapse repeated OCR symbols and excessive blank lines.
    text = re.sub(r"[•·]{2,}", " ", text)
    text = re.sub(r"[°º]{2,}", "°", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
