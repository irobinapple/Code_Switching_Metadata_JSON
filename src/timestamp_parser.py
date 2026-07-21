"""Pure timestamp parsing to elapsed seconds.

Primary case is the SRT comma-decimal form `HH:MM:SS,mmm`. Also handles dot
decimals, `M:SS`/`MM:SS` forms, plain seconds, and — defensively — a
six-digit no-colon `HHMMSS` form.
"""

from __future__ import annotations


class TimestampError(ValueError):
    """Raised when a timestamp string cannot be parsed."""


def parse_timestamp_to_seconds(value: str) -> float:
    """Convert a timestamp string to elapsed seconds.

    Accepts (comma or dot decimal separator):
    - `HH:MM:SS,mmm` / `HH:MM:SS.mmm` (SRT form — primary case)
    - `M:SS.mmm` / `MM:SS.mmm`
    - plain seconds like `83.5`
    - a six-digit no-colon `HHMMSS[,.]mmm` form (best-effort fallback)

    Raises TimestampError on genuinely invalid input.
    """
    if value is None:
        raise TimestampError("Timestamp is empty.")

    text = value.strip().replace(",", ".")
    if not text:
        raise TimestampError("Timestamp is empty.")

    if ":" in text:
        return _parse_colon_form(text, original=value)
    return _parse_no_colon_form(text, original=value)


def _parse_colon_form(text: str, original: str) -> float:
    parts = text.split(":")
    if len(parts) not in (2, 3):
        raise TimestampError(f"Unrecognized timestamp format: {original!r}")

    try:
        if len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
        else:
            hours = 0
            minutes, seconds = int(parts[0]), float(parts[1])
    except ValueError as exc:
        raise TimestampError(f"Unrecognized timestamp format: {original!r}") from exc

    if minutes < 0 or minutes >= 60 or seconds < 0 or seconds >= 60 or hours < 0:
        raise TimestampError(f"Timestamp component out of range: {original!r}")

    return hours * 3600 + minutes * 60 + seconds


def _parse_no_colon_form(text: str, original: str) -> float:
    if "." in text:
        whole, _, frac = text.partition(".")
    else:
        whole, frac = text, ""

    if not whole.isdigit():
        raise TimestampError(f"Unrecognized timestamp format: {original!r}")

    # Defensive six-digit HHMMSS form (no colon), e.g. "000123,500".
    if len(whole) == 6:
        hours = int(whole[0:2])
        minutes = int(whole[2:4])
        seconds = int(whole[4:6])
        if minutes >= 60 or seconds >= 60:
            raise TimestampError(f"Timestamp component out of range: {original!r}")
        total = hours * 3600 + minutes * 60 + seconds
        if frac:
            total += float(f"0.{frac}")
        return float(total)

    # Otherwise plain seconds.
    try:
        return float(text)
    except ValueError as exc:
        raise TimestampError(f"Unrecognized timestamp format: {original!r}") from exc
