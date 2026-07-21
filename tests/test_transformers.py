"""Tests for the rawmetadata transformation and exports."""

from __future__ import annotations

import io

import pandas as pd
from openpyxl import load_workbook

from src.constants import RAWMETADATA_COLUMNS
from src.exporters import (
    RAWMETADATA_SHEET_NAME,
    rawmetadata_to_csv_bytes,
    rawmetadata_to_xlsx_bytes,
)
from src.transformers import build_rawmetadata, segment_id


class TestSegmentId:
    def test_zero_pad_width_three(self):
        assert segment_id(1) == "seg001"
        assert segment_id(42) == "seg042"

    def test_beyond_three_digits(self):
        assert segment_id(1234) == "seg1234"


class TestRawmetadataShape:
    def test_exact_column_order(self, vi_en_segments, vi_config, vi_speaker_map):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert list(frame.columns) == RAWMETADATA_COLUMNS
        assert len(frame.columns) == 34

    def test_one_row_per_segment(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert len(frame) == len(vi_en_segments) == 4

    def test_turn_no_sequential(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert frame["Turn_No"].tolist() == [1, 2, 3, 4]

    def test_segment_ids(self, vi_en_segments, vi_config, vi_speaker_map):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert frame["Segment_ID"].tolist() == [
            "seg001",
            "seg002",
            "seg003",
            "seg004",
        ]


class TestRawmetadataValues:
    def test_source_timestamp_text_retained(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert frame["Start_Time_Sec"].iloc[0] == "00:00:04,040"
        assert frame["End_Time_Sec"].iloc[0] == "00:00:07,400"

    def test_defaults(self, vi_en_segments, vi_config, vi_speaker_map):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert (frame["Primary_Type"] == "Speech").all()
        assert (frame["Loudness_Level"] == "Normal").all()

    def test_language_derivations(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert (frame["Segment_Primary_Language"] == "vi_VN").all()
        assert (frame["Segment_Languages"] == "vi_VN, en_VN").all()
        assert (frame["Speaker_Languages"] == "vi_VN, en_VN").all()
        assert (frame["LangPair"] == "vi-VN_English").all()

    def test_speaker_sources(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert (frame["Speaker_Gender_Source"] == "Annotator").all()
        assert (frame["Speaker_Nativity_Source"] == "Annotator").all()
        # No No-Speaker rows here, so role source is empty everywhere.
        assert (frame["Speaker_Role_Source"] == "").all()

    def test_transliteration_blank_for_non_translit(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert (frame["Transliteration_Text"] == "").all()

    def test_qc_notes_blank(self, vi_en_segments, vi_config, vi_speaker_map):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        assert (frame["QC_Notes"] == "").all()


class TestExports:
    def test_csv_utf8_bom_and_unicode(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        data = rawmetadata_to_csv_bytes(frame)
        assert data.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
        text = data.decode("utf-8-sig")
        assert "Tôi rất bức bội." in text

    def test_xlsx_sheet_name_and_text_timestamps(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        data = rawmetadata_to_xlsx_bytes(frame)
        workbook = load_workbook(io.BytesIO(data))
        assert workbook.sheetnames == [RAWMETADATA_SHEET_NAME]
        worksheet = workbook[RAWMETADATA_SHEET_NAME]

        header = [c.value for c in worksheet[1]]
        start_col = header.index("Start_Time_Sec") + 1
        # Data cell stores the source string and is Text-formatted.
        cell = worksheet.cell(row=2, column=start_col)
        assert cell.value == "00:00:04,040"
        assert cell.number_format == "@"
        assert isinstance(cell.value, str)

    def test_xlsx_unicode_content(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        frame = build_rawmetadata(vi_en_segments, vi_config, vi_speaker_map)
        data = rawmetadata_to_xlsx_bytes(frame)
        workbook = load_workbook(io.BytesIO(data))
        worksheet = workbook[RAWMETADATA_SHEET_NAME]
        header = [c.value for c in worksheet[1]]
        content_col = header.index("Content_Text") + 1
        values = [
            worksheet.cell(row=r, column=content_col).value
            for r in range(2, worksheet.max_row + 1)
        ]
        assert any("Tôi rất bức bội." in (v or "") for v in values)
