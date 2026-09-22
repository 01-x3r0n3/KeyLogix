"""Observation sources.

A source either produces raw observations or returns an explicit status.
Sources never normalize, classify, or analyze.
"""

from __future__ import annotations

from keylogix.observation.base import ObservationSource, Session
from keylogix.observation.replay import ReplaySource
from keylogix.observation.synthetic import SyntheticSource, script_from_keys
from keylogix.observation.win32 import Win32HookSource

__all__ = [
    "ObservationSource",
    "Session",
    "ReplaySource",
    "SyntheticSource",
    "Win32HookSource",
    "script_from_keys",
]
