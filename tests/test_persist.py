from __future__ import annotations

from pathlib import Path
import pytest
from keylogix.persist import (
    atomic_write_text,
    ensure_dir,
    iter_jsonl,
    load_jsonl_models,
    read_json,
    write_json,
    write_jsonl,
)
from keylogix.status import Status


def test_ensure_dir_and_atomic_write(tmp_path: Path):
    target_dir = tmp_path / "subdir" / "nested"
    res = ensure_dir(target_dir)
    assert res.ok is True
    assert target_dir.is_dir()

    target_file = target_dir / "test.txt"
    w_res = atomic_write_text(target_file, "hello world")
    assert w_res.ok is True
    assert target_file.read_text(encoding="utf-8") == "hello world"


def test_write_and_read_json(tmp_path: Path):
    target = tmp_path / "data.json"
    obj = {"key": "value", "count": 10, "nested": [1, 2, 3]}
    w_res = write_json(target, obj)
    assert w_res.ok is True

    r_res = read_json(target)
    assert r_res.ok is True
    assert r_res.value == obj

    # Read missing file
    missing = read_json(tmp_path / "missing.json")
    assert missing.status == Status.UNREACHABLE

    # Read corrupted JSON
    corrupted = tmp_path / "bad.json"
    corrupted.write_text("{bad-json", encoding="utf-8")
    assert read_json(corrupted).status == Status.INVALID_INPUT


def test_write_and_iter_jsonl(tmp_path: Path):
    target = tmp_path / "records.jsonl"
    records = [{"id": 1, "name": "first"}, {"id": 2, "name": "second"}]
    w_res = write_jsonl(target, records)
    assert w_res.ok is True
    assert w_res.status == Status.SUCCESS_WITH_DATA

    items = list(iter_jsonl(target))
    assert len(items) == 2
    assert all(it.ok for it in items)
    assert items[0].value == records[0]
    assert items[1].value == records[1]

    # Empty jsonl
    empty_target = tmp_path / "empty.jsonl"
    w_empty = write_jsonl(empty_target, [])
    assert w_empty.status == Status.SUCCESS_NO_DATA
    empty_items = list(iter_jsonl(empty_target))
    assert len(empty_items) == 1
    assert empty_items[0].status == Status.SUCCESS_NO_DATA


def test_load_jsonl_models(tmp_path: Path):
    target = tmp_path / "models.jsonl"
    lines = ['{"val": 10}', '{"val": 20}', '{"val": "invalid"}']
    target.write_text("\n".join(lines), encoding="utf-8")

    def parser(d):
        if not isinstance(d.get("val"), int):
            raise ValueError("val must be int")
        return d["val"]

    res = load_jsonl_models(target, parser)
    assert res.status == Status.PARTIAL
    assert res.value == [10, 20]
    assert "errors" in res.details
