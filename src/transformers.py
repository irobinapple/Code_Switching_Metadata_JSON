"""Pure transformations from parsed segments to output DataFrames.

Milestone 2 builds the rawmetadata DataFrame (34 columns, exact order). The
metadata DataFrame is added in Milestone 3.
"""

from __future__ import annotations

import pandas as pd

from .constants import (
    DEFAULT_LOUDNESS_LEVEL,
    DEFAULT_PRIMARY_TYPE,
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
