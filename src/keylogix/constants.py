"""Shared constants. Keep vocabularies small and documented."""

from __future__ import annotations

IMPLEMENTATION_VERSION = "0.1.0"

SCHEMA_RAW = "keylogix.raw_observation.v1"
SCHEMA_NORMALIZED = "keylogix.normalized_event.v1"
SCHEMA_CLASSIFICATION = "keylogix.classification.v1"
SCHEMA_ANALYSIS = "keylogix.behavioral_analysis.v1"
SCHEMA_EVIDENCE = "keylogix.evidence.v1"
SCHEMA_EXPERIMENT = "keylogix.experiment.v1"
SCHEMA_OBSERVABILITY = "keylogix.observability.v1"
SCHEMA_ENVIRONMENT = "keylogix.environment.v1"
SCHEMA_SESSION = "keylogix.session.v1"

SOURCE_SYNTHETIC = "synthetic"
SOURCE_WIN32 = "win32_llhook"
SOURCE_UNKNOWN = "unknown"
SOURCE_VOCABULARY = frozenset({SOURCE_SYNTHETIC, SOURCE_WIN32, SOURCE_UNKNOWN})

EVENT_KEY_DOWN = "KEY_DOWN"
EVENT_KEY_UP = "KEY_UP"
EVENT_TYPES = frozenset({EVENT_KEY_DOWN, EVENT_KEY_UP})

# Win32 message names preserved on raw observations.
RAW_WM_KEYDOWN = "WM_KEYDOWN"
RAW_WM_KEYUP = "WM_KEYUP"
RAW_WM_SYSKEYDOWN = "WM_SYSKEYDOWN"
RAW_WM_SYSKEYUP = "WM_SYSKEYUP"

LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10
LLKHF_ALTDOWN = 0x20
LLKHF_UP = 0x80

CAT_UNKNOWN = "unknown"
CAT_ORDINARY = "ordinary"
CAT_MODIFIER = "modifier"
CAT_NAVIGATION = "navigation"
CAT_CONTROL = "control"
CAT_FUNCTION = "function"
CAT_LOCK = "lock"
CAT_NUMPAD = "numpad"
CAT_OEM = "oem"

CATEGORY_IDS = {
    CAT_UNKNOWN: 0,
    CAT_ORDINARY: 1,
    CAT_MODIFIER: 2,
    CAT_NAVIGATION: 3,
    CAT_CONTROL: 4,
    CAT_FUNCTION: 5,
    CAT_LOCK: 6,
    CAT_NUMPAD: 7,
    CAT_OEM: 8,
}
ID_TO_CATEGORY = {v: k for k, v in CATEGORY_IDS.items()}

SEQ_EMPTY = "empty"
SEQ_TEXT_ORIENTED = "text_oriented"
SEQ_SPECIAL = "special_key_sequence"
SEQ_CHORD = "modifier_chord"
SEQ_MIXED = "mixed"

KIND_RAW = "raw_observation"
KIND_NORMALIZED = "normalized_observation"
KIND_DERIVED = "derived_interpretation"
KIND_HEURISTIC = "heuristic_classification"
KIND_BEHAVIORAL = "behavioral_analysis"

PRESENCE_OBSERVED = "observed"
PRESENCE_UNAVAILABLE = "unavailable"
PRESENCE_NOT_APPLICABLE = "not_applicable"
PRESENCE_DERIVED = "derived"

METHOD_DETERMINISTIC = "deterministic"
METHOD_HEURISTIC = "heuristic"

# Behavioral research defaults (not malice thresholds).
BURST_MAX_INTERARRIVAL_NS = 50_000_000
BURST_MIN_EVENTS = 5
REPEAT_MIN_COUNT = 3
REPEAT_MAX_INTERARRIVAL_NS = 100_000_000
TEXT_ORIENTED_FRACTION = 0.70
SPECIAL_SEQUENCE_FRACTION = 0.70
HEURISTIC_CONFIDENCE = 0.7

NATIVE_MAX_CAPACITY = 1_000_000
KLX_BUF_MAGIC = 0x314C4B58
KLX_OK = 0
KLX_ERR_NULL = -1
KLX_ERR_INVALID = -2
KLX_ERR_NOSPACE = -3
KLX_ERR_OVERFLOW = -4
KLX_ERR_MAGIC = -5

MOD_SHIFT = 1
MOD_CTRL = 2
MOD_ALT = 4
MOD_WIN = 8
