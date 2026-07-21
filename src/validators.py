"""Validation engine.

Milestone 2 implements rawmetadata-scoped checks. The full metadata + JSON
quality-gate suite is layered on in Milestone 3. Results separate blocking
errors (which disable downloads) from non-blocking warnings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from .constants import (
    DOMAIN_CODES,
    NO_SPEAKER_ROLE,
    RAWMETADATA_COLUMNS,
    SAMPLING_RATES,
)
from .models import ConversationConfig, SpeakerMapping, TranscriptSegment

_SPK_STYLE_RE = re.compile(r"^SPK\d+$", re.IGNORECASE)


@dataclass
class ValidationResult:
    """Collected validation issues, split by severity."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_blocking_errors(self) -> bool:
        return bool(self.errors)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def extend(self, other: "ValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def validate_rawmetadata(
    frame: pd.DataFrame,
    config: ConversationConfig,
    speaker_map: dict[str, SpeakerMapping],
    segments: list[TranscriptSegment],
) -> ValidationResult:
    """Run rawmetadata-scoped blocking and warning checks."""
    result = ValidationResult()

    _check_required_fields(result, config)
    _check_columns(result, frame)
    _check_segments_present(result, segments)
    _check_speaker_mappings(result, speaker_map)
    _check_segment_content(result, segments, frame)
    _check_times(result, segments)
    _check_segment_ids(result, frame)

    _warn_cs_ratio(result, config)
    _warn_speaker_style(result, speaker_map)
    _warn_overlaps_and_gaps(result, segments)
    _warn_no_speaker_content(result, segments, speaker_map)

    return result


# --- Blocking checks -------------------------------------------------------


def _check_required_fields(
    result: ValidationResult, config: ConversationConfig
) -> None:
    if not config.conv_id.strip():
        result.error("ConvID is blank. Enter a ConvID before generating.")
    if not config.primary_language_code.strip():
        result.error("No language is selected. Choose a language.")
    if not config.domain.strip():
        result.error("Domain is blank. Choose a Domain.")
    elif config.domain not in DOMAIN_CODES:
        result.error(
            f"Domain {config.domain!r} is not one of the allowed codes."
        )
    if not config.sampling_rate.strip():
        result.error("Sampling Rate is blank. Choose a Sampling Rate.")
    elif config.sampling_rate not in SAMPLING_RATES:
        result.warn(
            f"Sampling Rate {config.sampling_rate!r} is a custom value."
        )
    if not config.annotator_id.strip():
        result.error("Annotator ID is required. Enter an Annotator ID.")


def _check_columns(result: ValidationResult, frame: pd.DataFrame) -> None:
    actual = list(frame.columns)
    if actual != RAWMETADATA_COLUMNS:
        result.error(
            "rawmetadata columns are missing or out of order. Expected the "
            f"{len(RAWMETADATA_COLUMNS)} defined columns in the exact order."
        )


def _check_segments_present(
    result: ValidationResult, segments: list[TranscriptSegment]
) -> None:
    if not segments:
        result.error(
            "The transcript contains zero valid turns. Check the file format."
        )


def _check_speaker_mappings(
    result: ValidationResult, speaker_map: dict[str, SpeakerMapping]
) -> None:
    for label, mapping in speaker_map.items():
        if not mapping.speaker_id.strip():
            result.error(
                f"Speaker mapping for {label!r} is incomplete: "
                "Output SpeakerID is blank."
            )
        if not mapping.role.strip():
            result.error(
                f"Speaker mapping for {label!r} is incomplete: role is blank."
            )


def _check_segment_content(
    result: ValidationResult,
    segments: list[TranscriptSegment],
    frame: pd.DataFrame,
) -> None:
    for i, seg in enumerate(segments, start=1):
        if not seg.speaker_label.strip():
            result.error(f"Segment {i} has no speaker label.")
    if "Content_Text" in frame.columns:
        for idx, value in enumerate(frame["Content_Text"].tolist(), start=1):
            text = "" if value is None else str(value)
            mapping_role = str(frame["Speaker_Role"].iloc[idx - 1])
            if not text.strip() and mapping_role != NO_SPEAKER_ROLE:
                result.error(f"Segment {idx} has empty content.")
            elif text != text.strip():
                result.warn(
                    f"Segment {idx} content has leading/trailing whitespace."
                )


def _check_times(
    result: ValidationResult, segments: list[TranscriptSegment]
) -> None:
    for i, seg in enumerate(segments, start=1):
        if seg.start_sec >= seg.end_sec:
            result.error(
                f"Segment {i}: start time ({seg.start_text}) is not before "
                f"end time ({seg.end_text})."
            )


def _check_segment_ids(result: ValidationResult, frame: pd.DataFrame) -> None:
    if "Segment_ID" not in frame.columns:
        return
    ids = frame["Segment_ID"].tolist()
    if len(ids) != len(set(ids)):
        result.error("Duplicate Segment_ID values exist.")


# --- Warning checks --------------------------------------------------------


def _warn_cs_ratio(
    result: ValidationResult, config: ConversationConfig
) -> None:
    total = config.cs_ratio_primary + config.cs_ratio_secondary
    if round(total, 6) != 100:
        result.warn(
            f"CS ratios total {total:g}, not 100 "
            f"({config.cs_ratio_primary:g} + {config.cs_ratio_secondary:g})."
        )


def _warn_speaker_style(
    result: ValidationResult, speaker_map: dict[str, SpeakerMapping]
) -> None:
    for label in speaker_map:
        if not _SPK_STYLE_RE.match(label):
            result.warn(
                f"Source speaker label {label!r} is not in the expected "
                "'SPK...' style."
            )


def _warn_overlaps_and_gaps(
    result: ValidationResult, segments: list[TranscriptSegment]
) -> None:
    ordered = sorted(segments, key=lambda s: s.start_sec)
    for prev, curr in zip(ordered, ordered[1:]):
        if curr.start_sec < prev.end_sec:
            result.warn(
                f"Segments overlap: a turn starts at {curr.start_text} before "
                f"the previous turn ends at {prev.end_text}."
            )
        gap = curr.start_sec - prev.end_sec
        if gap > 60:
            result.warn(
                f"There is a gap larger than 60 seconds ({gap:g}s) before the "
                f"turn at {curr.start_text}."
            )


def _warn_no_speaker_content(
    result: ValidationResult,
    segments: list[TranscriptSegment],
    speaker_map: dict[str, SpeakerMapping],
) -> None:
    for i, seg in enumerate(segments, start=1):
        mapping = speaker_map.get(seg.speaker_label)
        if (
            mapping is not None
            and mapping.role == NO_SPEAKER_ROLE
            and seg.content_text.strip()
        ):
            result.warn(
                f"Segment {i} is marked No-Speaker but has speech content."
            )
