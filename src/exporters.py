"""Export helpers producing in-memory bytes for download.

All exports return `bytes` so the Streamlit UI can offer downloads without
writing temporary files. XLSX forces the timestamp columns to Text so Excel
cannot corrupt a pasted timestamp into a time serial.
"""

from __future__ import annotations

import io
import json

import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from .constants import TEXT_FORMATTED_XLSX_COLUMNS

RAWMETADATA_SHEET_NAME = "rawmetadata"
_EXCEL_TEXT_FORMAT = "@"


def rawmetadata_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    """CSV bytes, UTF-8 with BOM for Excel compatibility."""
    return frame.to_csv(index=False).encode("utf-8-sig")


def metadata_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    """metadata.csv bytes, UTF-8 with BOM."""
    return frame.to_csv(index=False).encode("utf-8-sig")


def validation_report_json_bytes(errors: list[str], warnings: list[str]) -> bytes:
    """Serialize the validation report as JSON."""
    report = {
        "blocking_error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    return json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")


def validation_report_txt_bytes(errors: list[str], warnings: list[str]) -> bytes:
    """Serialize the validation report as human-readable text."""
    lines = [
        "Validation Report",
        "=================",
        f"Blocking errors: {len(errors)}",
        f"Warnings: {len(warnings)}",
        "",
        "Errors:",
    ]
    if errors:
        lines.extend(f"  - {e}" for e in errors)
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Warnings:")
    if warnings:
        lines.extend(f"  - {w}" for w in warnings)
    else:
        lines.append("  (none)")
    return ("\n".join(lines) + "\n").encode("utf-8")


def rawmetadata_to_xlsx_bytes(frame: pd.DataFrame) -> bytes:
    """XLSX bytes with worksheet `rawmetadata`; timestamp columns as Text.

    No formulas are written. Start/End time columns are formatted as Text and
    their cells stored as strings so Excel does not auto-convert them.
    """
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = RAWMETADATA_SHEET_NAME

    columns = list(frame.columns)
    worksheet.append(columns)

    text_col_indexes = {
        columns.index(name) + 1
        for name in TEXT_FORMATTED_XLSX_COLUMNS
        if name in columns
    }

    for _, row in frame.iterrows():
        worksheet.append([_cell_value(v) for v in row.tolist()])

    # Apply Text number format down each timestamp column (incl. header row).
    for col_index in text_col_indexes:
        letter = get_column_letter(col_index)
        for cell in worksheet[letter]:
            cell.number_format = _EXCEL_TEXT_FORMAT

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _cell_value(value: object) -> object:
    """Coerce NaN/None to empty string; leave other values intact."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return value
