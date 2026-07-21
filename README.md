# Transcript Metadata & JSON Generator

A local-first Python web app that converts a timestamped, multilingual
code-switching call-center transcript into delivery-ready metadata and JSON.

> Build status: **Milestone 1 (Foundation)** complete — repository structure,
> dependencies, language configuration, filename parser, and timestamp parser
> with tests. Ingestion, transformation, and the review UI arrive in later
> milestones.

## Prerequisites

- Python 3.11+

## Install

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Test

```bash
pytest
```

## Supported filename examples

The confirmed naming convention is:

```
<LangPair>_<Domain>_<SamplingRate>_<ConvID>.<ext>
```

Examples:

- `vi-VN_English_AIR_48kHz_Conv0347.json`
- `vi-VN_English_AIR_48Khz_Conv059.docx`

A compact run-together form (e.g. `vi-VNEnglishAIR48kHzConv0592.docx`) is
supported as a best-effort fallback.

## Supported transcript examples

Transcripts follow an SRT-like two-line pattern:

```
00:00:04,040 --> 00:00:07,400 [SPK001]
Xin chào, cảm ơn quý khách đã gọi đến bộ phận hỗ trợ hàng không.

00:00:08,280 --> 00:00:14,240 [SPK002]
Tôi rất bức bội. My flight to Paris was just cancelled...
```

## Project layout

```
config/languages.json   25 finalized language records (source of truth)
src/                     parsing, transformation, validation, export modules
tests/                   pytest suite
app.py                   Streamlit UI entry point
```
