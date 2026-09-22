"""Win32 WH_KEYBOARD_LL observation wrapper.

The Python process never installs a hook. It can launch the native
observer binary when running on Windows. On other operating systems the
source reports SKIPPED.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterator, Optional, Sequence, Union

from keylogix.constants import SOURCE_WIN32
from keylogix.observation.base import ObservationSource
from keylogix.observation.replay import ReplaySource
from keylogix.status import Result, Status


def default_observer_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "native" / "build" / "observer.exe"


class Win32HookSource(ObservationSource):
    name = SOURCE_WIN32

    def __init__(
        self,
        output_path: Union[str, Path],
        observer_path: Optional[Union[str, Path]] = None,
        duration_ms: Optional[int] = None,
        extra_args: Optional[Sequence[str]] = None,
        ids=None,
        clock=None,
    ) -> None:
        super().__init__(ids=ids, clock=clock)
        self.output_path = Path(output_path)
        self.observer_path = Path(observer_path) if observer_path else default_observer_path()
        self.duration_ms = duration_ms
        self.extra_args = list(extra_args or [])
        self._launch_status: Optional[Result] = None

    def availability(self) -> Result:
        if not sys.platform.startswith("win"):
            return Result.failure(
                Status.SKIPPED,
                "WH_KEYBOARD_LL requires Windows; current platform is {0}".format(
                    platform.system()
                ),
                details={"platform": sys.platform},
            )
        if not self.observer_path.is_file():
            return Result.failure(
                Status.UNREACHABLE,
                "observer binary not found: {0}".format(self.observer_path),
            )
        return Result.success({"observer": str(self.observer_path)})

    def start(self, session_id: Optional[str] = None) -> Result:
        started = super().start(session_id)
        if not started.ok:
            return started
        avail = self.availability()
        self._launch_status = avail
        if not avail.ok:
            return avail
        return started

    def events(self) -> Iterator[Result]:
        if self._session is None:
            yield Result.invalid("source not started")
            return
        avail = self._launch_status or self.availability()
        if not avail.ok:
            yield avail
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.observer_path),
            "--session",
            self._session.session_id,
            "--output",
            str(self.output_path),
        ]
        if self.duration_ms is not None:
            cmd.extend(["--duration-ms", str(int(self.duration_ms))])
        cmd.extend(self.extra_args)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=(self.duration_ms / 1000.0 + 30) if self.duration_ms else None,
                check=False,
            )
        except FileNotFoundError:
            yield Result.failure(
                Status.UNREACHABLE, "observer executable missing at launch"
            )
            return
        except subprocess.TimeoutExpired:
            yield Result.failure(Status.TIMEOUT, "observer timed out")
            return
        except OSError as exc:
            yield Result.failure(Status.PROVIDER_FAILURE, "observer launch failed: {0}".format(exc))
            return
        if proc.returncode != 0:
            yield Result.failure(
                Status.PROVIDER_FAILURE,
                "observer exited {0}: {1}".format(proc.returncode, (proc.stderr or "")[:500]),
                details={"returncode": proc.returncode},
            )
            return
        replay = ReplaySource(self.output_path, ids=self.ids, clock=self.clock)
        replay._session = self._session
        yield from replay.events()
