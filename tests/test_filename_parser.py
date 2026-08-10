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


class TestUnderscoredLocaleIsBlocked:
    """`fr_FR` instead of `fr-FR` must stop the upload with a rename hint."""

    def test_underscored_locale_blocks(self):
        result = parse_filename(
            "fr_FR_English_INS_16KHz_Conv134.docx", LANGS
        )
        assert result.is_blocked
        assert result.errors

    def test_suggested_filename_uses_a_hyphen(self):
        result = parse_filename(
            "fr_FR_English_INS_16KHz_Conv134.docx", LANGS
        )
        assert (
            result.suggested_filename
            == "fr-FR_English_INS_16KHz_Conv134.docx"
        )

    def test_error_names_both_forms(self):
        result = parse_filename("vi_VN_English_AIR_48kHz_Conv059.txt", LANGS)
        message = " ".join(result.errors)
        assert "vi_VN" in message
        assert "vi-VN" in message

    def test_correct_filename_is_not_blocked(self):
        result = parse_filename(
            "fr-FR_English_INS_16KHz_Conv134.docx", LANGS
        )
        assert not result.is_blocked
        assert result.locale == "fr-FR"
        assert result.conv_id == "Conv134"
        assert result.domain == "INS"
        assert result.sampling_rate == "16kHz"

    def test_casing_is_preserved_in_the_suggestion(self):
        result = parse_filename("FR_fr_English_INS_16KHz_Conv134.docx", LANGS)
        # Matched case-insensitively; the rename keeps what the user typed.
        assert result.suggested_filename == "FR-fr_English_INS_16KHz_Conv134.docx"


class TestLanguageConfigNormalization:
    def test_all_records(self):
        assert len(LANGS) == 32

    def test_display_names_unique(self):
        # The language dropdown selects by display name, so duplicates would
        # make a record unreachable (the client list has "Arabic" twice).
        names = [r.display_name for r in LANGS]
        assert len(names) == len(set(names))

    def test_client_list_codes_all_present(self):
        expected = {
            "ca-ES", "pt-BR", "pt-PT", "fr-CA", "fr-FR", "it-IT", "de-DE",
            "de-CH", "es-ES", "es-US", "nl-NL", "sv-SE", "da-DK", "fi-FI",
            "no-NO", "zh-CN", "zh-TW", "zh-HK", "ja-JP", "ko-KR", "ar-AE",
            "ar-SA", "hi-IN", "th-TH", "he-IL", "tr-TR", "ru-RU", "vi-VN",
            "ms-MY", "ta-IN", "ar-FR",
        }
        codes = {r.language_code for r in LANGS}
        assert expected <= codes
        # Tagalog stays on tl-PH (the client list's tl-TL is Timor-Leste).
        assert "tl-PH" in codes

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
