from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .context import load_execution_policy, prepare_stage_runtime
from .figma import build_manifest
from .orchestrator import GATES, STAGES, advance, next_action
from .usage import append_usage_event, summarize_usage
from .validation import validate_for_export, validate_project
from .workspace import (
    initialize_project,
    load_project,
    record_approval,
    record_changes_requested,
    refresh_gate_approvals,
    write_json,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="scd", description="SaaS Creative Director project controller")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a client workspace")
    init.add_argument("project", type=Path)
    init.add_argument("--name", required=True)
    status = commands.add_parser("status", help="show the next workflow action")
    status.add_argument("project", type=Path)
    validate = commands.add_parser("validate", help="check evidence links and project structure")
    validate.add_argument("project", type=Path)
    step = commands.add_parser("advance", help="advance to the next stage")
    step.add_argument("project", type=Path)
    approve = commands.add_parser("approve", help="record a human approval gate")
    approve.add_argument("project", type=Path)
    approve.add_argument("gate", choices=tuple(GATES))
    approve.add_argument("--by", default="human-reviewer")
    approve.add_argument("--notes", default="")
    reject = commands.add_parser("request-changes", help="record requested changes at a human gate")
    reject.add_argument("project", type=Path)
    reject.add_argument("gate", choices=tuple(GATES))
    reject.add_argument("--by", default="human-reviewer")
    reject.add_argument("--notes", required=True)
    figma = commands.add_parser("figma-manifest", help="build an editable-frame import manifest")
    figma.add_argument("project", type=Path)
    figma.add_argument("--output", type=Path, required=True)
    runtime = commands.add_parser("prepare-runtime", help="build a bounded stage context and checkpoint")
    runtime.add_argument("project", type=Path)
    runtime.add_argument("--stage", choices=STAGES)
    runtime.add_argument("--scene-id", action="append", default=[])
    usage = commands.add_parser("record-usage", help="append a privacy-minimal usage event")
    usage.add_argument("project", type=Path)
    usage.add_argument("--run-id", required=True)
    usage.add_argument("--stage", choices=STAGES, required=True)
    usage.add_argument("--scene-id", action="append", default=[])
    usage.add_argument("--billing-mode", choices=("subscription", "usage_credits", "api", "unknown"))
    usage.add_argument("--usage-source", choices=("provider_reported", "host_reported", "user_reported", "estimated", "unknown"), default="unknown")
    usage.add_argument("--model")
    usage.add_argument("--input-tokens", type=int)
    usage.add_argument("--output-tokens", type=int)
    usage.add_argument("--cache-read-tokens", type=int)
    usage.add_argument("--cache-write-tokens", type=int)
    usage.add_argument("--tool-calls", type=int)
    usage.add_argument("--estimated-usd", type=float)
    usage.add_argument("--price-snapshot-id")
    usage.add_argument("--estimated", action="store_true")
    usage_summary = commands.add_parser("usage-summary", help="summarize known usage without inventing missing values")
    usage_summary.add_argument("project", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            initialize_project(args.project, args.name)
            prepare_stage_runtime(args.project, "intake", next_actions=["Complete intake and register locatable sources."])
            print(f"Created {args.project}")
        elif args.command == "status":
            project = load_project(args.project)
            if refresh_gate_approvals(args.project, project):
                write_json(args.project / "project.json", project)
            action = next_action(project)
            prepare_stage_runtime(args.project, next_actions=[action.instruction])
            print(f"{action.kind}: {action.name}\n{action.instruction}")
        elif args.command == "validate":
            issues = validate_project(args.project)
            for issue in issues:
                print(f"{issue.severity.upper()} {issue.path}: {issue.message}")
            if issues:
                return 1
            print("Project is valid.")
        elif args.command == "advance":
            project = load_project(args.project)
            completed_stage = str(project.get("stage", "intake"))
            completed_runtime = prepare_stage_runtime(args.project, completed_stage)
            stage = advance(project, args.project)
            write_json(args.project / "project.json", project)
            policy = load_execution_policy()
            append_usage_event(args.project / "reviews" / "usage-ledger.jsonl", {
                "project_id": completed_runtime["project_id"],
                "run_id": f"stage/{completed_stage}/{completed_runtime['context_revision']}",
                "stage": completed_stage,
                "event_kind": "stage_boundary",
                "billing_mode": policy["billing_mode"],
                "usage_source": "unknown",
                "estimated": False,
            })
            prepare_stage_runtime(args.project, stage, next_actions=[next_action(project).instruction])
            print(f"Stage: {stage}")
        elif args.command == "approve":
            project = load_project(args.project)
            record_approval(args.project, project, args.gate, args.by, args.notes)
            write_json(args.project / "project.json", project)
            prepare_stage_runtime(args.project, next_actions=[next_action(project).instruction])
            print(f"Approved: {args.gate}")
        elif args.command == "request-changes":
            project = load_project(args.project)
            record_changes_requested(args.project, project, args.gate, args.by, args.notes)
            write_json(args.project / "project.json", project)
            prepare_stage_runtime(args.project, unresolved=[args.notes], next_actions=[next_action(project).instruction])
            print(f"Changes requested: {args.gate}")
        elif args.command == "figma-manifest":
            issues = validate_for_export(args.project)
            if issues:
                first = issues[0]
                raise ValueError(f"Cannot export: {first.path}: {first.message}")
            write_json(args.output, build_manifest(args.project))
            print(f"Wrote {args.output}")
        elif args.command == "prepare-runtime":
            state = prepare_stage_runtime(args.project, args.stage, args.scene_id)
            print(json.dumps({
                "stage": state["stage"],
                "context": str(state["context_path"]),
                "checkpoint": str(state["checkpoint_path"]),
                "cache_hit": state["cache_hit"],
                "enforcement_scope": state["execution_policy"]["enforcement_scope"],
            }, ensure_ascii=False, sort_keys=True))
        elif args.command == "record-usage":
            policy = load_execution_policy()
            runtime_state = prepare_stage_runtime(args.project, args.stage, args.scene_id)
            event = {
                "project_id": runtime_state["project_id"],
                "run_id": args.run_id,
                "stage": args.stage,
                "scene_ids": args.scene_id,
                "event_kind": "model_usage",
                "billing_mode": args.billing_mode or policy["billing_mode"],
                "usage_source": args.usage_source,
                "estimated": args.estimated,
                "model": args.model,
                "input_tokens": args.input_tokens,
                "output_tokens": args.output_tokens,
                "cache_read_tokens": args.cache_read_tokens,
                "cache_write_tokens": args.cache_write_tokens,
                "tool_calls": args.tool_calls,
                "estimated_usd": args.estimated_usd,
                "price_snapshot_id": args.price_snapshot_id,
            }
            added = append_usage_event(args.project / "reviews" / "usage-ledger.jsonl", event)
            print("Recorded." if added else "Already recorded.")
        elif args.command == "usage-summary":
            print(json.dumps(summarize_usage(args.project / "reviews" / "usage-ledger.jsonl"), ensure_ascii=False, sort_keys=True))
    except (FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
