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
    ANNOTATOR_IDS,
    CONVERSATION_TYPE_1,
    CONVERSATION_TYPE_2,
    CONVERSATION_TYPES,
    DEFAULT_CS_RATIO_PRIMARY,
    DEFAULT_MASTER_CONVENTION_NAME,
    DEFAULT_SPEAKER_LABELS,
    DOMAIN_CODES,
    SAMPLING_RATES,
    SPEAKER_AGE_BUCKETS,
    SPEAKER_COUNT_BY_TYPE,
    SPEAKER_GENDERS,
    SPEAKER_NATIVITIES,
    SPEAKER_ROLES,
)
from src.exporters import (
    metadata_csv_filename,
    metadata_to_csv_bytes,
    rawmetadata_csv_filename,
    rawmetadata_to_csv_bytes,
    rawmetadata_to_xlsx_bytes,
    rawmetadata_xlsx_filename,
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
    build_filename_stem,
    build_metadata,
    build_rawmetadata,
    conversation_duration_sec,
    role_for_label,
)
from src.validators import run_full_validation, validate_rawmetadata

STAGES = [
    "Upload",
    "Configure",
    "Raw Metadata Preview",
    "Generate Metadata & JSON",
]

# Suffix marking a read-only widget whose value is derived fresh on every run
# rather than held in session state (see _persist_widget_state).
DERIVED_DISPLAY_SUFFIX = "_langs_display"


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


