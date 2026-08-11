# Ace - CSMJ Tool

*(Code-Switching Metadata & JSON tool.)*

A local-first Python web app that converts a timestamped, multilingual
code-switching call-center transcript into delivery-ready outputs:

- `rawmetadata.xlsx` and `rawmetadata.csv` (34 columns)
- `metadata.csv` (21 columns)
- one UTF-8 JSON file per conversation
- `validation_report.json` and `validation_report.txt`

The workflow is a deliberate two-stage review: you inspect and download the
**raw metadata** first, then explicitly trigger **metadata + JSON** generation.
No ZIP bundling, no multi-tab preview — each file downloads individually and
downloads stay disabled until there are zero blocking errors.

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

Then open the URL Streamlit prints (default http://localhost:8501).

## Test

```bash
pytest
```

## How to use

1. **Upload** a `.docx`, `.csv`, or `.txt` transcript. The app shows the
   filename, detected filename tokens, and the parsed turn count.
2. **Configure** the conversation. Language selection is fully driven by
   `config/languages.json` and derives LangPair, primary/secondary codes, and
   metadata type. Filename tokens pre-fill fields but never overwrite an edit
   you have made. Map each detected speaker (first → Agent, second → Customer
   by default; change anything).
3. **Raw Metadata Preview** — review the single 34-column table, download
   `rawmetadata.xlsx` / `rawmetadata.csv`, and read the scoped validation
   panel. Click **"Looks good — Generate Metadata & JSON"** to continue.
4. **Generate Metadata & JSON** — summary cards, the full validation panel,
   and downloads for `metadata.csv`, the per-conversation JSON, and both
   validation reports.

## Sharing with non-technical associates

The tool runs entirely on the associate's own machine — no server, no account,
and uploaded transcripts never leave their computer. The first launch installs
a self-contained runtime (`uv`, which also fetches the correct Python
automatically) plus dependencies — a couple of minutes, one time only. The
browser then opens at http://localhost:8501; later launches start almost
instantly. Plain-language steps for associates are in **`HOW_TO_RUN.txt`**.

There are two ways to distribute, depending on whether you want auto-updates.

### Recommended: auto-updating copy (best for frequent changes)

Send associates the single file **`Get-Ace-CSMJ.bat`**. They double-click it; it
downloads the whole tool into a `Code_Switching_Metadata_JSON` folder. From then
on, **`Ace-CSMJ.bat` pulls your latest changes automatically on every launch**
(and only re-installs dependencies when something actually changed, so normal
launches stay fast and work offline). `Get-Ace-CSMJ.bat` auto-installs Git via
winget if it's missing (falling back to a manual link only if winget isn't
available); on a private repo the first download shows a one-time GitHub
sign-in.

**Windows**

- `Get-Ace-CSMJ.bat` — one-time downloader (the only file you need to send)
- `Ace-CSMJ.bat` — start the app (auto-updates first)
- `Update.bat` — pull the latest without starting the app
- `CreateDesktopShortcut.bat` — put an "Ace - CSMJ" icon on the Desktop

**macOS / Linux** — same flow, same auto-update:

- `Get-Ace-CSMJ.command` — one-time downloader. Offers to install Apple's
  Developer Tools if git is missing, and clears the `com.apple.quarantine`
  tag so the launcher opens normally.
- `Ace-CSMJ.command` — start the app (auto-updates first)

On macOS the first double-click of a downloaded `.command` is blocked by
Gatekeeper: right-click → **Open** → **Open** once, and it runs normally
from then on. Drag `Ace-CSMJ.command` to the Dock for one-click launching.

### Simple: static copy (no auto-update)

Click **Code → Download ZIP** on GitHub (or copy the folder to a USB/drive),
keep all files together, and have them double-click `Ace-CSMJ.bat`
(macOS/Linux: `Ace-CSMJ.command`, first time right-click → Open). To push an
update, re-share the folder.

