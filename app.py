"""Transcript Metadata & JSON Generator — Streamlit entry point.

The full multi-stage UI is built in later milestones. This entry point wires
up the foundation (language config, parsers) so the app runs locally.
"""

from __future__ import annotations

import streamlit as st

from src.models import load_language_records


def main() -> None:
    st.set_page_config(
        page_title="Transcript Metadata & JSON Generator",
        layout="wide",
    )
    st.title("Transcript Metadata & JSON Generator")
    st.caption(
        "Convert a timestamped multilingual transcript into rawmetadata, "
        "metadata, and per-conversation JSON."
    )

    records = load_language_records()
    st.info(
        f"Foundation ready — {len(records)} languages loaded from config. "
        "Upload and generation stages arrive in later milestones."
    )


if __name__ == "__main__":
    main()
