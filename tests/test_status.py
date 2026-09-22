from __future__ import annotations

import pytest
from keylogix.status import Result, Status


def test_status_values():
    assert Status.SUCCESS_WITH_DATA.value == "SUCCESS_WITH_DATA"
    assert Status.SUCCESS_NO_DATA.value == "SUCCESS_NO_DATA"
    assert Status.INVALID_INPUT.value == "INVALID_INPUT"
    assert Status.UNREACHABLE.value == "UNREACHABLE"
    assert Status.TIMEOUT.value == "TIMEOUT"
    assert Status.PROVIDER_FAILURE.value == "PROVIDER_FAILURE"
    assert Status.PARTIAL.value == "PARTIAL"
    assert Status.INCONCLUSIVE.value == "INCONCLUSIVE"
    assert Status.SKIPPED.value == "SKIPPED"
    assert Status.INTERRUPTED.value == "INTERRUPTED"
    assert Status.OUT_OF_SCOPE.value == "OUT_OF_SCOPE"
    assert Status.UNAVAILABLE_CONTEXT.value == "UNAVAILABLE_CONTEXT"


def test_result_success():
    res1 = Result.success("payload", "ok msg", details={"count": 1})
    assert res1.ok is True
    assert res1.has_data is True
    assert res1.status == Status.SUCCESS_WITH_DATA
    assert res1.value == "payload"
    assert res1.message == "ok msg"
    assert res1.details == {"count": 1}

    res_no_data = Result.success(None)
    assert res_no_data.ok is True
    assert res_no_data.has_data is False
    assert res_no_data.status == Status.SUCCESS_NO_DATA


def test_result_no_data():
    res = Result.no_data("custom message", details={"info": 42})
    assert res.ok is True
    assert res.has_data is False
    assert res.status == Status.SUCCESS_NO_DATA
    assert res.message == "custom message"
    assert res.details == {"info": 42}


def test_result_invalid():
    res = Result.invalid("bad arg", details={"field": "key_code"})
    assert res.ok is False
    assert res.has_data is False
    assert res.status == Status.INVALID_INPUT
    assert res.message == "bad arg"
    assert res.details == {"field": "key_code"}


def test_result_failure():
    res = Result.failure(Status.PROVIDER_FAILURE, "disk error", details={"errno": 5})
    assert res.ok is False
    assert res.status == Status.PROVIDER_FAILURE
    assert res.message == "disk error"
    assert res.details == {"errno": 5}

    with pytest.raises(ValueError, match="cannot be used with a success status"):
        Result.failure(Status.SUCCESS_WITH_DATA, "cannot fail with success")


def test_result_completed():
    assert Result.success(1).completed is True
    assert Result(Status.PARTIAL, 1).completed is True
    assert Result(Status.INCONCLUSIVE, None).completed is True
    assert Result(Status.SKIPPED, None).completed is False
    assert Result(Status.INTERRUPTED, None).completed is False
    assert Result(Status.OUT_OF_SCOPE, None).completed is False


def test_result_to_dict():
    res = Result.success({"a": 1}, "msg", details={"b": 2})
    d = res.to_dict()
    assert d["status"] == "SUCCESS_WITH_DATA"
    assert d["value"] == {"a": 1}
    assert d["message"] == "msg"
    assert d["details"] == {"b": 2}
