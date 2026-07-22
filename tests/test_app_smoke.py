"""Smoke tests that render each UI stage via Streamlit's AppTest.

These catch UI-only failures (e.g. duplicate element IDs) that the pure-logic
tests cannot, by actually executing app.py through the Streamlit runtime.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"


def _run_stage(segments, stage: int) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["segments"] = segments
    at.session_state["uploaded_name"] = "vi-VN_English_AIR_48kHz_Conv0347.txt"
    at.session_state["processed_key"] = "seeded"
    at.session_state["stage"] = stage
    at.run()
    return at


@pytest.mark.parametrize("stage", [1, 2, 3])
def test_stage_renders_without_exception(vi_en_segments, stage):
    at = _run_stage(vi_en_segments, stage)
    assert not at.exception, at.exception


def test_two_speaker_cards_do_not_collide(vi_en_segments):
    # Two speakers render the read-only "Speaker Languages" field twice; this
    # would raise StreamlitDuplicateElementId without a unique key per card.
    at = _run_stage(vi_en_segments, 1)
    assert not at.exception, at.exception


def _seed_full_config(at, segments) -> None:
    at.session_state["segments"] = segments
    at.session_state["uploaded_name"] = "vi-VN_English_AIR_48kHz_Conv0347.txt"
    at.session_state["processed_key"] = "seeded"
    at.session_state["cfg_conv_id"] = "Conv0347"
    at.session_state["cfg_language"] = "Vietnamese"
    at.session_state["cfg_domain"] = "AIR"
    at.session_state["cfg_sampling"] = "48kHz"
    at.session_state["cfg_annotator"] = ""
    at.session_state["cfg_cs_primary"] = 70
    at.session_state["cfg_cs_secondary"] = 30
    at.session_state["cfg_script_path"] = "vi-VN_English_AIR_48kHz_Conv0347.txt"
    at.session_state["cfg_master"] = "ClientTranscriptionGuidelines_en_US_3.2"
    at.session_state["cfg_audio_path"] = ""
    for lbl, sid, role in [("SPK001", "S1", "Agent"), ("SPK002", "S2", "Customer")]:
        at.session_state[f"spk_{lbl}_id"] = sid
        at.session_state[f"spk_{lbl}_role"] = role
        at.session_state[f"spk_{lbl}_gender"] = "Unknown"
        at.session_state[f"spk_{lbl}_age"] = "26-40"
        at.session_state[f"spk_{lbl}_nativity"] = "Unknown"


def _text_input_by_key(at, key):
    for widget in at.text_input:
        if widget.key == key:
            return widget
    raise KeyError(key)


def test_annotator_id_survives_navigation(vi_en_segments):
    # Type the Annotator ID on the Configure stage, then move to Generate.
    # Without the persistence pin, Streamlit drops the value and the Generate
    # stage reports "Annotator ID is required".
    at = AppTest.from_file(str(APP), default_timeout=30)
    _seed_full_config(at, vi_en_segments)
    at.session_state["stage"] = 1
    at.run()
    _text_input_by_key(at, "cfg_annotator").set_value("annot_001").run()

    at.session_state["stage"] = 3
    at.run()
    assert not at.exception, at.exception
    errors = [e.value for e in at.error]
    assert not any("Annotator ID is required" in e for e in errors), errors
    assert at.session_state["cfg_annotator"] == "annot_001"
