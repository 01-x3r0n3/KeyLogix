"""JSON / JSONL persistence. Failures are PROVIDER_FAILURE, not empty success."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional, TypeVar

from keylogix.status import Result, Status

T = TypeVar("T")


def ensure_dir(path: Path) -> Result:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return Result.success(str(path))
    except OSError as exc:
        return Result.failure(Status.PROVIDER_FAILURE, "cannot create directory: {0}".format(exc))


def atomic_write_text(path: Path, text: str) -> Result:
    directory = path.parent
    made = ensure_dir(directory)
    if not made.ok:
        return made
    tmp_name = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=".klx-", suffix=".tmp", dir=str(directory))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        tmp_name = None
        return Result.success(str(path))
    except OSError as exc:
        return Result.failure(Status.PROVIDER_FAILURE, "write failed: {0}".format(exc))
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "value"):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_json(path: Path, obj: Any) -> Result:
    try:
        text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=_json_default) + "\n"
    except (TypeError, ValueError) as exc:
        return Result.failure(Status.INVALID_INPUT, "json encode failed: {0}".format(exc))
    return atomic_write_text(path, text)


def write_jsonl(path: Path, objects: Iterable[Any]) -> Result:
    directory = path.parent
    made = ensure_dir(directory)
    if not made.ok:
        return made
    count = 0
    tmp_name = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=".klx-", suffix=".tmp", dir=str(directory))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for obj in objects:
                handle.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=_json_default))
                handle.write("\n")
                count += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        tmp_name = None
        if count == 0:
            return Result(Status.SUCCESS_NO_DATA, str(path), "wrote empty jsonl")
        return Result.success(str(path), "wrote {0} records".format(count))
    except OSError as exc:
        return Result.failure(Status.PROVIDER_FAILURE, "jsonl write failed: {0}".format(exc))
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def read_json(path: Path) -> Result:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Result.failure(Status.UNREACHABLE, "file not found: {0}".format(path))
    except OSError as exc:
        return Result.failure(Status.PROVIDER_FAILURE, "read failed: {0}".format(exc))
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return Result.failure(Status.INVALID_INPUT, "invalid json: {0}".format(exc))
    if obj is None:
        return Result.no_data("json null")
    return Result.success(obj)


def iter_jsonl(path: Path) -> Iterator[Result]:
    try:
        handle = path.open("r", encoding="utf-8")
    except FileNotFoundError:
        yield Result.failure(Status.UNREACHABLE, "file not found: {0}".format(path))
        return
    except OSError as exc:
        yield Result.failure(Status.PROVIDER_FAILURE, "read failed: {0}".format(exc))
        return
    with handle:
        any_line = False
        for lineno, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            any_line = True
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                yield Result.failure(
                    Status.INVALID_INPUT,
                    "invalid jsonl at line {0}: {1}".format(lineno, exc),
                    details={"line": lineno},
                )
                continue
            if not isinstance(obj, dict):
                yield Result.failure(
                    Status.INVALID_INPUT,
                    "jsonl line {0} is not an object".format(lineno),
                    details={"line": lineno},
                )
                continue
            yield Result.success(obj)
        if not any_line:
            yield Result.no_data("empty jsonl")


def load_jsonl_models(path: Path, parser: Callable[[Mapping[str, Any]], T]) -> Result:
    records: List[T] = []
    errors: List[Dict[str, Any]] = []
    saw_stream = False
    for item in iter_jsonl(path):
        saw_stream = True
        if item.status == Status.SUCCESS_NO_DATA:
            return Result.no_data(item.message)
        if not item.ok:
            errors.append(item.to_dict())
            continue
        try:
            records.append(parser(item.value))
        except (ValueError, TypeError, KeyError) as exc:
            errors.append({"status": Status.INVALID_INPUT.value, "message": str(exc)})
    if not saw_stream:
        return Result.failure(Status.PROVIDER_FAILURE, "jsonl iterator produced nothing")
    if errors and records:
        return Result(
            Status.PARTIAL,
            records,
            "loaded {0} records with {1} errors".format(len(records), len(errors)),
            {"errors": errors},
        )
    if errors and not records:
        return Result.failure(
            Status.INVALID_INPUT,
            "no valid records",
            details={"errors": errors},
        )
    if not records:
        return Result.no_data("no records")
    return Result.success(records)
