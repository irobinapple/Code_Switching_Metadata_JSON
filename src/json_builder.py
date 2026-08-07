"""Build the per-conversation JSON object matching the client's schema.

Key schema points enforced here (client V1 structure):
- `domainInfo.domainList` is an array containing exactly one object
- the `transliteration` key (lowercase) is omitted entirely for
  `Non-Transliteration` languages, and present for `Transliteration` ones
- segments are sorted ascending by numeric `start`
- `value.languages` carries only the primary code
- `speakerDominantVarieties` is an array with one object for the primary code
- a speaker's `languages` is `[primary, secondary]`, or `[]` for a No-Speaker
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
    METADATA_TYPE_TRANSLITERATION,
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

    # Only Transliteration-type languages carry the transliteration key at
    # all; for Non-Transliteration it is omitted entirely, per client feedback.
    include_transliteration = (
        config.metadata_type == METADATA_TYPE_TRANSLITERATION
    )
    segment_objects = _build_segments(
        segments, speaker_map, primary, secondary, include_transliteration
    )
    speaker_objects = _build_speakers(
        segments, speaker_map, primary, secondary
    )

    # Key order below mirrors the client's V1 file exactly (values are ours).
    return {
        "type": {"name": JSON_TYPE_NAME, "version": JSON_TYPE_VERSION},
        "value": {
            "languages": [primary],
            "languageInfo": {
                "spokenLanguages": [primary, secondary],
                "speakerDominantVarieties": [
                    {
                        "languageLocale": primary,
                        "languageVariety": [],
                        "otherLanguageInfluence": [],
                    }
                ],
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
            "conventionInfo": {
                "masterConventionName": config.master_convention_name,
                "customAddendum": config.custom_addendum,
            },
            "annotatorInfo": {
                "loginEncrypted": JSON_LOGIN_ENCRYPTED,
                "annotatorId": config.annotator_id,
            },
            "speakers": speaker_objects,
            "segments": segment_objects,
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
        },
    }


def _build_segments(
    segments: list[TranscriptSegment],
    speaker_map: dict[str, SpeakerMapping],
    primary: str,
    secondary: str,
    include_transliteration: bool,
) -> list[dict]:
    objects: list[dict] = []
    for i, seg in enumerate(segments, start=1):
        mapping = speaker_map[seg.speaker_label]
        transcription_data: dict[str, object] = {"content": seg.content_text}
        if include_transliteration:
            transcription_data["transliteration"] = _transliteration_value("")
        objects.append(
            {
                "start": seg.start_sec,
                "end": seg.end_sec,
                "primaryType": DEFAULT_PRIMARY_TYPE,
                "loudnessLevel": DEFAULT_LOUDNESS_LEVEL,
                "language": primary,
                "segmentLanguages": [primary, secondary],
                "transcriptionData": transcription_data,
                "segmentId": segment_id(i),
                "speakerId": mapping.speaker_id,
            }
        )
    objects.sort(key=lambda obj: obj["start"])
    return objects


def _build_speakers(
    segments: list[TranscriptSegment],
    speaker_map: dict[str, SpeakerMapping],
    primary: str,
    secondary: str,
) -> list[dict]:
    seen: list[str] = []
    objects: list[dict] = []
    for seg in segments:
        mapping = speaker_map[seg.speaker_label]
        if mapping.speaker_id in seen:
            continue
        seen.append(mapping.speaker_id)
        is_no_speaker = mapping.role == NO_SPEAKER_ROLE
        if is_no_speaker:
            # A No-Speaker (hold music / noise) has no gender/age/nativity
            # and no spoken languages, per the client schema.
            gender, age, nativity = "NA", "NA", "NA"
            languages: list[str] = []
            role_source = ANNOTATOR_SOURCE
        else:
            gender = mapping.gender
            age = mapping.age_bucket
            nativity = mapping.nativity
            languages = [primary, secondary]
            role_source = ""
        objects.append(
            {
                "speakerId": mapping.speaker_id,
                "gender": gender,
                "speaker_age": age,
                "genderSource": ANNOTATOR_SOURCE,
                "speakerNativity": nativity,
                "speakerNativitySource": ANNOTATOR_SOURCE,
                "speakerRole": mapping.role,
                "speakerRoleSource": role_source,
                "languages": languages,
            }
        )
    # No-Speaker(s) listed first, matching the client sample; real speakers
    # keep their first-appearance order (stable partition).
    no_speakers = [o for o in objects if o["speakerRole"] == NO_SPEAKER_ROLE]
    others = [o for o in objects if o["speakerRole"] != NO_SPEAKER_ROLE]
    return no_speakers + others


def json_filename(config: ConversationConfig) -> str:
    """`<LangPair>_<Domain>_<Sampling_Rate>_<ConvID>.json`."""
    return f"{build_filename_stem(config)}.json"


def json_to_bytes(obj: dict) -> bytes:
    """Serialize with ensure_ascii=False, indent=2, UTF-8."""
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    return text.encode("utf-8")
