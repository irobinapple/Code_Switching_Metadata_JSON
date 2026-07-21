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
