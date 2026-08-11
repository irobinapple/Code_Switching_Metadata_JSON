"""Tests for Type 1 / Type 2 conversations and conversation-named exports."""

from __future__ import annotations

import dataclasses

from src.constants import (
    CONVERSATION_TYPE_1,
    CONVERSATION_TYPE_2,
    SPEAKER_COUNT_BY_TYPE,
    SPEAKER_ROLES,
)
from src.exporters import (
    metadata_csv_filename,
    rawmetadata_csv_filename,
    rawmetadata_xlsx_filename,
)
from src.json_builder import build_conversation_json, json_filename
from src.models import SpeakerMapping
from src.transcript_parser import detect_speakers
from src.transformers import (
    build_filename_stem,
    build_metadata,
    build_rawmetadata,
    role_for_label,
)


class TestConversationTypes:
    def test_expected_speaker_counts(self):
        assert SPEAKER_COUNT_BY_TYPE[CONVERSATION_TYPE_1] == 2
        assert SPEAKER_COUNT_BY_TYPE[CONVERSATION_TYPE_2] == 3

    def test_translator_role_available(self):
        assert "Translator" in SPEAKER_ROLES


class TestRoleForLabel:
    """Labels that name the role win over positional guessing."""

    def test_named_labels_map_to_their_role(self):
        assert role_for_label("Agent", 0, CONVERSATION_TYPE_2) == "Agent"
        assert (
            role_for_label("Translator", 1, CONVERSATION_TYPE_2) == "Translator"
        )
        assert role_for_label("Customer", 2, CONVERSATION_TYPE_2) == "Customer"

    def test_label_match_is_case_insensitive(self):
        assert role_for_label("translator", 5, CONVERSATION_TYPE_2) == "Translator"
        assert role_for_label("  AGENT  ", 9, CONVERSATION_TYPE_1) == "Agent"

    def test_opaque_labels_fall_back_to_position(self):
        assert role_for_label("SPK001", 0, CONVERSATION_TYPE_1) == "Agent"
        assert role_for_label("SPK002", 1, CONVERSATION_TYPE_1) == "Customer"

    def test_third_speaker_defaults_to_translator_in_type_2(self):
        assert role_for_label("SPK003", 2, CONVERSATION_TYPE_2) == "Translator"

    def test_type_1_has_no_third_positional_default(self):
        # Beyond the configured roles the first role is a safe fallback; the
        # UI blocks a 3-speaker transcript in Type 1 before this matters.
        assert role_for_label("SPK003", 2, CONVERSATION_TYPE_1) in SPEAKER_ROLES


class TestThreeSpeakerPipeline:
    """The real Type 2 transcript end to end."""

    def _mappings(self, labels):
        return {
            label: SpeakerMapping(
                transcript_label=label,
                speaker_id=f"0000{i + 1}{i + 1}",
                role=role_for_label(label, i, CONVERSATION_TYPE_2),
                gender="Female" if i % 2 else "Male",
                age_bucket="18-25",
                nativity="Native",
            )
            for i, label in enumerate(labels)
        }

    def test_three_speakers_detected(self, three_speaker_segments):
        assert detect_speakers(three_speaker_segments) == [
            "Agent",
            "Translator",
            "Customer",
        ]

    def test_metadata_has_one_row_per_speaker(
        self, three_speaker_segments, vi_config
    ):
        labels = detect_speakers(three_speaker_segments)
        frame = build_metadata(
            three_speaker_segments, vi_config, self._mappings(labels)
        )
        assert len(frame) == 3
        assert frame["Speaker_Role"].tolist() == [
            "Agent",
            "Translator",
            "Customer",
        ]

    def test_rawmetadata_keeps_34_columns(
        self, three_speaker_segments, vi_config
    ):
        labels = detect_speakers(three_speaker_segments)
        frame = build_rawmetadata(
            three_speaker_segments, vi_config, self._mappings(labels)
        )
        assert len(frame.columns) == 34
        assert len(frame) == len(three_speaker_segments)

    def test_json_carries_all_three_speakers(
        self, three_speaker_segments, vi_config
    ):
        labels = detect_speakers(three_speaker_segments)
        obj = build_conversation_json(
            three_speaker_segments, vi_config, self._mappings(labels)
        )
        roles = [s["speakerRole"] for s in obj["value"]["speakers"]]
        assert roles == ["Agent", "Translator", "Customer"]

    def test_translator_speaker_shape_matches_the_others(
        self, three_speaker_segments, vi_config
    ):
        labels = detect_speakers(three_speaker_segments)
        obj = build_conversation_json(
            three_speaker_segments, vi_config, self._mappings(labels)
        )
        speakers = obj["value"]["speakers"]
        assert list(speakers[1].keys()) == list(speakers[0].keys())
        translator = speakers[1]
        assert translator["speakerRoleSource"] == ""
        assert translator["languages"] == ["vi_VN", "en"]


