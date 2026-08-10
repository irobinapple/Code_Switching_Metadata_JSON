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
        """LangPair token as it appears in real filenames, e.g. `vi-VN_English`.

        Every configured language code-switches with English (the secondary is
        always `en_<REGION>`), so the pair partner is the literal `English`,
        matching every delivered filename (`vi-VN_English_AIR_48kHz_Conv0347`).
        """
        return f"{self.language_code}_English"


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
    # Blocking problems with the filename itself (e.g. an underscore inside
    # the language code). Upload cannot proceed until the file is renamed.
    errors: list[str] = field(default_factory=list)
    # The client-convention filename to rename to, when we can derive it.
    suggested_filename: str | None = None

    @property
    def is_blocked(self) -> bool:
        return bool(self.errors)


@dataclass
class TranscriptSegment:
    """One parsed transcript turn."""

    speaker_label: str
    start_text: str
    end_text: str
    start_sec: float
    end_sec: float
    content_text: str


@dataclass
class ConversationConfig:
    """Conversation-level values from the setup form (one per ConvID)."""

    conv_id: str
    lang_pair: str
    primary_language_code: str
    secondary_language_code: str
    metadata_type: str
    domain: str
    sampling_rate: str
    recording_date: str
    conversation_script_path: str
    audio_file_path: str
    master_convention_name: str
    custom_addendum: str
    annotator_id: str
    cs_ratio_primary: float
    cs_ratio_secondary: float


@dataclass
class SpeakerMapping:
    """Output values for one source speaker label from the mapping form."""

    transcript_label: str
    speaker_id: str
    role: str
    gender: str
    age_bucket: str
    nativity: str

    @property
    def role_source(self) -> str:
        """`Annotator` only when the role is `No-Speaker`, else empty."""
        from .constants import ANNOTATOR_SOURCE, NO_SPEAKER_ROLE

        return ANNOTATOR_SOURCE if self.role == NO_SPEAKER_ROLE else ""

    @property
    def gender_source(self) -> str:
        from .constants import ANNOTATOR_SOURCE

        return ANNOTATOR_SOURCE

    @property
    def nativity_source(self) -> str:
        from .constants import ANNOTATOR_SOURCE

        return ANNOTATOR_SOURCE
