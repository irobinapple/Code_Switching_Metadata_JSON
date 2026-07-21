"""Transcript Metadata & JSON Generator — Streamlit UI.

Stages: Upload -> Configure -> Raw Metadata Preview -> Generate Metadata & JSON.
All parsing/transformation/validation logic lives in `src`; this module is UI
only. The Generate stage is completed in Milestone 3.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from src.constants import (
    DEFAULT_CS_RATIO_PRIMARY,
    DEFAULT_CS_RATIO_SECONDARY,
    DEFAULT_MASTER_CONVENTION_NAME,
    DOMAIN_CODES,
    SAMPLING_RATES,
    SPEAKER_GENDERS,
    SPEAKER_NATIVITIES,
    SPEAKER_ROLES,
)
from src.exporters import (
    metadata_to_csv_bytes,
    rawmetadata_to_csv_bytes,
    rawmetadata_to_xlsx_bytes,
    validation_report_json_bytes,
    validation_report_txt_bytes,
)
from src.filename_parser import parse_filename
from src.json_builder import (
    build_conversation_json,
    json_filename,
    json_to_bytes,
)
from src.models import (
    ConversationConfig,
    SpeakerMapping,
    load_language_records,
    language_by_locale,
)
from src.transcript_parser import (
    TranscriptParseError,
    detect_speakers,
    extract_text_from_docx,
    extract_text_from_txt,
    parse_csv_full_line_column,
    parse_csv_mapped,
    parse_transcript_text,
    read_csv_bytes,
)
from src.transformers import (
    build_metadata,
    build_rawmetadata,
    conversation_duration_sec,
)
from src.validators import run_full_validation, validate_rawmetadata

STAGES = [
    "Upload",
    "Configure",
    "Raw Metadata Preview",
    "Generate Metadata & JSON",
]


# --- Session helpers -------------------------------------------------------


def _init_state() -> None:
    st.session_state.setdefault("stage", 0)
    st.session_state.setdefault("segments", None)
    st.session_state.setdefault("fname_parse", None)
    st.session_state.setdefault("uploaded_name", None)
    st.session_state.setdefault("processed_key", None)


def _goto(stage_index: int) -> None:
    st.session_state["stage"] = stage_index


def _reset_project() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    _init_state()


# --- Header & stepper ------------------------------------------------------


def _render_header() -> None:
    st.set_page_config(
        page_title="Transcript Metadata & JSON Generator", layout="wide"
    )
    st.title("Transcript Metadata & JSON Generator")
    st.caption(
        "Convert a timestamped, multilingual code-switching transcript into "
        "rawmetadata, metadata, and per-conversation JSON."
    )


def _render_stepper() -> None:
    current = st.session_state["stage"]
    cols = st.columns(len(STAGES))
    for i, (col, name) in enumerate(zip(cols, STAGES)):
        marker = "●" if i == current else ("✓" if i < current else "○")
        col.markdown(f"**{marker} {i + 1}. {name}**")
    st.divider()


# --- Stage 1: Upload -------------------------------------------------------


def _extract_segments(name: str, data: bytes):
    lower = name.lower()
    if lower.endswith(".docx"):
        return parse_transcript_text(extract_text_from_docx(data))
    if lower.endswith(".txt"):
        return parse_transcript_text(extract_text_from_txt(data))
    if lower.endswith(".csv"):
        return _handle_csv(data)
    raise TranscriptParseError(
        "Unsupported file type. Upload a .docx, .csv, or .txt transcript."
    )


def _handle_csv(data: bytes):
    frame = read_csv_bytes(data)
    columns = list(frame.columns)
    st.markdown("**CSV column mapping**")
    mode = st.radio(
        "How is this CSV structured?",
        [
            "One column holds full transcript lines",
            "Separate start / end / speaker / content columns",
        ],
        key="csv_mode",
    )
    if mode.startswith("One column"):
        col = st.selectbox("Transcript line column", columns, key="csv_line_col")
        return parse_csv_full_line_column(frame, col)
    c1, c2, c3, c4 = st.columns(4)
    start = c1.selectbox("Start", columns, key="csv_start")
    end = c2.selectbox("End", columns, key="csv_end")
    speaker = c3.selectbox("Speaker", columns, key="csv_speaker")
    content = c4.selectbox("Content", columns, key="csv_content")
    return parse_csv_mapped(frame, start, end, speaker, content)


def _stage_upload(records) -> None:
    st.subheader("1. Upload a transcript")
    uploaded = st.file_uploader(
        "Accepted formats: .docx, .csv, .txt",
        type=["docx", "csv", "txt"],
    )
    if uploaded is None:
        st.info("Upload a transcript file to begin.")
        return

    data = uploaded.getvalue()
    try:
        segments = _extract_segments(uploaded.name, data)
    except TranscriptParseError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # pragma: no cover - surfaced to the user
        st.error(f"Could not read this file: {exc}")
        return

    fname_parse = parse_filename(uploaded.name, records)

    # Reset form defaults only when a genuinely new file is processed.
    new_key = f"{uploaded.name}:{len(data)}"
    if st.session_state.get("processed_key") != new_key:
        _seed_defaults(uploaded.name, fname_parse, segments, records)
        st.session_state["processed_key"] = new_key

    st.session_state["segments"] = segments
    st.session_state["fname_parse"] = fname_parse
    st.session_state["uploaded_name"] = uploaded.name

    st.success(f"Parsed **{uploaded.name}** — {len(segments)} turn(s) detected.")
    tokens = {
        "ConvID": fname_parse.conv_id or "—",
        "Locale": fname_parse.locale or "—",
        "Domain": fname_parse.domain or "—",
        "Sampling rate": fname_parse.sampling_rate or "—",
    }
    st.markdown("**Detected filename tokens**")
    st.table(pd.DataFrame([tokens]))
    for warning in fname_parse.warnings:
        st.warning(warning)

    if segments:
        st.button(
            "Continue to configuration →",
            type="primary",
            on_click=_goto,
            args=(1,),
        )
    else:
        st.error("No valid turns found. Check the transcript format.")


def _seed_defaults(name, fname_parse, segments, records) -> None:
    """Seed widget defaults once per uploaded file (never overwrites edits)."""
    locale_record = (
        language_by_locale(records, fname_parse.locale)
        if fname_parse.locale
        else None
    )
    st.session_state["cfg_conv_id"] = fname_parse.conv_id or ""
    st.session_state["cfg_language"] = (
        locale_record.display_name if locale_record else records[0].display_name
    )
    st.session_state["cfg_domain"] = fname_parse.domain or DOMAIN_CODES[0]
    st.session_state["cfg_sampling"] = fname_parse.sampling_rate or SAMPLING_RATES[0]
    st.session_state["cfg_recording_date"] = dt.date.today()
    st.session_state["cfg_script_path"] = name
    st.session_state["cfg_audio_path"] = ""
    st.session_state["cfg_master"] = DEFAULT_MASTER_CONVENTION_NAME
    st.session_state["cfg_annotator"] = ""
    st.session_state["cfg_cs_primary"] = DEFAULT_CS_RATIO_PRIMARY
    st.session_state["cfg_cs_secondary"] = DEFAULT_CS_RATIO_SECONDARY

    labels = detect_speakers(segments)
    for i, label in enumerate(labels):
        st.session_state.setdefault(f"spk_{label}_id", label)
        default_role = (
            "Agent" if i == 0 else "Customer" if i == 1 else SPEAKER_ROLES[0]
        )
        st.session_state.setdefault(f"spk_{label}_role", default_role)
        st.session_state.setdefault(f"spk_{label}_gender", "Unknown")
        st.session_state.setdefault(f"spk_{label}_age", "Unknown")
        st.session_state.setdefault(f"spk_{label}_nativity", "Unknown")


# --- Stage 2: Configure ----------------------------------------------------


def _selected_record(records):
    display = st.session_state.get("cfg_language", records[0].display_name)
    return next((r for r in records if r.display_name == display), records[0])


def _stage_configure(records) -> None:
    segments = st.session_state.get("segments")
    if not segments:
        st.info("Upload a transcript first.")
        return

    st.subheader("2. Conversation setup")
    left, right = st.columns(2)

    with left:
        st.text_input(
            "Transcript filename",
            value=st.session_state.get("uploaded_name", ""),
            disabled=True,
        )
        st.text_input("ConvID", key="cfg_conv_id")
        display_names = [r.display_name for r in records]
        st.selectbox("Language", display_names, key="cfg_language")
        st.selectbox("Domain", DOMAIN_CODES, key="cfg_domain")
        st.selectbox("Sampling Rate", SAMPLING_RATES, key="cfg_sampling")
        st.date_input("Recording Date", key="cfg_recording_date")

    record = _selected_record(records)
    with right:
        st.text_input("LangPair", value=record.lang_pair, disabled=True)
        st.text_input(
            "Primary Language Code",
            value=record.primary_language_code,
            disabled=True,
        )
        st.text_input(
            "Secondary Language Code",
            value=record.secondary_language_code,
            disabled=True,
        )
        st.text_input("Metadata Type", value=record.metadata_type, disabled=True)
        st.text_input("Annotator ID", key="cfg_annotator")
        c1, c2 = st.columns(2)
        c1.number_input("CS Ratio Primary", key="cfg_cs_primary", step=1)
        c2.number_input("CS Ratio Secondary", key="cfg_cs_secondary", step=1)

    with st.expander("Paths & convention"):
        st.text_input("Conversation Script Path", key="cfg_script_path")
        st.text_input("Audio File Path (optional)", key="cfg_audio_path")
        advanced = st.toggle("Advanced: edit Master Convention Name")
        st.text_input(
            "Master Convention Name",
            key="cfg_master",
            disabled=not advanced,
        )
        default_addendum = f"{record.primary_language_code}_2.0"
        st.session_state.setdefault("cfg_addendum", default_addendum)
        st.text_input("Custom Addendum", key="cfg_addendum")

    _render_speaker_cards(segments, record)

    st.divider()
    nav1, nav2 = st.columns([1, 1])
    nav1.button("← Back to upload", on_click=_goto, args=(0,))
    nav2.button(
        "Build raw metadata →",
        type="primary",
        on_click=_goto,
        args=(2,),
    )


def _render_speaker_cards(segments, record) -> None:
    st.subheader("Speaker mapping")
    labels = detect_speakers(segments)
    languages = (
        f"{record.primary_language_code}, {record.secondary_language_code}"
    )
    for label in labels:
        with st.container(border=True):
            st.markdown(f"**Transcript Speaker Label:** `{label}`")
            c1, c2, c3 = st.columns(3)
            c1.text_input("Output SpeakerID", key=f"spk_{label}_id")
            c2.selectbox("Role", SPEAKER_ROLES, key=f"spk_{label}_role")
            c3.selectbox("Gender", SPEAKER_GENDERS, key=f"spk_{label}_gender")
            c4, c5, c6 = st.columns(3)
            c4.text_input("Age Bucket", key=f"spk_{label}_age")
            c5.selectbox(
                "Nativity", SPEAKER_NATIVITIES, key=f"spk_{label}_nativity"
            )
            c6.text_input("Speaker Languages", value=languages, disabled=True)


# --- Config assembly -------------------------------------------------------


def _assemble_config(records) -> ConversationConfig:
    record = _selected_record(records)
    return ConversationConfig(
        conv_id=st.session_state.get("cfg_conv_id", "").strip(),
        lang_pair=record.lang_pair,
        primary_language_code=record.primary_language_code,
        secondary_language_code=record.secondary_language_code,
        metadata_type=record.metadata_type,
        domain=st.session_state.get("cfg_domain", ""),
        sampling_rate=st.session_state.get("cfg_sampling", ""),
        recording_date=str(st.session_state.get("cfg_recording_date", "")),
        conversation_script_path=st.session_state.get("cfg_script_path", ""),
        audio_file_path=st.session_state.get("cfg_audio_path", ""),
        master_convention_name=st.session_state.get("cfg_master", ""),
        custom_addendum=st.session_state.get("cfg_addendum", ""),
        annotator_id=st.session_state.get("cfg_annotator", "").strip(),
        cs_ratio_primary=st.session_state.get("cfg_cs_primary", 0),
        cs_ratio_secondary=st.session_state.get("cfg_cs_secondary", 0),
    )


def _assemble_speaker_map(segments) -> dict[str, SpeakerMapping]:
    mapping: dict[str, SpeakerMapping] = {}
    for label in detect_speakers(segments):
        mapping[label] = SpeakerMapping(
            transcript_label=label,
            speaker_id=st.session_state.get(f"spk_{label}_id", "").strip(),
            role=st.session_state.get(f"spk_{label}_role", ""),
            gender=st.session_state.get(f"spk_{label}_gender", ""),
            age_bucket=st.session_state.get(f"spk_{label}_age", ""),
            nativity=st.session_state.get(f"spk_{label}_nativity", ""),
        )
    return mapping


# --- Stage 3: Raw Metadata Preview -----------------------------------------


def _render_validation_panel(result) -> None:
    if result.errors:
        st.markdown("**Errors (must fix before generating)**")
        for err in result.errors:
            st.error(err)
    if result.warnings:
        st.markdown("**Warnings (export still allowed)**")
        for warn in result.warnings:
            st.warning(warn)
    if not result.errors and not result.warnings:
        st.success("No issues found in raw metadata checks.")


def _stage_preview(records) -> None:
    segments = st.session_state.get("segments")
    if not segments:
        st.info("Upload a transcript first.")
        return

    st.subheader("3. Raw Metadata Preview")
    config = _assemble_config(records)
    speaker_map = _assemble_speaker_map(segments)
    frame = build_rawmetadata(segments, config, speaker_map)
    result = validate_rawmetadata(frame, config, speaker_map, segments)

    st.markdown("**All 34 columns — scroll horizontally to review.**")
    st.dataframe(frame, use_container_width=True, hide_index=True)

    d1, d2 = st.columns(2)
    d1.download_button(
        "Download rawmetadata.xlsx",
        data=rawmetadata_to_xlsx_bytes(frame),
        file_name="rawmetadata.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    d2.download_button(
        "Download rawmetadata.csv",
        data=rawmetadata_to_csv_bytes(frame),
        file_name="rawmetadata.csv",
        mime="text/csv",
    )

    st.divider()
    _render_validation_panel(result)

    st.divider()
    nav1, nav2 = st.columns([1, 1])
    nav1.button("← Back to configuration", on_click=_goto, args=(1,))
    nav2.button(
        "Looks good — Generate Metadata & JSON",
        type="primary",
        disabled=result.has_blocking_errors,
        on_click=_goto,
        args=(3,),
    )
    if result.has_blocking_errors:
        st.caption("Resolve the blocking errors above to continue.")


# --- Stage 4: Generate (Milestone 3) ---------------------------------------


def _stage_generate(records) -> None:
    segments = st.session_state.get("segments")
    if not segments:
        st.info("Upload a transcript first.")
        return

    st.subheader("4. Generate Metadata & JSON")
    config = _assemble_config(records)
    speaker_map = _assemble_speaker_map(segments)

    raw_frame = build_rawmetadata(segments, config, speaker_map)
    meta_frame = build_metadata(segments, config, speaker_map)
    json_obj = build_conversation_json(segments, config, speaker_map)
    json_bytes = json_to_bytes(json_obj)

    result = run_full_validation(
        raw_frame, meta_frame, json_obj, json_bytes, config, speaker_map,
        segments,
    )

    _render_summary_cards(segments, meta_frame, result)
    st.divider()
    _render_validation_panel(result)
    st.divider()

    blocked = result.has_blocking_errors
    st.markdown("**Validated outputs**")
    if blocked:
        st.caption("Downloads are disabled until all blocking errors are fixed.")

    d1, d2 = st.columns(2)
    d1.download_button(
        "Download metadata.csv",
        data=metadata_to_csv_bytes(meta_frame),
        file_name="metadata.csv",
        mime="text/csv",
        disabled=blocked,
    )
    d2.download_button(
        f"Download {json_filename(config)}",
        data=json_bytes,
        file_name=json_filename(config),
        mime="application/json",
        disabled=blocked,
    )

    r1, r2 = st.columns(2)
    r1.download_button(
        "Download validation_report.json",
        data=validation_report_json_bytes(result.errors, result.warnings),
        file_name="validation_report.json",
        mime="application/json",
    )
    r2.download_button(
        "Download validation_report.txt",
        data=validation_report_txt_bytes(result.errors, result.warnings),
        file_name="validation_report.txt",
        mime="text/plain",
    )

    st.divider()
    st.button("← Back to preview", on_click=_goto, args=(2,))


def _render_summary_cards(segments, meta_frame, result) -> None:
    earliest = min(segments, key=lambda s: s.start_sec)
    latest = max(segments, key=lambda s: s.end_sec)
    duration = conversation_duration_sec(segments)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Segments", len(segments))
    c2.metric("Speakers", len(meta_frame))
    c3.metric("Start time", earliest.start_text)
    c4.metric("End time", latest.end_text)
    c5, c6, c7 = st.columns(3)
    c5.metric("Duration (sec)", f"{duration:g}")
    c6.metric("Warnings", len(result.warnings))
    c7.metric("Blocking errors", len(result.errors))


# --- Main ------------------------------------------------------------------


def main() -> None:
    _render_header()
    _init_state()
    records = load_language_records()

    with st.sidebar:
        st.markdown("### Project")
        st.caption(f"{len(records)} languages loaded from config.")
        st.button("Reset project", on_click=_reset_project)

    _render_stepper()

    stage = st.session_state["stage"]
    if stage == 0:
        _stage_upload(records)
    elif stage == 1:
        _stage_configure(records)
    elif stage == 2:
        _stage_preview(records)
    else:
        _stage_generate(records)


if __name__ == "__main__":
    main()