To stop the app, close the launcher window; to start again, double-click the
launcher (or the desktop shortcut).

## Supported filename examples

Confirmed naming convention:

```
<LangPair>_<Domain>_<SamplingRate>_<ConvID>.<ext>
```

Examples:

- `vi-VN_English_AIR_48kHz_Conv0347.json`
- `vi-VN_English_AIR_48Khz_Conv059.docx`

Parsing splits on underscores and matches tokens against the known domain
codes, sampling-rate patterns (`8kHz`/`16kHz`/`48kHz`, case-insensitive,
`Khz` accepted), the `Conv\d+` pattern, and the locales in
`config/languages.json`. A compact run-together form
(e.g. `vi-VNEnglishAIR48kHzConv0592.docx`) is supported as a best-effort
fallback. Undetected tokens are left blank with a non-blocking warning —
never guessed.

The language code must use a **hyphen** (`fr-FR`), per the client convention.
A filename that writes it with an underscore (`fr_FR_English_INS_16KHz_...`)
is **rejected**: the app shows the exact corrected filename to rename to and
will not process the file until it does. The uploaded name ships as
`Conversation_Script_Path`, so it has to be right at the source.

## Supported transcript examples

Transcripts follow an SRT-like two-line pattern — a timestamp+speaker line,
then the content on the following line(s):

```
00:00:04,040 --> 00:00:07,400 [SPK001]
Xin chào, cảm ơn quý khách đã gọi đến bộ phận hỗ trợ hàng không.

00:00:08,280 --> 00:00:14,240 [SPK002]
Tôi rất bức bội. My flight to Paris was just cancelled and no one told me.
```

- Content spanning multiple lines is joined with a single space until the next
  timestamp line.
- Timestamps accept `HH:MM:SS,mmm` (the real SRT comma-decimal form),
  `HH:MM:SS.mmm`, `M:SS.mmm`, and plain seconds. Source timestamp text is
  preserved as-is in rawmetadata; parsed seconds are used in JSON.
- CSV input is supported either as one full-transcript-line column or via a
  column-mapping UI (start / end / speaker / content).

## Output notes

- rawmetadata `Start_Time_Sec` / `End_Time_Sec` are stored as **Text** in the
  XLSX so Excel cannot corrupt a pasted timestamp into a time serial.
- `metadata` duration is conversation-level (same on every speaker row);
  `Number_of_Turns` is per-speaker only.
- JSON uses `ensure_ascii=False` (multilingual text preserved),
  `domainInfo.domainList` is an **array** of one object, and segments are
  sorted ascending by numeric `start`. The lowercase `transliteration` key is
  **omitted entirely** for `Non-Transliteration` languages and present for
  `Transliteration` ones. `speakerDominantVarieties` is an array
  of one object (`languageLocale` + empty variety/influence arrays); a
  speaker's `languages` is `[primary, secondary]`, or `[]` for a No-Speaker
  (whose gender/age/nativity are `NA`); any No-Speaker is listed first.
  Matches the client's V1 schema. The secondary (English) code is bare `en`
  for every locale except the Indian ones (Hindi, Tamil), which use `en_IN`.
- `QC_Notes` never appears in `metadata.csv` or the JSON.

## Project layout

```
app.py                    Streamlit UI entry point (UI only)
requirements.txt
config/languages.json     32 language records (source of truth)
src/
  constants.py            column lists, allowed values, schema literals
  models.py               dataclasses + language config loading
  filename_parser.py      filename token parsing
  timestamp_parser.py     parse_timestamp_to_seconds
  transcript_parser.py    DOCX/TXT/CSV ingestion + two-line SRT parsing
  transformers.py         rawmetadata + metadata builders
  json_builder.py         per-conversation JSON assembly
  validators.py           quality gates + mandatory automated checks
  exporters.py            xlsx/csv/json/report byte exports
tests/                    pytest suite (+ VI-EN fixture transcript)
```
