"""Tests for the two-line SRT transcript parser and ingestion."""

from __future__ import annotations

import pandas as pd
import pytest

from src.transcript_parser import (
    TranscriptParseError,
    detect_speakers,
    parse_csv_mapped,
    parse_transcript_text,
)


class TestTwoLineFormat:
    def test_canonical_segment_count(self, vi_en_segments):
        assert len(vi_en_segments) == 4

    def test_first_segment_fields(self, vi_en_segments):
        seg = vi_en_segments[0]
        assert seg.speaker_label == "SPK001"
        assert seg.start_text == "00:00:04,040"
        assert seg.end_text == "00:00:07,400"
        assert seg.start_sec == pytest.approx(4.04)
        assert seg.end_sec == pytest.approx(7.4)
        assert seg.content_text.startswith("Xin chào")

    def test_speaker_labels_bracket_stripped(self, vi_en_segments):
        assert all("[" not in s.speaker_label for s in vi_en_segments)

    def test_detect_speakers_order(self, vi_en_segments):
        assert detect_speakers(vi_en_segments) == ["SPK001", "SPK002"]


class TestMultilineContent:
    def test_content_lines_joined_with_space(self, vi_en_segments):
        third = vi_en_segments[2]
        assert "check your booking right away." in third.content_text
        assert "I can see your reservation here." in third.content_text
        # Two source lines joined by a single space, no newline.
        assert "\n" not in third.content_text
        assert "right away. I can see" in third.content_text


class TestUnicodePreservation:
    def test_vietnamese_diacritics_intact(self, vi_en_segments):
        assert "Tôi rất bức bội." in vi_en_segments[1].content_text

    def test_code_switched_english_intact(self, vi_en_segments):
        assert "My flight to Paris" in vi_en_segments[1].content_text


class TestInvalidTimestampLine:
    def test_arrow_line_that_cannot_parse_raises(self):
        bad = "not-a-time --> also-bad [SPK001]\nsome content"
        with pytest.raises(TranscriptParseError):
            parse_transcript_text(bad)

    def test_empty_transcript_yields_no_segments(self):
        assert parse_transcript_text("") == []


class TestBareSpeakerAndBlankLines:
    def test_bare_speaker_without_brackets(self):
        text = "00:00:01,000 --> 00:00:02,000 SPK001\nHello there"
        segs = parse_transcript_text(text)
        assert segs[0].speaker_label == "SPK001"
        assert segs[0].content_text == "Hello there"

    def test_blank_lines_between_segments_ignored(self):
        text = (
            "00:00:01,000 --> 00:00:02,000 [SPK001]\nHi\n\n\n"
            "00:00:03,000 --> 00:00:04,000 [SPK002]\nBye"
        )
        segs = parse_transcript_text(text)
        assert len(segs) == 2
        assert segs[0].content_text == "Hi"
        assert segs[1].content_text == "Bye"


class TestCsvMapped:
    def test_mapped_columns(self):
        frame = pd.DataFrame(
            {
                "s": ["00:00:01,000", "00:00:03,000"],
                "e": ["00:00:02,000", "00:00:04,000"],
                "spk": ["SPK001", "SPK002"],
                "text": ["Xin chào", "Hello"],
            }
        )
        segs = parse_csv_mapped(frame, "s", "e", "spk", "text")
        assert len(segs) == 2
        assert segs[0].content_text == "Xin chào"
        assert segs[1].start_sec == pytest.approx(3.0)
