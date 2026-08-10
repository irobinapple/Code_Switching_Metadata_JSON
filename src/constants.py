"""Constant column lists, allowed values, and fixed schema literals.

Central source of truth for anything the PRD pins down exactly: the 34
rawmetadata columns, the 21 metadata columns, allowed dropdown values, and
the fixed JSON schema constants.
"""

from __future__ import annotations

from pathlib import Path

# --- Paths -----------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
LANGUAGES_JSON = CONFIG_DIR / "languages.json"

# --- rawmetadata: exactly 34 columns, in this exact order ------------------

RAWMETADATA_COLUMNS: list[str] = [
    "ConvID",
    "LangPair",
    "Primary_Language_Code",
    "Secondary_Language_Code",
    "Domain",
    "Sampling_Rate",
    "Recording_Date",
    "Conversation_Script_Path",
    "Audio_File_Path",
    "Master_Convention_Name",
    "Custom_Addendum",
    "Annotator_ID",
    "CS_Ratio_Primary",
    "CS_Ratio_Secondary",
    "Speaker_ID",
    "Speaker_Role",
    "Speaker_Role_Source",
    "Speaker_Gender",
    "Speaker_Gender_Source",
    "Speaker_Age_Bucket",
    "Speaker_Nativity",
    "Speaker_Nativity_Source",
    "Speaker_Languages",
    "Turn_No",
    "Segment_ID",
    "Start_Time_Sec",
    "End_Time_Sec",
    "Primary_Type",
    "Loudness_Level",
    "Segment_Primary_Language",
    "Segment_Languages",
    "Content_Text",
    "Transliteration_Text",
    "QC_Notes",
]

# --- metadata: exactly 21 columns, in this exact order ---------------------

METADATA_COLUMNS: list[str] = [
    "SNo",
    "FileName",
    "ConvID",
    "LangPair",
    "Speaker_ID",
    "Speaker_Role",
    "Speaker_Role_Source",
    "Speaker_Gender",
    "Speaker_Gender_Source",
    "Speaker_Age_Bucket",
    "Speaker_Nativity",
    "Speaker_Nativity_Source",
    "Domain",
    "Duration_Sec",
    "Number_of_Turns",
    "Sampling_Rate",
    "CS_Ratio_Primary",
    "CS_Ratio_Secondary",
    "Recording_Date",
    "Conversation_Script_Path",
    "Audio_File_Path",
]

# Columns stored as Text in XLSX so Excel does not corrupt pasted timestamps.
TEXT_FORMATTED_XLSX_COLUMNS: list[str] = ["Start_Time_Sec", "End_Time_Sec"]

# --- Allowed dropdown values -----------------------------------------------

DOMAIN_CODES: list[str] = [
    "AIR",
    "BANK",
    "FIN",
    "INS",
    "HEALTH",
    "IT",
    "ECOM",
    "TECHSUPPORT",
    "BILLING",
    "PRODUCT",
    "ACCOUNT",
]

SAMPLING_RATES: list[str] = ["8kHz", "16kHz", "48kHz", "Custom"]

# When a transcript has no speaker labels on its timestamp lines, turns are
# assigned to these default labels in alternating order (turn 1 -> first,
# turn 2 -> second, turn 3 -> first, ...). This matches 2-party call-center
# transcripts, where turns strictly alternate between agent and customer, and
# feeds the speaker-mapping UI so the first label defaults to Agent and the
# second to Customer.
DEFAULT_SPEAKER_LABELS: list[str] = ["Speaker 1", "Speaker 2"]

SPEAKER_ROLES: list[str] = ["Agent", "Customer", "No-Speaker"]
SPEAKER_GENDERS: list[str] = ["Male", "Female", "Unknown"]
SPEAKER_NATIVITIES: list[str] = ["Native", "Non-Native", "Unknown"]
SPEAKER_AGE_BUCKETS: list[str] = ["18-25", "26-40", "41-65", "65+"]

# Suggested annotator IDs. The dropdown also accepts a typed-in value, so an
# ID missing from this list can be used without a code change.
ANNOTATOR_IDS: list[str] = [
    "annot_001",
    "annot_002",
    "annot_003",
    "annot_004",
    "annot_005",
]

# --- Defaults --------------------------------------------------------------

DEFAULT_MASTER_CONVENTION_NAME = "awsTranscriptionGuidelines_en_US_3.2"
DEFAULT_PRIMARY_TYPE = "Speech"
DEFAULT_LOUDNESS_LEVEL = "Normal"
# Floats so the UI accepts fractional splits such as 60.8 / 39.2.
DEFAULT_CS_RATIO_PRIMARY = 70.0
DEFAULT_CS_RATIO_SECONDARY = 30.0
DEFAULT_DOMAIN_TOPIC = "Call-center"

# --- Fixed JSON schema constants -------------------------------------------

JSON_TYPE_NAME = "MULTI_SPEAKER_LONG_FORM_TRANSCRIPTION"
JSON_TYPE_VERSION = "3.2"
JSON_LOGIN_ENCRYPTED = "N/A"
JSON_DOMAIN_VERSION = "1.0"
JSON_DOMAIN_LITERAL = "Call-center"
ANNOTATOR_SOURCE = "Annotator"
NO_SPEAKER_ROLE = "No-Speaker"

# --- Metadata type sentinels -----------------------------------------------

METADATA_TYPE_TRANSLITERATION = "Transliteration"
METADATA_TYPE_NON_TRANSLITERATION = "Non-Transliteration"
