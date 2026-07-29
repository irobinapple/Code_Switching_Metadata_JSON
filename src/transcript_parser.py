"""Transcript ingestion and parsing.

Handles DOCX/TXT/CSV ingestion and the real two-line SRT-style transcript
format:

    00:00:04,040 --> 00:00:07,400 [SPK001]
    Xin chào, cảm ơn quý khách đã gọi đến bộ phận hỗ trợ hàng không.

Line 1 is `<start> --> <end> [<speaker>]`; subsequent non-timestamp lines are
appended to that segment's content (single-space separated).

The speaker label is optional. Some transcripts have no diarization labels at
all — just a bare timestamp line:

    00:00:04,880 --> 00:00:07,980
    Chào mừng quý khách đến với dịch vụ hỗ trợ hàng không toàn cầu ạ.

For those turns the speaker is filled from `DEFAULT_SPEAKER_LABELS` in
alternating order (turn 1 -> first label, turn 2 -> second, and so on), which
matches 2-party call-center calls where turns alternate between the two
speakers.
"""

from __future__ import annotations

import io
import re

import pandas as pd

from .constants import DEFAULT_SPEAKER_LABELS
from .models import TranscriptSegment
from .timestamp_parser import TimestampError, parse_timestamp_to_seconds

ARROW = "-->"

# A timestamp line: <start> --> <end> with an OPTIONAL trailing speaker
# (bracketed or bare). The speaker group is None when the line is just a
# timestamp, e.g. "00:00:04,880 --> 00:00:07,980" (with or without trailing
# whitespace).
_TS_LINE_RE = re.compile(
    r"^\s*(?P<start>[\d:,\.]+)\s*-->\s*(?P<end>[\d:,\.]+)\s*(?P<speaker>\S.*?)?\s*$"
)


class TranscriptParseError(ValueError):
    """Raised when a line that looks like a timestamped turn cannot be parsed."""


def _clean_speaker(raw: str) -> str:
    """Strip surrounding brackets/whitespace from a speaker label."""
    return raw.strip().strip("[]").strip()


def parse_transcript_text(text: str) -> list[TranscriptSegment]:
    """Parse raw transcript text into ordered segments.

    A line containing the `-->` arrow is treated as a timestamp line and must
    parse fully, otherwise a TranscriptParseError is raised. The speaker label
    is optional; turns without one are assigned an alternating default speaker
    (see module docstring). Non-timestamp, non-blank lines extend the current
    segment's content.
    """
    segments: list[TranscriptSegment] = []
    current: TranscriptSegment | None = None
    content_parts: list[str] = []
    unlabeled_turns = 0  # count of turns that arrived without a speaker label

    def flush() -> None:
        nonlocal current, content_parts
        if current is not None:
            current.content_text = " ".join(
                part.strip() for part in content_parts if part.strip()
            )
            segments.append(current)
        current = None
        content_parts = []

    for line in text.splitlines():
        if ARROW in line:
            match = _TS_LINE_RE.match(line)
            if not match:
                raise TranscriptParseError(
                    f"This line looks like a timestamped turn but could not be "
                    f"read: {line.strip()!r}. Expected "
                    f"'<start> --> <end> [SPK]'."
                )
            flush()
            start_text = match.group("start").strip()
            end_text = match.group("end").strip()
            raw_speaker = match.group("speaker")
            speaker = _clean_speaker(raw_speaker) if raw_speaker else ""
            if not speaker:
                # No speaker label on this turn: assign an alternating default
                # so unlabeled 2-party transcripts still get per-speaker output.
                speaker = DEFAULT_SPEAKER_LABELS[
                    unlabeled_turns % len(DEFAULT_SPEAKER_LABELS)
                ]
                unlabeled_turns += 1
            try:
                start_sec = parse_timestamp_to_seconds(start_text)
                end_sec = parse_timestamp_to_seconds(end_text)
            except TimestampError as exc:
                raise TranscriptParseError(
                    f"Could not read a timestamp on line "
                    f"{line.strip()!r}: {exc}"
                ) from exc
            current = TranscriptSegment(
                speaker_label=speaker,
                start_text=start_text,
                end_text=end_text,
                start_sec=start_sec,
                end_sec=end_sec,
                content_text="",
            )
        else:
            if current is not None and line.strip():
                content_parts.append(line)

    flush()
    return segments


def detect_speakers(segments: list[TranscriptSegment]) -> list[str]:
    """Return unique speaker labels in first-appearance order."""
    seen: list[str] = []
    for seg in segments:
        if seg.speaker_label not in seen:
            seen.append(seg.speaker_label)
    return seen


# --- Ingestion -------------------------------------------------------------


def extract_text_from_docx(data: bytes) -> str:
    """Extract paragraph text from a DOCX file's bytes."""
    from docx import Document  # imported lazily to keep import cost local

    document = Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def extract_text_from_txt(data: bytes) -> str:
    """Decode TXT bytes as UTF-8 (tolerating a BOM)."""
    return data.decode("utf-8-sig")


def parse_csv_full_line_column(
    frame: pd.DataFrame, transcript_column: str
) -> list[TranscriptSegment]:
    """Parse a CSV whose one column holds full transcript lines/blocks."""
    text = "\n".join(str(v) for v in frame[transcript_column].tolist())
    return parse_transcript_text(text)


def parse_csv_mapped(
    frame: pd.DataFrame,
    start_column: str,
    end_column: str,
    speaker_column: str,
    content_column: str,
) -> list[TranscriptSegment]:
    """Parse a CSV with explicit start/end/speaker/content columns."""
    segments: list[TranscriptSegment] = []
    for _, row in frame.iterrows():
        start_text = str(row[start_column]).strip()
        end_text = str(row[end_column]).strip()
        speaker = _clean_speaker(str(row[speaker_column]))
        content = str(row[content_column]).strip()
        try:
            start_sec = parse_timestamp_to_seconds(start_text)
            end_sec = parse_timestamp_to_seconds(end_text)
        except TimestampError as exc:
            raise TranscriptParseError(
                f"Could not read a timestamp for speaker {speaker!r}: {exc}"
            ) from exc
        segments.append(
            TranscriptSegment(
                speaker_label=speaker,
                start_text=start_text,
                end_text=end_text,
                start_sec=start_sec,
                end_sec=end_sec,
                content_text=content,
            )
        )
    return segments


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Read CSV bytes into a DataFrame, preserving strings and BOM handling."""
    return pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
