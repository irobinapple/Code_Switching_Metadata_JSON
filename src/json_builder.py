"""Build the per-conversation JSON object matching the client's schema.

Key schema points enforced here:
- `domainInfo.domainList` is an array containing exactly one object
- the transliteration key is `Transliteration` (capital T), `null` when blank
- segments are sorted ascending by numeric `start`
- `languages` / `speakerDominantVarieties` carry only the primary code
"""

from __future__ import annotations

import json

from .constants import (
    ANNOTATOR_SOURCE,
    DEFAULT_LOUDNESS_LEVEL,
    DEFAULT_PRIMARY_TYPE,
    JSON_DOMAIN_LITERAL,
    JSON_DOMAIN_VERSION,
    JSON_LOGIN_ENCRYPTED,
    JSON_TYPE_NAME,
    JSON_TYPE_VERSION,
    NO_SPEAKER_ROLE,
)
from .models import ConversationConfig, SpeakerMapping, TranscriptSegment
from .transformers import build_filename_stem, segment_id


def _normalize_code(code: str) -> str:
    """Convert any stray hyphen to an underscore in a language code."""
    return code.replace("-", "_")


def _transliteration_value(text: str) -> str | None:
    """Blank transliteration becomes JSON null, not an empty string."""
    stripped = (text or "").strip()
    return stripped if stripped else None


def build_conversation_json(
    segments: list[TranscriptSegment],
    config: ConversationConfig,
    speaker_map: dict[str, SpeakerMapping],
) -> dict:
    """Assemble the full JSON object for one conversation."""
    primary = _normalize_code(config.primary_language_code)
    secondary = _normalize_code(config.secondary_language_code)

    segment_objects = _build_segments(segments, speaker_map, primary, secondary)
    speaker_objects = _build_speakers(segments, speaker_map, primary)

    return {
        "type": {"name": JSON_TYPE_NAME, "version": JSON_TYPE_VERSION},
        "value": {
            "conventionInfo": {
                "masterConventionName": config.master_convention_name,
                "customAddendum": config.custom_addendum,
            },
            "annotatorInfo": {
                "loginEncrypted": JSON_LOGIN_ENCRYPTED,
                "annotatorId": config.annotator_id,
            },
            "taskStatus": {
                "segmentation": {
                    "workflowStatus": "COMPLETE",
                    "workflowType": "LABEL",
                },
                "speakerId": {
                    "workflowStatus": "COMPLETE",
                    "workflowType": "LABEL",
                },
                "transcription": {
                    "workflowStatus": "COMPLETE",
                    "workflowType": "LABEL",
                },
            },
            "segments": segment_objects,
            "speakers": speaker_objects,
            "languages": [primary],
            "languageInfo": {
                "spokenLanguages": [primary, secondary],
                "speakerDominantVarieties": [primary],
            },
            "domainInfo": {
                "domainVersion": JSON_DOMAIN_VERSION,
                "domainList": [
                    {
                        "domain": JSON_DOMAIN_LITERAL,
                        "topicList": [config.domain],
                    }
                ],
            },
        },
    }


def _build_segments(
    segments: list[TranscriptSegment],
    speaker_map: dict[str, SpeakerMapping],
    primary: str,
    secondary: str,
) -> list[dict]:
    objects: list[dict] = []
    for i, seg in enumerate(segments, start=1):
        mapping = speaker_map[seg.speaker_label]
        objects.append(
            {
                "start": seg.start_sec,
                "end": seg.end_sec,
                "segmentId": segment_id(i),
                "primaryType": DEFAULT_PRIMARY_TYPE,
                "loudnessLevel": DEFAULT_LOUDNESS_LEVEL,
                "language": primary,
                "segmentLanguages": [primary, secondary],
                "speakerId": mapping.speaker_id,
                "transcriptionData": {
                    "content": seg.content_text,
                    "Transliteration": _transliteration_value(""),
                },
            }
        )
    objects.sort(key=lambda obj: obj["start"])
    return objects


def _build_speakers(
    segments: list[TranscriptSegment],
    speaker_map: dict[str, SpeakerMapping],
    primary: str,
) -> list[dict]:
    seen: list[str] = []
    objects: list[dict] = []
    for seg in segments:
        mapping = speaker_map[seg.speaker_label]
        if mapping.speaker_id in seen:
            continue
        seen.append(mapping.speaker_id)
        role_source = (
            ANNOTATOR_SOURCE if mapping.role == NO_SPEAKER_ROLE else ""
        )
        objects.append(
            {
                "speakerId": mapping.speaker_id,
                "speaker_age": mapping.age_bucket,
                "gender": mapping.gender,
                "genderSource": ANNOTATOR_SOURCE,
                "speakerRole": mapping.role,
                "speakerRoleSource": role_source,
                "speakerNativity": mapping.nativity,
                "speakerNativitySource": ANNOTATOR_SOURCE,
                "languages": [primary],
            }
        )
    return objects


def json_filename(config: ConversationConfig) -> str:
    """`<LangPair>_<Domain>_<Sampling_Rate>_<ConvID>.json`."""
    return f"{build_filename_stem(config)}.json"


def json_to_bytes(obj: dict) -> bytes:
    """Serialize with ensure_ascii=False, indent=2, UTF-8."""
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    return text.encode("utf-8")
