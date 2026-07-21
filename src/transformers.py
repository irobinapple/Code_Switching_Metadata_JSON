"""Pure transformations from parsed segments to output DataFrames.

Milestone 2 builds the rawmetadata DataFrame (34 columns, exact order). The
metadata DataFrame is added in Milestone 3.
"""

from __future__ import annotations

import pandas as pd

from .constants import (
    DEFAULT_LOUDNESS_LEVEL,
    DEFAULT_PRIMARY_TYPE,
    METADATA_COLUMNS,
    METADATA_TYPE_TRANSLITERATION,
    RAWMETADATA_COLUMNS,
)
from .models import ConversationConfig, SpeakerMapping, TranscriptSegment


def segment_id(index: int) -> str:
    """Zero-padded segment id (minimum width 3): 1 -> 'seg001'."""
    return f"seg{index:03d}"


def build_rawmetadata(
    segments: list[TranscriptSegment],
    config: ConversationConfig,
    speaker_map: dict[str, SpeakerMapping],
) -> pd.DataFrame:
    """Build the rawmetadata DataFrame — one row per segment, 34 columns.

    `speaker_map` maps each source transcript label to its SpeakerMapping.
    Start/End times retain the source timestamp text (not parsed numbers).
    """
    speaker_languages = (
        f"{config.primary_language_code}, {config.secondary_language_code}"
    )
    segment_languages = speaker_languages
    is_translit = config.metadata_type == METADATA_TYPE_TRANSLITERATION

    rows: list[dict[str, object]] = []
    for i, seg in enumerate(segments, start=1):
        mapping = speaker_map[seg.speaker_label]
        rows.append(
            {
                "ConvID": config.conv_id,
                "LangPair": config.lang_pair,
                "Primary_Language_Code": config.primary_language_code,
                "Secondary_Language_Code": config.secondary_language_code,
                "Domain": config.domain,
                "Sampling_Rate": config.sampling_rate,
                "Recording_Date": config.recording_date,
                "Conversation_Script_Path": config.conversation_script_path,
                "Audio_File_Path": config.audio_file_path,
                "Master_Convention_Name": config.master_convention_name,
                "Custom_Addendum": config.custom_addendum,
                "Annotator_ID": config.annotator_id,
                "CS_Ratio_Primary": config.cs_ratio_primary,
                "CS_Ratio_Secondary": config.cs_ratio_secondary,
                "Speaker_ID": mapping.speaker_id,
                "Speaker_Role": mapping.role,
                "Speaker_Role_Source": mapping.role_source,
                "Speaker_Gender": mapping.gender,
                "Speaker_Gender_Source": mapping.gender_source,
                "Speaker_Age_Bucket": mapping.age_bucket,
                "Speaker_Nativity": mapping.nativity,
                "Speaker_Nativity_Source": mapping.nativity_source,
                "Speaker_Languages": speaker_languages,
                "Turn_No": i,
                "Segment_ID": segment_id(i),
                "Start_Time_Sec": seg.start_text,
                "End_Time_Sec": seg.end_text,
                "Primary_Type": DEFAULT_PRIMARY_TYPE,
                "Loudness_Level": DEFAULT_LOUDNESS_LEVEL,
                "Segment_Primary_Language": config.primary_language_code,
                "Segment_Languages": segment_languages,
                "Content_Text": seg.content_text,
                "Transliteration_Text": "",
                "QC_Notes": "",
            }
        )

    frame = pd.DataFrame(rows, columns=RAWMETADATA_COLUMNS)
    # Keep timestamp columns as strings so nothing coerces them to numbers.
    for col in ("Start_Time_Sec", "End_Time_Sec"):
        frame[col] = frame[col].astype(str)
    _ = is_translit  # Transliteration_Text stays blank; editable in the UI.
    return frame


def build_filename_stem(config: ConversationConfig) -> str:
    """`<LangPair>_<Domain>_<Sampling_Rate>_<ConvID>` — real delivery form."""
    return (
        f"{config.lang_pair}_{config.domain}_"
        f"{config.sampling_rate}_{config.conv_id}"
    )


def conversation_duration_sec(segments: list[TranscriptSegment]) -> float:
    """max(parsed end) - min(parsed start) across the whole conversation."""
    if not segments:
        return 0.0
    latest = max(seg.end_sec for seg in segments)
    earliest = min(seg.start_sec for seg in segments)
    return round(latest - earliest, 2)


def build_metadata(
    segments: list[TranscriptSegment],
    config: ConversationConfig,
    speaker_map: dict[str, SpeakerMapping],
) -> pd.DataFrame:
    """Build the metadata DataFrame — one row per unique speaker, 21 columns.

    Duration is conversation-level (identical on every speaker row); turn count
    is per-speaker only.
    """
    file_stem = build_filename_stem(config)
    duration = conversation_duration_sec(segments)

    # Per-speaker turn counts keyed by output Speaker_ID.
    turn_counts: dict[str, int] = {}
    speaker_order: list[str] = []
    for seg in segments:
        mapping = speaker_map[seg.speaker_label]
        speaker_id = mapping.speaker_id
        if speaker_id not in turn_counts:
            turn_counts[speaker_id] = 0
            speaker_order.append(seg.speaker_label)
        turn_counts[speaker_id] += 1

    rows: list[dict[str, object]] = []
    for sno, label in enumerate(speaker_order, start=1):
        mapping = speaker_map[label]
        rows.append(
            {
                "SNo": sno,
                "FileName": file_stem,
                "ConvID": config.conv_id,
                "LangPair": config.lang_pair,
                "Speaker_ID": mapping.speaker_id,
                "Speaker_Role": mapping.role,
                "Speaker_Role_Source": mapping.role_source,
                "Speaker_Gender": mapping.gender,
                "Speaker_Gender_Source": mapping.gender_source,
                "Speaker_Age_Bucket": mapping.age_bucket,
                "Speaker_Nativity": mapping.nativity,
                "Speaker_Nativity_Source": mapping.nativity_source,
                "Domain": config.domain,
                "Duration_Sec": duration,
                "Number_of_Turns": turn_counts[mapping.speaker_id],
                "Sampling_Rate": config.sampling_rate,
                "CS_Ratio_Primary": config.cs_ratio_primary,
                "CS_Ratio_Secondary": config.cs_ratio_secondary,
                "Recording_Date": config.recording_date,
                "Conversation_Script_Path": config.conversation_script_path,
                "Audio_File_Path": config.audio_file_path,
            }
        )

    frame = pd.DataFrame(rows, columns=METADATA_COLUMNS)
    # Force numeric duration so no exporter coerces it to an Excel time.
    frame["Duration_Sec"] = pd.to_numeric(frame["Duration_Sec"])
    frame["Number_of_Turns"] = pd.to_numeric(frame["Number_of_Turns"])
    return frame
