"""Validation engine.

Milestone 2 implements rawmetadata-scoped checks. The full metadata + JSON
quality-gate suite is layered on in Milestone 3. Results separate blocking
errors (which disable downloads) from non-blocking warnings.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field

import pandas as pd

from .constants import (
    DOMAIN_CODES,
    METADATA_COLUMNS,
    METADATA_TYPE_TRANSLITERATION,
    NO_SPEAKER_ROLE,
    RAWMETADATA_COLUMNS,
    SAMPLING_RATES,
)
from .models import ConversationConfig, SpeakerMapping, TranscriptSegment
from .transformers import conversation_duration_sec

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


# --- Full quality-gate suite (rawmetadata + metadata + JSON) ---------------


def run_full_validation(
    raw_frame: pd.DataFrame,
    meta_frame: pd.DataFrame,
    json_obj: dict,
    json_bytes: bytes,
    config: ConversationConfig,
    speaker_map: dict[str, SpeakerMapping],
    segments: list[TranscriptSegment],
) -> ValidationResult:
    """Run the entire quality-gate suite and mandatory automated checks."""
    result = validate_rawmetadata(raw_frame, config, speaker_map, segments)
    _check_turn_no_sequential(result, raw_frame)
    _check_numeric_times(result, segments)
    validate_metadata(result, meta_frame, raw_frame, segments)
    validate_json(
        result, json_obj, json_bytes, raw_frame, segments, config.metadata_type
    )
    return result


def _check_turn_no_sequential(
    result: ValidationResult, raw_frame: pd.DataFrame
) -> None:
    turns = raw_frame["Turn_No"].tolist()
    if turns != list(range(1, len(turns) + 1)):
        result.error("Turn_No is not sequential starting at 1.")


def _check_numeric_times(
    result: ValidationResult, segments: list[TranscriptSegment]
) -> None:
    for i, seg in enumerate(segments, start=1):
        if not (
            math.isfinite(seg.start_sec) and math.isfinite(seg.end_sec)
        ):
            result.error(f"Segment {i} has an invalid numeric start/end time.")


def validate_metadata(
    result: ValidationResult,
    meta_frame: pd.DataFrame,
    raw_frame: pd.DataFrame,
    segments: list[TranscriptSegment],
) -> None:
    """Metadata column order, per-speaker turn counts, conversation duration."""
    if list(meta_frame.columns) != METADATA_COLUMNS:
        result.error(
            "metadata columns are missing or out of order. Expected the "
            f"{len(METADATA_COLUMNS)} defined columns in the exact order."
        )
        return

    # Per-speaker turn counts must match rawmetadata group counts.
    raw_counts = raw_frame.groupby("Speaker_ID").size().to_dict()
    for _, row in meta_frame.iterrows():
        speaker = row["Speaker_ID"]
        expected = raw_counts.get(speaker, 0)
        if int(row["Number_of_Turns"]) != int(expected):
            result.error(
                f"metadata Number_of_Turns for {speaker!r} "
                f"({row['Number_of_Turns']}) does not match the rawmetadata "
                f"count ({expected})."
            )

    # Duration must equal max end - min start for the conversation.
    expected_duration = conversation_duration_sec(segments)
    for value in meta_frame["Duration_Sec"].tolist():
        if round(float(value), 2) != expected_duration:
            result.error(
                f"metadata Duration_Sec ({value}) does not match the "
                f"conversation duration ({expected_duration})."
            )
            break

    if "QC_Notes" in meta_frame.columns or "QCNotes" in meta_frame.columns:
        result.error("QC_Notes must not appear in metadata.")


def _check_transliteration_presence(
    result: ValidationResult,
    json_segments: list[dict],
    metadata_type: str | None,
) -> None:
    """Transliteration key must be absent for Non-Transliteration languages.

    Transliteration-type languages keep the key on every segment.
    """
    if metadata_type is None:
        return
    is_translit = metadata_type == METADATA_TYPE_TRANSLITERATION
    for index, seg in enumerate(json_segments, start=1):
        present = "transliteration" in seg.get("transcriptionData", {})
        if is_translit and not present:
            result.error(
                f"Segment {index}: the transliteration key is missing, but "
                f"{metadata_type} files must include it."
            )
            return
        if not is_translit and present:
            result.error(
                f"Segment {index}: the transliteration key must be omitted "
                f"entirely for {metadata_type} files."
            )
            return


def validate_json(
    result: ValidationResult,
    json_obj: dict,
    json_bytes: bytes,
    raw_frame: pd.DataFrame,
    segments: list[TranscriptSegment],
    metadata_type: str | None = None,
) -> None:
    """JSON parseability, structure, ordering, and schema-literal checks."""
    # Re-parse to confirm serializability/round-trip.
    try:
        text = json_bytes.decode("utf-8")
    except UnicodeDecodeError:
        result.error("Generated JSON is not valid UTF-8.")
        return
    try:
        reloaded = json.loads(text)
    except json.JSONDecodeError as exc:
        result.error(f"Generated JSON cannot be re-parsed: {exc}")
        return

    # Transliteration key casing (client V1 uses lowercase).
    if '"Transliteration"' in text:
        result.error(
            "JSON uses capital 'Transliteration'; it must be lowercase "
            "'transliteration'."
        )

    # QC_Notes must never leak into JSON.
    if "QC_Notes" in text or "QCNotes" in text:
        result.error("QC_Notes must not appear in JSON.")

    value = reloaded.get("value", {})
    json_segments = value.get("segments", [])
    json_speakers = value.get("speakers", [])

    _check_transliteration_presence(result, json_segments, metadata_type)

    # Segment count equals rawmetadata row count.
    if len(json_segments) != len(raw_frame):
        result.error(
            f"JSON segment count ({len(json_segments)}) does not equal the "
            f"rawmetadata row count ({len(raw_frame)})."
        )

    # Speaker count equals unique speaker count for the conversation.
    unique_speakers = raw_frame["Speaker_ID"].nunique()
    if len(json_speakers) != unique_speakers:
        result.error(
            f"JSON speaker count ({len(json_speakers)}) does not equal the "
            f"unique speaker count ({unique_speakers})."
        )

    # Segments ascending by start.
    starts = [seg.get("start") for seg in json_segments]
    if starts != sorted(starts):
        result.error("JSON segments are not sorted ascending by start.")

    # domainList must be an array with exactly one item.
    domain_list = value.get("domainInfo", {}).get("domainList")
    if not isinstance(domain_list, list):
        result.error("domainInfo.domainList must be a JSON array.")
    elif len(domain_list) != 1:
        result.error(
            f"domainInfo.domainList must contain exactly one item, "
            f"found {len(domain_list)}."
        )
