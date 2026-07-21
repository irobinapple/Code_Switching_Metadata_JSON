"""Tests for parse_timestamp_to_seconds."""

from __future__ import annotations

import pytest

from src.timestamp_parser import TimestampError, parse_timestamp_to_seconds


class TestValidFormats:
    def test_srt_comma_decimal_primary(self):
        # HH:MM:SS,mmm — the confirmed real SRT form.
        assert parse_timestamp_to_seconds("00:01:23,500") == pytest.approx(83.5)

    def test_srt_comma_decimal_with_hours(self):
        assert parse_timestamp_to_seconds("01:02:03,250") == pytest.approx(
            3723.25
        )

    def test_dot_decimal(self):
        assert parse_timestamp_to_seconds("00:01:23.500") == pytest.approx(83.5)

    def test_m_ss_dot(self):
        assert parse_timestamp_to_seconds("1:23.5") == pytest.approx(83.5)

    def test_mm_ss_dot(self):
        assert parse_timestamp_to_seconds("01:23.500") == pytest.approx(83.5)

    def test_plain_seconds(self):
        assert parse_timestamp_to_seconds("83.5") == pytest.approx(83.5)

    def test_plain_integer_seconds(self):
        assert parse_timestamp_to_seconds("5") == pytest.approx(5.0)

    def test_zero(self):
        assert parse_timestamp_to_seconds("00:00:00,000") == pytest.approx(0.0)

    def test_whitespace_trimmed(self):
        assert parse_timestamp_to_seconds("  00:00:04,040  ") == pytest.approx(
            4.04
        )

    def test_six_digit_no_colon_defensive(self):
        # HHMMSS defensive form: 00:01:23,500
        assert parse_timestamp_to_seconds("000123,500") == pytest.approx(83.5)

    def test_six_digit_no_colon_dot(self):
        assert parse_timestamp_to_seconds("010203.250") == pytest.approx(3723.25)


class TestInvalidFormats:
    def test_empty_string(self):
        with pytest.raises(TimestampError):
            parse_timestamp_to_seconds("")

    def test_whitespace_only(self):
        with pytest.raises(TimestampError):
            parse_timestamp_to_seconds("   ")

    def test_non_numeric(self):
        with pytest.raises(TimestampError):
            parse_timestamp_to_seconds("abc")

    def test_minutes_out_of_range(self):
        with pytest.raises(TimestampError):
            parse_timestamp_to_seconds("00:75:00,000")

    def test_seconds_out_of_range(self):
        with pytest.raises(TimestampError):
            parse_timestamp_to_seconds("00:00:75,000")

    def test_too_many_colon_parts(self):
        with pytest.raises(TimestampError):
            parse_timestamp_to_seconds("00:00:00:00")

    def test_garbage_with_colon(self):
        with pytest.raises(TimestampError):
            parse_timestamp_to_seconds("aa:bb,cc")
