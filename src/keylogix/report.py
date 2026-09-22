"""Markdown reports of what was actually measured."""

from __future__ import annotations

from typing import Any, Mapping


def render_report(experiment: Mapping[str, Any]) -> str:
    lines = [
        "# Experiment {0}".format(experiment.get("experiment_id", "unknown")),
        "",
        "## Status",
        "",
        "`{0}`".format(experiment.get("status", "UNKNOWN")),
        "",
        "## Objective",
        "",
        str(experiment.get("objective") or ""),
        "",
        "## Environment",
        "",
        _code(experiment.get("environment")),
        "",
        "## Implementation version",
        "",
        str(experiment.get("implementation_version") or ""),
        "",
        "## Configuration",
        "",
        _code(experiment.get("configuration")),
        "",
        "## Input",
        "",
        _code(experiment.get("input")),
        "",
        "## Procedure",
        "",
    ]
    proc = experiment.get("procedure") or []
    if isinstance(proc, list):
        for step in proc:
            lines.append("- {0}".format(step))
    else:
        lines.append(str(proc))
    lines.extend(
        [
            "",
            "## Expected observation",
            "",
            _code(experiment.get("expected_observation")),
            "",
            "## Actual observation",
            "",
            _code(experiment.get("actual_observation")),
            "",
            "## Telemetry / observability",
            "",
            _code(experiment.get("telemetry")),
            "",
            "## Security-product state",
            "",
            _code(experiment.get("security_product_state")),
            "",
            "## Result",
            "",
            str(experiment.get("result") or ""),
            "",
            "## Limitations",
            "",
        ]
    )
    limits = experiment.get("limitations") or []
    if isinstance(limits, list):
        for item in limits:
            lines.append("- {0}".format(item))
    else:
        lines.append(str(limits))
    lines.extend(
        [
            "",
            "## Analysis",
            "",
            _code(experiment.get("analysis")),
            "",
            "This report does not claim that any behavior is undetectable,",
            "malicious, or operationally stealthy.",
            "",
        ]
    )
    return "\n".join(lines)


def _code(obj: Any) -> str:
    import json

    try:
        body = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    except TypeError:
        body = str(obj)
    return "```json\n{0}\n```".format(body)
