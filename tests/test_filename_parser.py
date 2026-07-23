"""Tests for filename parsing and language-config normalization."""

from __future__ import annotations

from src.filename_parser import parse_filename
from src.models import load_language_records


LANGS = load_language_records()


class TestUnderscoreStyle:
    def test_full_source_transcript_name(self):
        result = parse_filename("vi-VN_English_AIR_48Khz_Conv059.docx", LANGS)
        assert result.conv_id == "Conv059"
        assert result.locale == "vi-VN"
        assert result.domain == "AIR"
        assert result.sampling_rate == "48kHz"
        assert result.warnings == []

    def test_json_delivery_name(self):
        result = parse_filename("vi-VN_English_AIR_48kHz_Conv0347.json", LANGS)
        assert result.conv_id == "Conv0347"
        assert result.locale == "vi-VN"
        assert result.domain == "AIR"
        assert result.sampling_rate == "48kHz"

    def test_variable_convid_width(self):
        assert parse_filename("vi-VN_AIR_8kHz_Conv0592.docx", LANGS).conv_id == (
            "Conv0592"
        )
        assert parse_filename("vi-VN_AIR_8kHz_Conv5.docx", LANGS).conv_id == (
            "Conv5"
        )

    def test_sampling_rate_case_insensitive(self):
        assert parse_filename(
            "vi-VN_AIR_16KHZ_Conv1.docx", LANGS
        ).sampling_rate == "16kHz"


class TestCompactFallback:
    def test_run_together_best_effort(self):
        result = parse_filename("vi-VNEnglishAIR48kHzConv0592.docx", LANGS)
        assert result.conv_id == "Conv0592"
        assert result.locale == "vi-VN"
        assert result.domain == "AIR"
        assert result.sampling_rate == "48kHz"


class TestMissingTokens:
    def test_no_convid_warns(self):
        result = parse_filename("vi-VN_AIR_8kHz.docx", LANGS)
        assert result.conv_id is None
        assert any("ConvID" in w for w in result.warnings)

    def test_no_domain_warns(self):
        result = parse_filename("vi-VN_8kHz_Conv1.docx", LANGS)
        assert result.domain is None
        assert any("domain" in w.lower() for w in result.warnings)

    def test_no_sampling_warns(self):
        result = parse_filename("vi-VN_AIR_Conv1.docx", LANGS)
        assert result.sampling_rate is None
        assert any("sampling" in w.lower() for w in result.warnings)

    def test_no_locale_warns(self):
        result = parse_filename("AIR_8kHz_Conv1.docx", LANGS)
        assert result.locale is None
        assert any("locale" in w.lower() for w in result.warnings)


class TestLanguageConfigNormalization:
    def test_all_25_records(self):
        assert len(LANGS) == 25

    def test_no_hyphen_in_derived_codes(self):
        for rec in LANGS:
            assert "-" not in rec.primary_language_code
            assert "-" not in rec.secondary_language_code
            assert "_" in rec.primary_language_code

    def test_primary_codes_all_distinct(self):
        # Primary codes must be fully distinct — they drive LangPair and
        # filename construction, so no two languages may share one.
        codes = [r.primary_language_code for r in LANGS]
        assert len(codes) == len(set(codes))

    def test_secondary_code_rule(self):
        # Client rule (reversed): the secondary code is bare `en` for every
        # locale EXCEPT the Indian ones (Hindi & Tamil), which are `en_IN`.
        for rec in LANGS:
            if rec.language_code.endswith("-IN"):
                assert rec.secondary_language_code == "en_IN"
            else:
                assert rec.secondary_language_code == "en"
        indian = [
            r.display_name
            for r in LANGS
            if r.secondary_language_code == "en_IN"
        ]
        assert set(indian) == {"Hindi", "Tamil"}

    def test_locale_uses_hyphen(self):
        for rec in LANGS:
            assert "-" in rec.language_code
            assert "_" not in rec.language_code

    def test_vietnamese_record(self):
        vi = next(r for r in LANGS if r.display_name == "Vietnamese")
        assert vi.language_code == "vi-VN"
        assert vi.metadata_type == "Non-Transliteration"
        assert vi.primary_language_code == "vi_VN"
        assert vi.secondary_language_code == "en"
