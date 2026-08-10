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
    at.session_state["cfg_annotator"] = None
    at.session_state["cfg_cs_primary"] = 70
    at.session_state["cfg_cs_secondary"] = 30
    at.session_state["cfg_script_path"] = "vi-VN_English_AIR_48kHz_Conv0347.txt"
    at.session_state["cfg_master"] = "awsTranscriptionGuidelines_en_US_3.2"
    at.session_state["cfg_audio_path"] = ""
    for lbl, sid, role in [("SPK001", "S1", "Agent"), ("SPK002", "S2", "Customer")]:
        at.session_state[f"spk_{lbl}_id"] = sid
        at.session_state[f"spk_{lbl}_role"] = role
        at.session_state[f"spk_{lbl}_gender"] = "Unknown"
        at.session_state[f"spk_{lbl}_age"] = "26-40"
        at.session_state[f"spk_{lbl}_nativity"] = "Unknown"


def _widget_by_key(widgets, key):
    for widget in widgets:
        if widget.key == key:
            return widget
    raise KeyError(key)


def test_no_widget_default_vs_session_state_warning(vi_en_segments, caplog):
    """Speaker cards must not warn about a value set two ways.

    The read-only "Speaker Languages" box is created with an explicit value,
    so it must be excluded from the session-state pin in _persist_widget_state
    or Streamlit logs a warning on every rerun.
    """
    import logging

    for name in list(logging.root.manager.loggerDict):
        if name.startswith("streamlit"):
            logging.getLogger(name).propagate = True

    at = AppTest.from_file(str(APP), default_timeout=30)
    _seed_full_config(at, vi_en_segments)
    at.session_state["stage"] = 1
    with caplog.at_level(logging.WARNING):
        at.run()
        at.run()  # the pin only collides once the key already exists

    offending = [
        r.getMessage()
        for r in caplog.records
        if "default value but also had its value set" in r.getMessage()
    ]
    assert not offending, offending


def _secondary_ratio_widget(at):
    return next(
        n for n in at.number_input if n.label == "CS Ratio Secondary"
    )


class TestDerivedSecondaryCsRatio:
    """Secondary ratio is always 100 - primary, and never user-editable."""

    def _configured(self, segments, primary):
        at = AppTest.from_file(str(APP), default_timeout=30)
        _seed_full_config(at, segments)
        at.session_state["cfg_cs_primary"] = primary
        at.session_state["stage"] = 1
        at.run()
        assert not at.exception, at.exception
        return at

    def test_whole_number_primary(self, vi_en_segments):
        at = self._configured(vi_en_segments, 70.0)
        assert _secondary_ratio_widget(at).value == 30.0

    def test_decimal_primary(self, vi_en_segments):
        at = self._configured(vi_en_segments, 60.8)
        assert _secondary_ratio_widget(at).value == 39.2

    def test_secondary_is_disabled(self, vi_en_segments):
        at = self._configured(vi_en_segments, 70.0)
        assert _secondary_ratio_widget(at).disabled


class TestAnnotatorIdDropdown:
    def _configured(self, segments, annotator):
        at = AppTest.from_file(str(APP), default_timeout=30)
        _seed_full_config(at, segments)
        at.session_state["cfg_annotator"] = annotator
        at.session_state["stage"] = 1
        at.run()
        assert not at.exception, at.exception
        return at

    def test_lists_the_configured_ids(self, vi_en_segments):
        from src.constants import ANNOTATOR_IDS

        at = self._configured(vi_en_segments, None)
        options = list(_widget_by_key(at.selectbox, "cfg_annotator").options)
        assert options == ANNOTATOR_IDS

    def test_accepts_an_id_outside_the_list(self, vi_en_segments):
        # What typing a new ID in the browser produces.
        at = self._configured(vi_en_segments, "annot_099")
        assert at.session_state["cfg_annotator"] == "annot_099"


def test_annotator_id_survives_navigation(vi_en_segments):
    # Type the Annotator ID on the Configure stage, then move to Generate.
    # Without the persistence pin, Streamlit drops the value and the Generate
    # stage reports "Annotator ID is required".
    at = AppTest.from_file(str(APP), default_timeout=30)
    _seed_full_config(at, vi_en_segments)
    at.session_state["stage"] = 1
    at.run()
    _widget_by_key(at.selectbox, "cfg_annotator").set_value("annot_001").run()

    at.session_state["stage"] = 3
    at.run()
    assert not at.exception, at.exception
    errors = [e.value for e in at.error]
    assert not any("Annotator ID is required" in e for e in errors), errors
    assert at.session_state["cfg_annotator"] == "annot_001"
