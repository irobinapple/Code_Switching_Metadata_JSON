"""Tests for rawmetadata-scoped validation (Milestone 2 scope)."""

from __future__ import annotations

import dataclasses

from src.models import SpeakerMapping
from src.transformers import build_rawmetadata
from src.validators import validate_rawmetadata


def _validate(segments, config, speaker_map):
    frame = build_rawmetadata(segments, config, speaker_map)
    return frame, validate_rawmetadata(frame, config, speaker_map, segments)


class TestCleanInputPasses:
    def test_no_blocking_errors(self, vi_en_segments, vi_config, vi_speaker_map):
        _, result = _validate(vi_en_segments, vi_config, vi_speaker_map)
        assert not result.has_blocking_errors, result.errors


class TestBlockingErrors:
    def test_blank_convid(self, vi_en_segments, vi_config, vi_speaker_map):
        cfg = dataclasses.replace(vi_config, conv_id="")
        _, result = _validate(vi_en_segments, cfg, vi_speaker_map)
        assert any("ConvID" in e for e in result.errors)

    def test_blank_annotator(self, vi_en_segments, vi_config, vi_speaker_map):
        cfg = dataclasses.replace(vi_config, annotator_id="  ")
        _, result = _validate(vi_en_segments, cfg, vi_speaker_map)
        assert any("Annotator" in e for e in result.errors)

    def test_invalid_domain(self, vi_en_segments, vi_config, vi_speaker_map):
        cfg = dataclasses.replace(vi_config, domain="NOPE")
        _, result = _validate(vi_en_segments, cfg, vi_speaker_map)
        assert any("Domain" in e for e in result.errors)

    def test_incomplete_speaker_mapping(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        broken = dict(vi_speaker_map)
        broken["SPK001"] = dataclasses.replace(
            vi_speaker_map["SPK001"], speaker_id=""
        )
        _, result = _validate(vi_en_segments, vi_config, broken)
        assert any("incomplete" in e for e in result.errors)

    def test_start_ge_end(self, vi_en_segments, vi_config, vi_speaker_map):
        segs = list(vi_en_segments)
        segs[0] = dataclasses.replace(segs[0], start_sec=10.0, end_sec=5.0)
        _, result = _validate(segs, vi_config, vi_speaker_map)
        assert any("not before" in e for e in result.errors)

    def test_zero_turns(self, vi_config, vi_speaker_map):
        _, result = _validate([], vi_config, vi_speaker_map)
        assert any("zero valid turns" in e for e in result.errors)


class TestWarnings:
    def test_cs_ratio_not_100(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        cfg = dataclasses.replace(
            vi_config, cs_ratio_primary=60, cs_ratio_secondary=30
        )
        _, result = _validate(vi_en_segments, cfg, vi_speaker_map)
        assert any("total" in w for w in result.warnings)

    def test_non_spk_style_label(self, vi_config):
        segs_map = {
            "AGENT": SpeakerMapping(
                transcript_label="AGENT",
                speaker_id="S1",
                role="Agent",
                gender="Female",
                age_bucket="30-40",
                nativity="Native",
            )
        }
        from src.models import TranscriptSegment

        segs = [
            TranscriptSegment(
                speaker_label="AGENT",
                start_text="00:00:01,000",
                end_text="00:00:02,000",
                start_sec=1.0,
                end_sec=2.0,
                content_text="Hello",
            )
        ]
        _, result = _validate(segs, vi_config, segs_map)
        assert any("SPK" in w for w in result.warnings)

    def test_no_speaker_with_content_warns(
        self, vi_en_segments, vi_config, vi_speaker_map
    ):
        m = dict(vi_speaker_map)
        m["SPK001"] = dataclasses.replace(
            vi_speaker_map["SPK001"], role="No-Speaker"
        )
        _, result = _validate(vi_en_segments, vi_config, m)
        assert any("No-Speaker" in w for w in result.warnings)
