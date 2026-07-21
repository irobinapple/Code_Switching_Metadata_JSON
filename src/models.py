"""Dataclasses and the language-configuration loader.

Language data is the sole source of truth for dropdown values and derived
codes; nothing in the app hardcodes language names or codes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .constants import LANGUAGES_JSON


@dataclass(frozen=True)
class LanguageRecord:
    """A single language configuration entry from config/languages.json."""

    display_name: str
    language_code: str
    metadata_type: str
    primary_language_code: str
    secondary_language_code: str

    @property
    def lang_pair(self) -> str:
        """LangPair as `<language_code>_<secondary_language_code>`."""
        return f"{self.language_code}_{self.secondary_language_code}"


def load_language_records(path: Path | None = None) -> list[LanguageRecord]:
    """Load and validate language records from the JSON config file."""
    source = path if path is not None else LANGUAGES_JSON
    raw = json.loads(source.read_text(encoding="utf-8"))
    records = [
        LanguageRecord(
            display_name=item["display_name"],
            language_code=item["language_code"],
            metadata_type=item["metadata_type"],
            primary_language_code=item["primary_language_code"],
            secondary_language_code=item["secondary_language_code"],
        )
        for item in raw
    ]
    return records


def language_by_display_name(
    records: list[LanguageRecord], display_name: str
) -> LanguageRecord | None:
    """Return the record matching a display name, or None."""
    for record in records:
        if record.display_name == display_name:
            return record
    return None


def language_by_locale(
    records: list[LanguageRecord], locale: str
) -> LanguageRecord | None:
    """Return the record matching a `language_code` locale (e.g. `vi-VN`)."""
    for record in records:
        if record.language_code.lower() == locale.lower():
            return record
    return None


@dataclass
class ParsedFilename:
    """Tokens detected from an uploaded transcript filename."""

    conv_id: str | None = None
    locale: str | None = None
    domain: str | None = None
    sampling_rate: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class TranscriptSegment:
    """One parsed transcript turn."""

    speaker_label: str
    start_text: str
    end_text: str
    start_sec: float
    end_sec: float
    content_text: str
