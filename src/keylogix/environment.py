"""Capture analysis-host environment for experiment records."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Any, Dict, Optional

from keylogix.constants import IMPLEMENTATION_VERSION, SCHEMA_ENVIRONMENT


def git_revision(cwd: Optional[str] = None) -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if head.returncode != 0:
            return "uncommitted"
        sha = head.stdout.strip() or "uncommitted"
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if dirty.returncode == 0 and dirty.stdout.strip():
            return sha + "-dirty"
        return sha
    except (OSError, subprocess.TimeoutExpired):
        return "uncommitted"


def collect_environment(repo_root: Optional[str] = None) -> Dict[str, Any]:
    return {
        "schema": SCHEMA_ENVIRONMENT,
        "implementation_version": IMPLEMENTATION_VERSION,
        "source_revision": git_revision(repo_root),
        "python_version": sys.version,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "executable": sys.executable,
        "cwd": os.getcwd(),
        "win32_hook_available": sys.platform.startswith("win"),
        "security_product": {
            "present": False,
            "identity": None,
            "version": None,
            "configuration": None,
            "notes": "Not measured on this host. Do not interpret as non-detection.",
        },
    }