class TestUploadGating:
    """Which transcript/type combinations the Upload stage accepts."""

    def _accepted(self, segments, conv_type):
        from src.constants import DEFAULT_SPEAKER_LABELS

        detected = detect_speakers(segments)
        unlabeled = bool(detected) and set(detected) <= set(
            DEFAULT_SPEAKER_LABELS
        )
        if unlabeled and conv_type == CONVERSATION_TYPE_2:
            return False
        return len(detected) == SPEAKER_COUNT_BY_TYPE[conv_type]

    def test_two_speaker_transcript_fits_type_1(self, vi_en_segments):
        assert self._accepted(vi_en_segments, CONVERSATION_TYPE_1)

    def test_two_speaker_transcript_rejected_by_type_2(self, vi_en_segments):
        assert not self._accepted(vi_en_segments, CONVERSATION_TYPE_2)

    def test_three_speaker_transcript_fits_type_2(self, three_speaker_segments):
        assert self._accepted(three_speaker_segments, CONVERSATION_TYPE_2)

    def test_three_speaker_transcript_rejected_by_type_1(
        self, three_speaker_segments
    ):
        assert not self._accepted(three_speaker_segments, CONVERSATION_TYPE_1)

    def test_unlabeled_transcript_rejected_by_type_2(self):
        from src.transcript_parser import parse_transcript_text

        segments = parse_transcript_text(
            "00:00:01,000 --> 00:00:02,000\nHola\n\n"
            "00:00:03,000 --> 00:00:04,000\nHello\n"
        )
        assert not self._accepted(segments, CONVERSATION_TYPE_2)
        # Still fine for Type 1, which can alternate two speakers.
        assert self._accepted(segments, CONVERSATION_TYPE_1)


class TestExportFilenames:
    """Every export is named after the conversation, like the JSON."""

    def test_names_derive_from_the_conversation(self, vi_config):
        cfg = dataclasses.replace(
            vi_config,
            conv_id="Conv120",
            lang_pair="es-US_English",
            domain="IT",
            sampling_rate="16kHz",
        )
        stem = build_filename_stem(cfg)
        assert stem == "es-US_English_IT_16kHz_Conv120"
        assert metadata_csv_filename(stem) == (
            "es-US_English_IT_16kHz_Conv120.csv"
        )
        assert rawmetadata_xlsx_filename(stem) == (
            "es-US_English_IT_16kHz_Conv120_rawmetadata.xlsx"
        )
        assert rawmetadata_csv_filename(stem) == (
            "es-US_English_IT_16kHz_Conv120_rawmetadata.csv"
        )
        assert json_filename(cfg) == "es-US_English_IT_16kHz_Conv120.json"

    def test_metadata_csv_matches_the_json_name(self, vi_config):
        stem = build_filename_stem(vi_config)
        assert (
            metadata_csv_filename(stem).removesuffix(".csv")
            == json_filename(vi_config).removesuffix(".json")
        )

    def test_metadata_and_rawmetadata_never_collide(self, vi_config):
        stem = build_filename_stem(vi_config)
        assert metadata_csv_filename(stem) != rawmetadata_csv_filename(stem)
