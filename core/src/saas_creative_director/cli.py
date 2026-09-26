from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .figma import build_manifest
from .orchestrator import GATES, advance, next_action
from .validation import validate_project
from .workspace import initialize_project, load_project, utc_now, write_json


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
    figma = commands.add_parser("figma-manifest", help="build an editable-frame import manifest")
    figma.add_argument("project", type=Path)
    figma.add_argument("--output", type=Path, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            initialize_project(args.project, args.name)
            print(f"Created {args.project}")
        elif args.command == "status":
            action = next_action(load_project(args.project))
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
            stage = advance(project)
            write_json(args.project / "project.json", project)
            print(f"Stage: {stage}")
        elif args.command == "approve":
            project = load_project(args.project)
            project["gates"][args.gate] = {
                "status": "APPROVED",
                "approved_by": args.by,
                "approved_at": utc_now(),
                "notes": args.notes,
            }
            write_json(args.project / "project.json", project)
            print(f"Approved: {args.gate}")
        elif args.command == "figma-manifest":
            write_json(args.output, build_manifest(args.project))
            print(f"Wrote {args.output}")
    except (FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