# Colors come from Streamlit's active theme (see .streamlit/config.toml), not
# hardcoded values, so text and surfaces always stay legible together.
_CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1200px; }
h1 { font-size: 1.6rem !important; font-weight: 700; }
.stButton > button { border-radius: 6px; }
div[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.25);
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
}
</style>
"""


def _render_header() -> None:
    st.set_page_config(
        page_title="Ace - CSMJ Tool",
        layout="wide",
        page_icon="🗂️",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title("Ace - CSMJ Tool")
    st.caption(
        "Convert a timestamped, multilingual code-switching transcript into "
        "rawmetadata, metadata, and per-conversation JSON."
    )


def _render_sidebar_summary(records) -> None:
    """Sticky live summary of derived, read-only values."""
    segments = st.session_state.get("segments")
    if not segments:
        st.caption("Upload a transcript to see a live summary.")
        return
    record = _selected_record(records)
    st.markdown("#### Summary")
    rows = {
        "ConvID": st.session_state.get("cfg_conv_id", "—") or "—",
        "LangPair": record.lang_pair,
        "Primary": record.primary_language_code,
        "Secondary": record.secondary_language_code,
        "Metadata type": record.metadata_type,
        "Turns": len(segments),
        "Speakers": len(detect_speakers(segments)),
    }
    for key, value in rows.items():
        st.markdown(f"**{key}:** `{value}`")


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


def _conversation_type() -> str:
    return st.session_state.get("cfg_conv_type", CONVERSATION_TYPE_1)


def _expected_speaker_count() -> int:
    return SPEAKER_COUNT_BY_TYPE[_conversation_type()]


def _stage_upload(records) -> None:
    st.subheader("1. Upload a transcript")

    st.radio(
        "Conversation type",
        CONVERSATION_TYPES,
        key="cfg_conv_type",
        horizontal=True,
        help=(
            "Type 1 is a standard Agent/Customer call. Type 2 adds a "
            "Translator. This is kept for the rest of the session — change "
            "it here or in the sidebar."
        ),
    )
    expected = _expected_speaker_count()
    st.caption(
        f"Transcripts must contain exactly **{expected} speakers**."
    )

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

    # A filename that breaks the client naming convention is a hard stop: the
    # name itself ships as Conversation_Script_Path, so it must be corrected
    # at the source rather than worked around here.
    if fname_parse.is_blocked:
        for message in fname_parse.errors:
            st.error(message)
        if fname_parse.suggested_filename:
            st.markdown("**Rename the file to:**")
            st.code(fname_parse.suggested_filename, language=None)
        st.info(
            "Rename the file on your computer, then upload it again. "
            "Client deliveries must use a hyphen inside the language code "
            "(e.g. `fr-FR`), not an underscore."
        )
        return

    detected = detect_speakers(segments)
    unlabeled = bool(detected) and set(detected) <= set(DEFAULT_SPEAKER_LABELS)
    conv_type = _conversation_type()

    # A 3-speaker call cannot be attributed from an unlabeled transcript: the
    # translator interleaves rather than following a fixed rotation, so any
    # guess would mislabel most turns.
    if unlabeled and conv_type == CONVERSATION_TYPE_2:
        st.error(
            "This transcript has no speaker labels, which cannot be used for "
            f"{CONVERSATION_TYPE_2}. Add a label to each turn — "
            "`[Agent]`, `[Customer]` or `[Translator]` — then upload again."
        )
        st.code(
            "00:00:03,060 --> 00:00:04,520 [Agent]\n"
            "Thank you for calling Global IT.",
            language=None,
        )
        return

    if len(detected) != expected:
        st.error(
            f"{conv_type} expects **{expected} speakers**, but this "
            f"transcript has **{len(detected)}** "
            f"({', '.join(detected) if detected else 'none'}). Check the "
            "transcript, or switch the conversation type above."
        )
        return

    # Only a transcript that passed every check is committed to the session.
    new_key = f"{uploaded.name}:{len(data)}:{conv_type}"
    if st.session_state.get("processed_key") != new_key:
        _seed_defaults(uploaded.name, fname_parse, segments, records)
        st.session_state["processed_key"] = new_key

    st.session_state["segments"] = segments
    st.session_state["fname_parse"] = fname_parse
    st.session_state["uploaded_name"] = uploaded.name

    st.success(f"Parsed **{uploaded.name}** — {len(segments)} turn(s) detected.")

    if unlabeled:
        st.info(
            "This transcript had no speaker labels, so turns were assigned to "
            f"**{'** / **'.join(detected)}** in alternating order. Please "
            "confirm the Role (Agent / Customer) for each speaker on the next "
            "step."
        )
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
    # None so the Annotator ID selectbox opens on its placeholder rather than
    # silently pre-selecting someone.
    st.session_state["cfg_annotator"] = None
    st.session_state["cfg_cs_primary"] = DEFAULT_CS_RATIO_PRIMARY
    # cfg_cs_secondary is not seeded: the secondary ratio is always derived
    # from the primary (see secondary_cs_ratio).

    labels = detect_speakers(segments)
    conv_type = _conversation_type()
    for i, label in enumerate(labels):
        st.session_state.setdefault(f"spk_{label}_id", label)
        # Transcripts usually name the role in the label itself ([Translator]),
        # which beats guessing by position — the translator is often speaker 2.
        st.session_state.setdefault(
            f"spk_{label}_role", role_for_label(label, i, conv_type)
        )
        st.session_state.setdefault(f"spk_{label}_gender", "Unknown")
        st.session_state.setdefault(f"spk_{label}_age", SPEAKER_AGE_BUCKETS[1])
        st.session_state.setdefault(f"spk_{label}_nativity", "Unknown")


# --- Stage 2: Configure ----------------------------------------------------


def _selected_record(records):
    display = st.session_state.get("cfg_language", records[0].display_name)
    return next((r for r in records if r.display_name == display), records[0])


def secondary_cs_ratio() -> float:
    """Secondary CS ratio, always 100 minus the primary."""
    primary = float(
        st.session_state.get("cfg_cs_primary", DEFAULT_CS_RATIO_PRIMARY)
    )
    return round(100.0 - primary, 4)


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
        st.text_input(
            "ConvID",
            key="cfg_conv_id",
            help="Parsed from the filename (e.g. Conv0347). Edit if wrong.",
        )
        display_names = [r.display_name for r in records]
        st.selectbox(
            "Language",
            display_names,
            key="cfg_language",
            help="Drives LangPair and all derived language codes.",
        )
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
        st.selectbox(
            "Annotator ID",
            ANNOTATOR_IDS,
            key="cfg_annotator",
            accept_new_options=True,
            help="Pick an ID, or type a new one if yours is not listed. "
            "Required — blocks generation while empty.",
        )
        c1, c2 = st.columns(2)
        c1.number_input(
            "CS Ratio Primary",
            key="cfg_cs_primary",
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            format="%.1f",
            help="Decimals allowed (e.g. 60.8). The secondary ratio is "
            "calculated automatically as 100 minus this value.",
        )
        # Derived, never typed: removes any chance of the pair not totalling 100.
        c2.number_input(
            "CS Ratio Secondary",
            value=secondary_cs_ratio(),
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            format="%.1f",
            disabled=True,
            help="Calculated as 100 minus the primary ratio.",
        )

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
            c4.selectbox(
                "Age Bucket", SPEAKER_AGE_BUCKETS, key=f"spk_{label}_age"
            )
            c5.selectbox(
                "Nativity", SPEAKER_NATIVITIES, key=f"spk_{label}_nativity"
            )
            c6.text_input(
                "Speaker Languages",
                value=languages,
                disabled=True,
                key=f"spk_{label}{DERIVED_DISPLAY_SUFFIX}",
            )


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
        annotator_id=(st.session_state.get("cfg_annotator") or "").strip(),
        cs_ratio_primary=float(st.session_state.get("cfg_cs_primary", 0.0)),
        cs_ratio_secondary=secondary_cs_ratio(),
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
    st.dataframe(frame, hide_index=True)

    stem = build_filename_stem(config)
    d1, d2 = st.columns(2)
    d1.download_button(
        f"Download {rawmetadata_xlsx_filename(stem)}",
        data=rawmetadata_to_xlsx_bytes(frame),
        file_name=rawmetadata_xlsx_filename(stem),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    d2.download_button(
        f"Download {rawmetadata_csv_filename(stem)}",
        data=rawmetadata_to_csv_bytes(frame),
        file_name=rawmetadata_csv_filename(stem),
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

    stem = build_filename_stem(config)
    d1, d2 = st.columns(2)
    d1.download_button(
        f"Download {metadata_csv_filename(stem)}",
        data=metadata_to_csv_bytes(meta_frame),
        file_name=metadata_csv_filename(stem),
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


def _persist_widget_state() -> None:
    """Pin form values so Streamlit keeps them across stage navigation.

    Streamlit drops a keyed widget's value from session_state on runs where
    that widget is not rendered. Re-assigning each form key to itself at the
    top of every run (before any widget is created) prevents that, so values
    entered on the Configure stage survive on Preview/Generate.
    """
    for key in list(st.session_state.keys()):
        if not key.startswith(("cfg_", "spk_")):
            continue
        # Read-only derived fields (e.g. Speaker Languages) are rebuilt from
        # the current language on every run and passed as an explicit value.
        # Pinning them too would make Streamlit warn that the widget has both
        # a default value and a Session State entry.
        if key.endswith(DERIVED_DISPLAY_SUFFIX):
            continue
        st.session_state[key] = st.session_state[key]


def main() -> None:
    _render_header()
    _init_state()
    _persist_widget_state()
    records = load_language_records()

    with st.sidebar:
        st.markdown("### Project")
        st.caption(f"{len(records)} languages loaded from config.")
        # Read-only here: the type is chosen on the Upload stage, because
        # changing it means the transcript has to be re-checked anyway.
        st.markdown(f"**Conversation type:** `{_conversation_type()}`")
        st.button(
            "Change conversation type",
            on_click=_goto,
            args=(0,),
            help="Takes you back to Upload, where the type is set.",
        )
        _render_sidebar_summary(records)
        st.divider()
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
