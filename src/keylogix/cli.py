"""Command-line interface for KeyLogix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from keylogix.constants import IMPLEMENTATION_VERSION
from keylogix.environment import collect_environment
from keylogix.experiment import ExperimentRunner
from keylogix.model import NormalizedEvent, RawObservation
from keylogix.native_bridge import NativeBridge
from keylogix.observation.replay import ReplaySource
from keylogix.observation.synthetic import SyntheticSource, script_from_keys
from keylogix.persist import iter_jsonl, load_jsonl_models
from keylogix.pipeline import Pipeline, PipelineConfig
from keylogix.status import Result, Status


def _cmd_run_experiment(args: argparse.Namespace) -> int:
    runner = ExperimentRunner(base_output_dir=args.output_dir or "output/experiments")
    res = runner.run_experiment(args.definition, run_id=args.run_id)
    if not res.ok and res.status != Status.PARTIAL:
        print(f"[-] Experiment failed: {res.status.value} - {res.message}", file=sys.stderr)
        return 1
    val = res.value or {}
    print(f"[+] Experiment completed: {res.status.value}")
    print(f"    Experiment ID : {val.get('experiment_id')}")
    print(f"    Run ID        : {val.get('run_id')}")
    print(f"    Artifacts Dir : {val.get('output_dir')}")
    return 0


def _cmd_run_synthetic(args: argparse.Namespace) -> int:
    keys = []
    if args.keys:
        for k in args.keys.split(","):
            k_s = k.strip()
            if k_s:
                if k_s.startswith("0x") or k_s.startswith("0X"):
                    keys.append(int(k_s, 16))
                else:
                    keys.append(int(k_s))
    else:
        # Default test sequence: 'T', 'E', 'S', 'T' (0x54, 0x45, 0x53, 0x54)
        keys = [0x54, 0x45, 0x53, 0x54]

    script = script_from_keys(
        keys,
        hold=True,
        application=args.default_application,
        window_title=args.default_window,
    )
    source = SyntheticSource(
        script=script,
        default_application=args.default_application,
        default_window=args.default_window,
    )

    out_dir = Path(args.output_dir or f"output/experiments/{args.experiment_id}/manual_run")
    pipeline = Pipeline()
    config = PipelineConfig(
        experiment_id=args.experiment_id,
        output_dir=out_dir,
        associate_context=True,
        persist=True,
    )

    res = pipeline.run(source, config)
    if not res.ok and res.status != Status.PARTIAL:
        print(f"[-] Synthetic pipeline run failed: {res.status.value} - {res.message}", file=sys.stderr)
        return 1
    print(f"[+] Pipeline completed: {res.status.value}")
    print(f"    Output directory: {out_dir}")
    print(f"    Raw events: {len(res.value.raw)}")
    print(f"    Normalized: {len(res.value.normalized)}")
    return 0


def _cmd_run_replay(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"[-] Replay input file not found: {path}", file=sys.stderr)
        return 1

    source = ReplaySource(path=path)
    out_dir = Path(args.output_dir or f"output/experiments/{args.experiment_id}/replay_run")
    pipeline = Pipeline()
    config = PipelineConfig(
        experiment_id=args.experiment_id,
        output_dir=out_dir,
        associate_context=True,
        persist=True,
    )

    res = pipeline.run(source, config)
    if not res.ok and res.status != Status.PARTIAL:
        print(f"[-] Replay run failed: {res.status.value} - {res.message}", file=sys.stderr)
        return 1
    print(f"[+] Replay run completed: {res.status.value}")
    print(f"    Output directory: {out_dir}")
    print(f"    Raw events: {len(res.value.raw)}")
    print(f"    Normalized: {len(res.value.normalized)}")
    return 0


def _cmd_inspect_raw(args: argparse.Namespace) -> int:
    path = Path(args.file)
    res = load_jsonl_models(path, RawObservation.from_dict)
    if not res.ok and not res.has_data:
        print(f"[-] Failed to read raw observations: {res.message}", file=sys.stderr)
        return 1
    events: List[RawObservation] = res.value or []
    print(f"[+] Loaded {len(events)} raw observations from {path}:")
    for i, e in enumerate(events[:args.limit], start=1):
        lbl = e.key_label.value if e.key_label.presence in ("observed", "derived") else "n/a"
        print(f"  [{i:03d}] {e.timestamp} | {e.event_type:9s} | VK:0x{e.key_code or 0:02X} ({lbl:8s}) | Mod:0x{e.modifier_state.encoding:X} | Src:{e.source}")
    if len(events) > args.limit:
        print(f"  ... and {len(events) - args.limit} more events.")
    return 0


def _cmd_inspect_normalized(args: argparse.Namespace) -> int:
    path = Path(args.file)
    res = load_jsonl_models(path, NormalizedEvent.from_dict)
    if not res.ok and not res.has_data:
        print(f"[-] Failed to read normalized events: {res.message}", file=sys.stderr)
        return 1
    events: List[NormalizedEvent] = res.value or []
    print(f"[+] Loaded {len(events)} normalized events from {path}:")
    for i, e in enumerate(events[:args.limit], start=1):
        lbl = e.key_label.value if e.key_label.presence in ("observed", "derived") else "n/a"
        app = e.application.value if e.application.presence in ("observed", "derived") else "n/a"
        print(f"  [{i:03d}] {e.timestamp} | {e.event_type:9s} | VK:0x{e.key_code:02X} ({lbl:8s}) | Mod:0x{e.modifier_state.encoding:X} | App:{app}")
    if len(events) > args.limit:
        print(f"  ... and {len(events) - args.limit} more events.")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    print(f"=== KeyLogix v{IMPLEMENTATION_VERSION} Verification ===")
    env = collect_environment()
    print(f"Python Platform : {env.get('platform')}")
    print(f"Source Revision : {env.get('source_revision')}")
    print(f"Win32 Hook Avail: {env.get('win32_hook_available')}")
    
    bridge = NativeBridge()
    print(f"Native Library  : {'Available (' + str(bridge.lib_path) + ')' if bridge.available else 'Not Built / Not Found'}")
    
    if bridge.available:
        buf_res = bridge.evt_buffer_init(100)
        print(f"Native ABI Test : {'OK (' + str(buf_res.value) + ')' if buf_res.ok else 'FAIL: ' + buf_res.message}")
    print("=== Verification Complete ===")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="keylogix",
        description="KeyLogix: Controlled laboratory for Windows low-level input-capture research",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {IMPLEMENTATION_VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # run-experiment
    p_exp = subparsers.add_parser("run-experiment", help="Execute an experiment from a definition file")
    p_exp.add_argument("definition", help="Path to experiment definition JSON file")
    p_exp.add_argument("--output-dir", help="Custom base output directory")
    p_exp.add_argument("--run-id", help="Explicit run ID (default: auto-generated UUID4)")

    # run-synthetic
    p_syn = subparsers.add_parser("run-synthetic", help="Run pipeline with synthetic input script")
    p_syn.add_argument("--keys", help="Comma-separated VK key codes (decimal or hex, e.g. 0x41,0x42)")
    p_syn.add_argument("--experiment-id", default="EXP-MANUAL-SYNTHETIC", help="Experiment ID")
    p_syn.add_argument("--default-application", default="notepad.exe", help="Default application context")
    p_syn.add_argument("--default-window", default="Untitled - Notepad", help="Default window title context")
    p_syn.add_argument("--output-dir", help="Custom output directory")

    # run-replay
    p_rep = subparsers.add_parser("run-replay", help="Run pipeline replaying raw JSONL observations")
    p_rep.add_argument("file", help="Path to raw.jsonl file")
    p_rep.add_argument("--experiment-id", default="EXP-MANUAL-REPLAY", help="Experiment ID")
    p_rep.add_argument("--output-dir", help="Custom output directory")

    # inspect-raw
    p_iraw = subparsers.add_parser("inspect-raw", help="Inspect raw observation JSONL file")
    p_iraw.add_argument("file", help="Path to raw.jsonl")
    p_iraw.add_argument("--limit", type=int, default=25, help="Max records to display")

    # inspect-normalized
    p_inorm = subparsers.add_parser("inspect-normalized", help="Inspect normalized event JSONL file")
    p_inorm.add_argument("file", help="Path to normalized.jsonl")
    p_inorm.add_argument("--limit", type=int, default=25, help="Max records to display")

    # verify
    subparsers.add_parser("verify", help="Check environment and native library status")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "run-experiment": _cmd_run_experiment,
        "run-synthetic": _cmd_run_synthetic,
        "run-replay": _cmd_run_replay,
        "inspect-raw": _cmd_inspect_raw,
        "inspect-normalized": _cmd_inspect_normalized,
        "verify": _cmd_verify,
    }

    handler = commands.get(args.command)
    if not handler:
        parser.print_help()
        return 1
    return handler(args)
