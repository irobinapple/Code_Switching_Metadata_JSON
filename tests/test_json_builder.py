"""Tests for the JSON builder and JSON quality gates."""

from __future__ import annotations

import dataclasses
import json

from src.json_builder import (
    build_conversation_json,
    json_filename,
    json_to_bytes,
)


def _build(segments, config, speaker_map):
    return build_conversation_json(segments, config, speaker_map)


class TestKeyOrderMatchesClient:
    """Lock the exact key order to the client's V1 layout."""

    def test_value_key_order(self, vi_en_segments, vi_config, vi_speaker_map):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        assert list(obj["value"].keys()) == [
            "languages",
            "languageInfo",
            "domainInfo",
            "conventionInfo",
            "annotatorInfo",
            "speakers",
            "segments",
            "taskStatus",
        ]

    def test_segment_key_order(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        assert list(obj["value"]["segments"][0].keys()) == [
            "start",
            "end",
            "primaryType",
            "loudnessLevel",
            "language",
            "segmentLanguages",
            "transcriptionData",
            "segmentId",
            "speakerId",
        ]

    def test_speaker_key_order(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        assert list(obj["value"]["speakers"][0].keys()) == [
            "speakerId",
            "gender",
            "speaker_age",
            "genderSource",
            "speakerNativity",
            "speakerNativitySource",
            "speakerRole",
            "speakerRoleSource",
            "languages",
        ]


class TestStructure:
    def test_type_constants(self, vi_en_segments, vi_config, vi_speaker_map):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        assert obj["type"]["name"] == "MULTI_SPEAKER_LONG_FORM_TRANSCRIPTION"
        assert obj["type"]["version"] == "3.2"

    def test_login_encrypted(self, vi_en_segments, vi_config, vi_speaker_map):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        assert obj["value"]["annotatorInfo"]["loginEncrypted"] == "N/A"

    def test_domainlist_is_array_with_one_item(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        domain_list = obj["value"]["domainInfo"]["domainList"]
        assert isinstance(domain_list, list)
        assert len(domain_list) == 1
        assert domain_list[0]["domain"] == "Call-center"
        assert domain_list[0]["topicList"] == ["AIR"]

    def test_languages_primary_only(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        assert obj["value"]["languages"] == ["vi_VN"]

    def test_language_info(self, vi_en_segments, vi_config, vi_speaker_map):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        info = obj["value"]["languageInfo"]
        assert info["spokenLanguages"] == ["vi_VN", "en_VN"]
        assert info["speakerDominantVarieties"] == [
            {
                "languageLocale": "vi_VN",
                "languageVariety": [],
                "otherLanguageInfluence": [],
            }
        ]


class TestSegments:
    def test_segment_count(self, vi_en_segments, vi_config, vi_speaker_map):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        assert len(obj["value"]["segments"]) == 4

    def test_numeric_start_end(self, vi_en_segments, vi_config, vi_speaker_map):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        seg = obj["value"]["segments"][0]
        assert seg["start"] == 4.04
        assert seg["end"] == 7.4
        assert isinstance(seg["start"], float)

    def test_sorted_by_start(self, vi_config, vi_speaker_map):
        from src.models import TranscriptSegment

        # Deliberately out-of-order input.
        segs = [
            TranscriptSegment("SPK001", "5", "6", 5.0, 6.0, "second"),
            TranscriptSegment("SPK002", "1", "2", 1.0, 2.0, "first"),
        ]
        obj = build_conversation_json(segs, vi_config, vi_speaker_map)
        starts = [s["start"] for s in obj["value"]["segments"]]
        assert starts == sorted(starts)

    def test_transliteration_lowercase_and_null(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        seg = obj["value"]["segments"][0]
        assert "transliteration" in seg["transcriptionData"]
        assert "Transliteration" not in seg["transcriptionData"]
        assert seg["transcriptionData"]["transliteration"] is None

    def test_content_preserved(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        contents = [
            s["transcriptionData"]["content"] for s in obj["value"]["segments"]
        ]
        assert any("Tôi rất bức bội." in c for c in contents)


class TestSpeakers:
    def test_one_per_unique_speaker(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        speakers = obj["value"]["speakers"]
        assert len(speakers) == 2
        assert {s["speakerId"] for s in speakers} == {"S1", "S2"}

    def test_speaker_sources(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        for s in obj["value"]["speakers"]:
            assert s["genderSource"] == "Annotator"
            assert s["speakerNativitySource"] == "Annotator"
            assert s["speakerRoleSource"] == ""  # none are No-Speaker
            # Real speakers carry both primary and secondary languages.
            assert s["languages"] == ["vi_VN", "en_VN"]

    def test_no_speaker_role_source(self, vi_en_segments, vi_config):
        from src.models import SpeakerMapping

        smap = {
            "SPK001": SpeakerMapping(
                "SPK001", "S1", "No-Speaker", "Unknown", "Unknown", "Unknown"
            ),
            "SPK002": SpeakerMapping(
                "SPK002", "S2", "Customer", "Male", "40-50", "Native"
            ),
        }
        obj = build_conversation_json(vi_en_segments, vi_config, smap)
        # No-Speaker is listed first, matching the client sample, even though
        # SPK002 (the real speaker) appears first in the transcript.
        assert obj["value"]["speakers"][0]["speakerRole"] == "No-Speaker"
        s1 = next(s for s in obj["value"]["speakers"] if s["speakerId"] == "S1")
        assert s1["speakerRoleSource"] == "Annotator"
        assert s1["languages"] == []
        assert s1["gender"] == "NA"
        assert s1["speaker_age"] == "NA"
        assert s1["speakerNativity"] == "NA"
        # Sources stay "Annotator" even for a No-Speaker.
        assert s1["genderSource"] == "Annotator"
        assert s1["speakerNativitySource"] == "Annotator"


class TestSerialization:
    def test_reparseable_and_utf8(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        obj = _build(vi_en_segments, vi_config, vi_speaker_map)
        data = json_to_bytes(obj)
        text = data.decode("utf-8")
        reloaded = json.loads(text)
        assert reloaded == obj

    def test_unicode_not_escaped(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        data = json_to_bytes(_build(vi_en_segments, vi_config, vi_speaker_map))
        assert "Tôi rất bức bội." in data.decode("utf-8")

    def test_filename(self, vi_config):
        assert (
            json_filename(vi_config)
            == "vi-VN_English_AIR_48kHz_Conv0347.json"
        )

    def test_hyphen_normalized_in_codes(
        self, vi_en_segments, vi_speaker_map, vi_config
    ):
        # Force a hyphen into the code and confirm it is normalized out.
        cfg = dataclasses.replace(vi_config, primary_language_code="vi-VN")
        obj = build_conversation_json(vi_en_segments, cfg, vi_speaker_map)
        assert obj["value"]["languages"] == ["vi_VN"]
        assert obj["value"]["segments"][0]["language"] == "vi_VN"
