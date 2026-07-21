"""Detect ConvID, locale, domain, and sampling rate from a filename.

Primary strategy splits on underscores and matches known tokens. A looser
regex fallback handles a compact run-together form as best-effort only.
Undetected tokens are left blank with a non-blocking warning — never guessed.
"""

from __future__ import annotations

import re
from pathlib import Path

from .constants import DOMAIN_CODES
from .models import LanguageRecord, ParsedFilename

_CONV_RE = re.compile(r"(Conv\d+)", re.IGNORECASE)
_SAMPLING_RE = re.compile(r"(8|16|48)\s*k?hz", re.IGNORECASE)


def _normalize_sampling_rate(raw: str) -> str:
    """Canonicalize a detected sampling-rate token to `8kHz`/`16kHz`/`48kHz`."""
    digits = re.sub(r"\D", "", raw)
    return f"{digits}kHz"


def parse_filename(
    filename: str, language_records: list[LanguageRecord]
) -> ParsedFilename:
    """Parse a transcript filename into detected tokens with warnings."""
    stem = Path(filename).stem
    result = ParsedFilename()

    # ConvID — regex, preserved exactly, variable digit width.
    conv_match = _CONV_RE.search(stem)
    if conv_match:
        result.conv_id = conv_match.group(1)
    else:
        result.warnings.append(
            "No ConvID (Conv followed by digits) found in the filename. "
            "Enter it manually."
        )

    # Locale — match a known language_code from config.
    result.locale = _detect_locale(stem, language_records)
    if result.locale is None:
        result.warnings.append(
            "No known language locale detected in the filename. "
            "Select the language manually."
        )

    # Domain — match an allowed domain code token.
    result.domain = _detect_domain(stem)
    if result.domain is None:
        result.warnings.append(
            "No filename domain token was detected. Choose a Domain manually."
        )

    # SamplingRate — case-insensitive, accepts `Khz`.
    sampling_match = _SAMPLING_RE.search(stem)
    if sampling_match:
        result.sampling_rate = _normalize_sampling_rate(sampling_match.group(0))
    else:
        result.warnings.append(
            "No sampling-rate token was detected. Choose a Sampling Rate manually."
        )

    return result


def _detect_locale(
    stem: str, language_records: list[LanguageRecord]
) -> str | None:
    """Find a known `language_code` (e.g. `vi-VN`) anywhere in the stem."""
    lowered = stem.lower()
    # Longest first so `zh-HK` is not shadowed by a shorter partial match.
    for record in sorted(
        language_records, key=lambda r: len(r.language_code), reverse=True
    ):
        if record.language_code.lower() in lowered:
            return record.language_code
    return None


def _detect_domain(stem: str) -> str | None:
    """Find an allowed domain code as a token (underscore or run-together)."""
    upper = stem.upper()
    tokens = re.split(r"[_\-]", upper)
    # Prefer an exact underscore/hyphen-delimited token match.
    for token in tokens:
        if token in DOMAIN_CODES:
            return token
    # Fallback: run-together form — match longest domain code as a substring.
    for code in sorted(DOMAIN_CODES, key=len, reverse=True):
        if code in upper:
            return code
    return None
