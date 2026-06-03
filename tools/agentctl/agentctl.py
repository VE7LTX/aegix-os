#!/usr/bin/env python3
"""Aegix operator CLI preview control plane."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


VERSION = "preview-v0.2"
DEFAULT_ROOT = Path(os.environ.get("AEGIX_ROOT", "/aegix"))

COMMANDS = [
    "status",
    "commands",
    "doctor",
    "paths",
    "agents",
    "run",
    "receipts",
    "events",
    "inspect",
    "diff",
    "caps",
    "approve",
    "approvals",
    "snapshot",
    "snapshots",
    "rollback",
    "secrets",
    "notes",
    "codex",
    "openclaw",
    "obsidian",
    "tui",
    "term",
    "vault",
    "plugins",
    "capabilities",
    "memory",
    "mcp",
    "api",
    "router",
    "models",
    "ollama",
    "packages",
    "databases",
    "db",
    "vector",
    "timeseries",
    "network",
    "screenshot",
    "logs",
    "services",
    "verify",
    "receipts-path",
    "appliances",
]

PREVIEW_POLICY = {
    "mode": "preview-friendly",
    "allowed_without_approval": [
        "files.read",
        "status.read",
        "logs.read",
        "agent.session.create",
        "receipt.write",
    ],
    "local_write_roots": [
        "/aegix/scratch",
        "/aegix/projects",
    ],
    "approval_required": [
        "external.write",
        "secret.read",
        "service.restart",
        "package.install",
        "auth.change",
        "system.modify",
    ],
    "denied_by_default": [
        "money.movement",
        "device.sensor",
        "network.lan_scan",
    ],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return clean.strip("-") or "item"


def root_from_args(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "root", DEFAULT_ROOT)).expanduser()


def paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "sessions": root / "sessions",
        "receipts": root / "receipts",
        "approvals": root / "approvals",
        "snapshots": root / "snapshots",
        "checkpoints": root / "checkpoints",
        "logs": root / "logs",
        "runbooks": root / "runbooks",
        "policy": root / "policy",
    }


def ensure_dirs(root: Path) -> None:
    for path in paths(root).values():
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_event(root: Path, event: dict[str, Any]) -> None:
    payload = {
        "created_at": iso_now(),
        **event,
    }
    try:
        log_path = root / "logs" / "events.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError:
        pass


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def emit(args: argparse.Namespace, payload: dict[str, Any], exit_code: int = 0) -> int:
    as_json = bool(getattr(args, "json", False))
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=json_default))
    else:
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, sort_keys=True, default=json_default)}")
            else:
                print(f"{key}: {value}")
    return exit_code


def resolve_for_policy(path: Path) -> Path:
    try:
        return path.resolve()
    except FileNotFoundError:
        return path.absolute()


def is_under(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def allowed_workspace(root: Path, workspace: Path) -> bool:
    candidate = resolve_for_policy(workspace)
    allowed_roots = [resolve_for_policy(root / "scratch"), resolve_for_policy(root / "projects")]
    return any(is_under(candidate, allowed_root) for allowed_root in allowed_roots)


def make_session_id(agent: str) -> str:
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{slug(agent)}-{uuid.uuid4().hex[:8]}"


def list_json_files(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    entries = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        data = read_json(path) or {}
        if "path" not in data:
            data["path"] = str(path)
        entries.append(data)
    return entries


def list_events(root: Path, limit: int) -> list[dict[str, Any]]:
    log_path = root / "logs" / "events.jsonl"
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()[-limit:]
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"unparsed": line})
    return events


def policy_payload(root: Path) -> dict[str, Any]:
    policy = dict(PREVIEW_POLICY)
    policy["local_write_roots"] = [str(root / "scratch"), str(root / "projects")]
    policy["policy_file"] = str(root / "policy" / "capabilities.yaml")
    return policy


def cmd_status(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    p = paths(root)
    payload = {
        "name": "Aegix OS",
        "version": VERSION,
        "root": str(root),
        "available_commands": COMMANDS,
        "counts": {
            "sessions": len(list(p["sessions"].glob("*"))) if p["sessions"].exists() else 0,
            "receipts": len(list(p["receipts"].glob("*.json"))) if p["receipts"].exists() else 0,
            "approvals": len(list(p["approvals"].glob("*.json"))) if p["approvals"].exists() else 0,
            "snapshots": len(list(p["snapshots"].glob("*.json"))) if p["snapshots"].exists() else 0,
        },
    }
    return emit(args, payload)


def cmd_commands(args: argparse.Namespace) -> int:
    return emit(args, {"commands": COMMANDS})


def cmd_paths(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    p = paths(root)
    payload = {
        "root": str(root),
        "paths": {name: str(path) for name, path in p.items()},
        "quick_commands": [
            "agentctl doctor --json",
            "agentctl run demo-agent --task \"Create preview receipt\" --workspace /aegix/scratch/demo --json",
            "agentctl receipts --json",
            "agentctl events --json",
            "agentctl rollback <session_id> --json",
        ],
    }
    append_event(root, {"command": "paths", "status": "reported"})
    return emit(args, payload)


def directory_check(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "readable": os.access(path, os.R_OK),
        "writable": os.access(path, os.W_OK),
        "executable": os.access(path, os.X_OK),
    }


def failed_units() -> dict[str, Any]:
    if shutil.which("systemctl") is None:
        return {"available": False, "failed_count": None, "output": "systemctl not available"}
    result = subprocess.run(
        ["systemctl", "--failed", "--no-pager", "--plain"],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    output = (result.stdout + result.stderr).strip()
    failed_count = 0
    for line in output.splitlines():
        if ".service" in line or ".socket" in line or ".timer" in line:
            failed_count += 1
    return {
        "available": True,
        "exit_code": result.returncode,
        "failed_count": failed_count,
        "output": output,
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    ensure_dirs(root)
    p = paths(root)
    dirs = [
        p["root"],
        root / "scratch",
        root / "projects",
        p["sessions"],
        p["receipts"],
        p["approvals"],
        p["snapshots"],
        p["checkpoints"],
        p["logs"],
        p["policy"],
    ]
    checks = {
        "directories": {str(path): directory_check(path) for path in dirs},
        "policy_file": {
            "path": str(root / "policy" / "capabilities.yaml"),
            "exists": (root / "policy" / "capabilities.yaml").exists(),
        },
        "commands": {
            "agentctl": shutil.which("agentctl") or "current script",
            "aegixtui": shutil.which("aegixtui"),
            "obsidianctl": shutil.which("obsidianctl"),
            "secretsctl": shutil.which("secretsctl"),
            "codexcli": shutil.which("codexcli"),
        },
        "systemd_failed": failed_units(),
    }
    writable_required = {
        str(root / "scratch"),
        str(root / "projects"),
        str(p["sessions"]),
        str(p["receipts"]),
        str(p["approvals"]),
        str(p["snapshots"]),
        str(p["checkpoints"]),
        str(p["logs"]),
    }
    writable_failures = [
        item["path"]
        for item in checks["directories"].values()
        if item["path"] in writable_required and item["exists"] and item["is_dir"] and not item["writable"]
    ]
    systemd_failed_count = checks["systemd_failed"].get("failed_count")
    status = "passed" if not writable_failures and systemd_failed_count in (0, None) else "degraded"
    payload = {
        "status": status,
        "version": VERSION,
        "root": str(root),
        "writable_failures": writable_failures,
        "checks": checks,
    }
    append_event(root, {"command": "doctor", "status": status, "writable_failures": writable_failures})
    return emit(args, payload, 0 if status == "passed" else 1)


def cmd_caps(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    append_event(root, {"command": "caps", "status": "reported"})
    return emit(args, policy_payload(root))


def cmd_run(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    ensure_dirs(root)
    session_id = make_session_id(args.agent)
    workspace = Path(args.workspace).expanduser()
    if not workspace.is_absolute():
        workspace = root / workspace

    created_at = iso_now()
    session_dir = root / "sessions" / session_id
    session_path = session_dir / "session.json"
    receipt_path = root / "receipts" / f"{session_id}.json"
    permitted = allowed_workspace(root, workspace)

    capabilities_used = ["agent.session.create", "receipt.write"]
    actions: list[dict[str, Any]] = [
        {"type": "session.create", "path": str(session_path)},
        {"type": "receipt.write", "path": str(receipt_path)},
    ]

    if permitted:
        artifact_path = workspace / f"aegix-session-{session_id}.md"
        try:
            workspace.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                "\n".join(
                    [
                        f"# Aegix Preview Session {session_id}",
                        "",
                        f"- agent: {args.agent}",
                        f"- task: {args.task}",
                        f"- created_at: {created_at}",
                        "",
                        "This file is a preview-safe local write created by agentctl.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            capabilities_used.append(f"files.write:{workspace}")
            actions.append({"type": "file.write", "path": str(artifact_path)})
            verification = {
                "method": "file_exists",
                "target": str(artifact_path),
                "result": "passed" if artifact_path.exists() else "failed",
            }
            status = "completed" if artifact_path.exists() else "failed"
        except OSError as exc:
            verification = {
                "method": "filesystem_write",
                "target": str(workspace),
                "result": "blocked",
                "reason": f"{exc.__class__.__name__}: {exc}",
            }
            status = "blocked"
            actions.append({"type": "filesystem.block", "path": str(workspace), "reason": str(exc)})
    else:
        verification = {
            "method": "policy_check",
            "target": str(workspace),
            "result": "blocked",
            "reason": "workspace must be under /aegix/scratch or /aegix/projects",
        }
        status = "blocked"
        actions.append({"type": "policy.block", "path": str(workspace)})

    session = {
        "session_id": session_id,
        "agent": args.agent,
        "task": args.task,
        "workspace": str(workspace),
        "risk_level": args.risk_level,
        "created_at": created_at,
        "status": status,
        "session_dir": str(session_dir),
    }
    receipt = {
        "session_id": session_id,
        "agent": args.agent,
        "task": args.task,
        "workspace": str(workspace),
        "capabilities_used": capabilities_used,
        "actions": actions,
        "verification": verification,
        "rollback": {
            "status": "metadata-only",
            "snapshot_command": f"agentctl snapshot {session_id} --json",
            "rollback_command": f"agentctl rollback {session_id} --json",
            "note": "Preview v0.2 records rollback intent. Destructive rollback is not executed.",
        },
        "status": status,
        "created_at": created_at,
    }

    write_json(session_path, session)
    write_json(receipt_path, receipt)
    append_event(
        root,
        {
            "command": "run",
            "session_id": session_id,
            "agent": args.agent,
            "workspace": str(workspace),
            "status": status,
        },
    )

    payload = {
        "session_id": session_id,
        "status": status,
        "session": session,
        "receipt": receipt,
        "session_path": str(session_path),
        "receipt_path": str(receipt_path),
    }
    return emit(args, payload, 0 if status != "failed" else 1)


def cmd_receipts(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    payload = {"receipts": list_json_files(root / "receipts")}
    append_event(root, {"command": "receipts", "status": "listed", "count": len(payload["receipts"])})
    return emit(args, payload)


def cmd_events(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    payload = {"events": list_events(root, args.limit), "log_path": str(root / "logs" / "events.jsonl")}
    return emit(args, payload)


def cmd_inspect(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    session_path = root / "sessions" / args.session_id / "session.json"
    receipt_path = root / "receipts" / f"{args.session_id}.json"
    session = read_json(session_path)
    receipt = read_json(receipt_path)
    if session is None and receipt is None:
        return emit(
            args,
            {
                "found": False,
                "session_id": args.session_id,
                "session_path": str(session_path),
                "receipt_path": str(receipt_path),
            },
            1,
        )
    return emit(
        args,
        {
            "found": True,
            "session_id": args.session_id,
            "session": session,
            "receipt": receipt,
        },
    )


def cmd_approve(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    ensure_dirs(root)
    created_at = utc_now()
    expires_at = created_at + timedelta(minutes=args.ttl_minutes)
    approval = {
        "session_id": args.session_id,
        "capability": args.cap,
        "approver": args.approver,
        "reason": args.reason,
        "created_at": created_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "metadata-only",
        "execution_enabled": False,
    }
    approval_id = f"{args.session_id}-{slug(args.cap)}-{uuid.uuid4().hex[:8]}"
    approval_path = root / "approvals" / f"{approval_id}.json"
    approval["approval_id"] = approval_id
    approval["path"] = str(approval_path)
    write_json(approval_path, approval)
    append_event(
        root,
        {
            "command": "approve",
            "session_id": args.session_id,
            "capability": args.cap,
            "status": "metadata-only",
        },
    )
    return emit(args, {"approval": approval})


def cmd_approvals(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    return emit(args, {"approvals": list_json_files(root / "approvals")})


def cmd_snapshot(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    ensure_dirs(root)
    created_at = iso_now()
    snapshot_id = f"{args.session_id}-{uuid.uuid4().hex[:8]}"
    snapshot_path = root / "snapshots" / f"{snapshot_id}.json"
    checkpoint_path = root / "checkpoints" / f"{snapshot_id}.json"
    snapshot = {
        "snapshot_id": snapshot_id,
        "session_id": args.session_id,
        "created_at": created_at,
        "status": "metadata-only",
        "destructive_actions": False,
        "rollback_available": False,
        "session_path": str(root / "sessions" / args.session_id / "session.json"),
        "receipt_path": str(root / "receipts" / f"{args.session_id}.json"),
        "checkpoint_path": str(checkpoint_path),
        "restore_plan": [
            "read receipt actions",
            "compare current workspace files with receipt metadata",
            "show planned reversal to operator",
            "require approval token before modifying files",
        ],
        "note": "Preview v0.2 records snapshot intent only. Real btrfs/ZFS snapshotting is deferred.",
    }
    write_json(snapshot_path, snapshot)
    write_json(checkpoint_path, snapshot)
    append_event(root, {"command": "snapshot", "session_id": args.session_id, "status": "metadata-only"})
    return emit(args, {"snapshot": snapshot, "snapshot_path": str(snapshot_path), "checkpoint_path": str(checkpoint_path)})


def cmd_snapshots(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    return emit(args, {"snapshots": list_json_files(root / "snapshots")})


def cmd_rollback(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    payload = {
        "session_id": args.session_id,
        "status": "planned",
        "destructive_actions": False,
        "rollback_executed": False,
        "planned_behavior": [
            "load session metadata",
            "load receipt diff and snapshot reference",
            "present rollback plan for operator approval",
            "apply filesystem or declarative config rollback in a later release",
        ],
        "operator_next_step": f"inspect receipt and snapshot metadata before approving rollback for {args.session_id}",
        "receipt_path": str(root / "receipts" / f"{args.session_id}.json"),
    }
    append_event(root, {"command": "rollback", "session_id": args.session_id, "status": "planned"})
    return emit(args, payload)


def cmd_scaffold(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    command = getattr(args, "command", "unknown")
    payload = {
        "command": command,
        "status": "scaffolded",
        "version": VERSION,
        "root": str(root),
        "message": "This command is reserved for the next Aegix control-plane milestone.",
    }
    return emit(args, payload)


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentctl", description="Aegix OS operator CLI")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Aegix root path")
    add_json_flag(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show Aegix status")
    add_json_flag(status)
    status.set_defaults(func=cmd_status)

    commands = subparsers.add_parser("commands", help="list available commands")
    add_json_flag(commands)
    commands.set_defaults(func=cmd_commands)

    doctor = subparsers.add_parser("doctor", help="run preview health checks")
    add_json_flag(doctor)
    doctor.set_defaults(func=cmd_doctor)

    path_cmd = subparsers.add_parser("paths", help="show Aegix control-plane paths")
    add_json_flag(path_cmd)
    path_cmd.set_defaults(func=cmd_paths)

    run = subparsers.add_parser("run", help="run a preview-safe agent session")
    run.add_argument("agent", help="agent name")
    run.add_argument("--task", required=True, help="task text")
    run.add_argument("--workspace", required=True, help="workspace path")
    run.add_argument("--risk-level", default="L1", help="risk level label")
    add_json_flag(run)
    run.set_defaults(func=cmd_run)

    receipts = subparsers.add_parser("receipts", help="list receipts")
    add_json_flag(receipts)
    receipts.set_defaults(func=cmd_receipts)

    events = subparsers.add_parser("events", help="show recent Aegix event log entries")
    events.add_argument("--limit", type=int, default=25)
    add_json_flag(events)
    events.set_defaults(func=cmd_events)

    inspect = subparsers.add_parser("inspect", help="inspect a session")
    inspect.add_argument("session_id", help="session id")
    add_json_flag(inspect)
    inspect.set_defaults(func=cmd_inspect)

    caps = subparsers.add_parser("caps", help="show preview capability policy")
    add_json_flag(caps)
    caps.set_defaults(func=cmd_caps)

    approve = subparsers.add_parser("approve", help="create approval token metadata")
    approve.add_argument("session_id", help="session id")
    approve.add_argument("--cap", required=True, help="capability to approve")
    approve.add_argument("--approver", default=os.environ.get("USER") or os.environ.get("USERNAME") or "operator")
    approve.add_argument("--ttl-minutes", type=int, default=60)
    approve.add_argument("--reason", default="preview approval scaffold")
    add_json_flag(approve)
    approve.set_defaults(func=cmd_approve)

    approvals = subparsers.add_parser("approvals", help="list approval metadata")
    add_json_flag(approvals)
    approvals.set_defaults(func=cmd_approvals)

    snapshot = subparsers.add_parser("snapshot", help="create snapshot metadata")
    snapshot.add_argument("session_id", help="session id")
    add_json_flag(snapshot)
    snapshot.set_defaults(func=cmd_snapshot)

    snapshots = subparsers.add_parser("snapshots", help="list snapshot metadata")
    add_json_flag(snapshots)
    snapshots.set_defaults(func=cmd_snapshots)

    rollback = subparsers.add_parser("rollback", help="show planned rollback behavior")
    rollback.add_argument("session_id", help="session id")
    add_json_flag(rollback)
    rollback.set_defaults(func=cmd_rollback)

    for command in COMMANDS:
        if command in {
            "status",
            "commands",
            "doctor",
            "paths",
            "run",
            "receipts",
            "events",
            "inspect",
            "caps",
            "approve",
            "approvals",
            "snapshot",
            "snapshots",
            "rollback",
        }:
            continue
        scaffold = subparsers.add_parser(command, help=f"{command} scaffold")
        scaffold.add_argument("args", nargs="*")
        add_json_flag(scaffold)
        scaffold.set_defaults(func=cmd_scaffold)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
