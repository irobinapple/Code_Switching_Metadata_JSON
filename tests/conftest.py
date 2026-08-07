"""Shared pytest fixtures for the transcript metadata generator tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models import ConversationConfig, SpeakerMapping, load_language_records
from src.transcript_parser import parse_transcript_text

FIXTURES = Path(__file__).parent / "fixtures"
CANONICAL_TRANSCRIPT = FIXTURES / "vi-VN_English_AIR_48kHz_Conv0347.txt"


@pytest.fixture
def vi_en_text() -> str:
    return CANONICAL_TRANSCRIPT.read_text(encoding="utf-8")


@pytest.fixture
def vi_en_segments(vi_en_text):
    return parse_transcript_text(vi_en_text)


@pytest.fixture
def vietnamese_record():
    records = load_language_records()
    return next(r for r in records if r.display_name == "Vietnamese")


@pytest.fixture
def vi_config(vietnamese_record) -> ConversationConfig:
    return ConversationConfig(
        conv_id="Conv0347",
        lang_pair=vietnamese_record.lang_pair,
        primary_language_code=vietnamese_record.primary_language_code,
        secondary_language_code=vietnamese_record.secondary_language_code,
        metadata_type=vietnamese_record.metadata_type,
        domain="AIR",
        sampling_rate="48kHz",
        recording_date="2026-07-21",
        conversation_script_path="vi-VN_English_AIR_48kHz_Conv0347.txt",
        audio_file_path="",
        master_convention_name="awsTranscriptionGuidelines_en_US_3.2",
        custom_addendum="vi_VN_2.0",
        annotator_id="ann_042",
        cs_ratio_primary=70,
        cs_ratio_secondary=30,
    )


@pytest.fixture
def vi_speaker_map() -> dict[str, SpeakerMapping]:
    return {
        "SPK001": SpeakerMapping(
            transcript_label="SPK001",
            speaker_id="S1",
            role="Agent",
            gender="Female",
            age_bucket="30-40",
            nativity="Native",
        ),
        "SPK002": SpeakerMapping(
            transcript_label="SPK002",
            speaker_id="S2",
            role="Customer",
            gender="Male",
            age_bucket="40-50",
            nativity="Native",
        ),
    }
