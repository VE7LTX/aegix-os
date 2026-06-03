#!/usr/bin/env python3
"""Aegix operator CLI preview control plane."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


VERSION = "preview-v0.2"
DEFAULT_ROOT = Path(os.environ.get("AEGIX_ROOT", "/aegix"))

CLI_DESCRIPTION = """\
Aegix operator CLI.

Use agentctl as the first stop for agents and operators. Prefer --json when an
agent will parse the result, write receipts for meaningful work, and use
snapshot/rollback commands before planning destructive changes.
"""

COMMANDS = [
    "status",
    "commands",
    "help",
    "doctor",
    "paths",
    "agents",
    "index",
    "search-index",
    "graph",
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

DEFAULT_AGENT_PROMPT = {
    "intent": "Reserved Aegix command group for future control-plane work.",
    "when_to_use": "Use it to discover the planned surface, then check docs or run agentctl commands --json.",
    "example": "agentctl commands --json",
    "safety_notes": [
        "This preview command does not execute dangerous actions.",
        "Prefer implemented JSON commands before ad hoc shell automation.",
    ],
    "next_steps": [
        "Run agentctl doctor --json to check the environment.",
        "Run agentctl paths --json to find stable files and logs.",
    ],
}

COMMAND_GUIDES: dict[str, dict[str, Any]] = {
    "status": {
        "intent": "Summarize the Aegix root, version, command registry, and control-plane object counts.",
        "when_to_use": "Run first when entering the VM or when a new agent needs orientation.",
        "example": "agentctl status --json",
        "json_fields": ["name", "version", "root", "available_commands", "counts"],
        "next_steps": ["agentctl doctor --json", "agentctl paths --json"],
    },
    "commands": {
        "intent": "List implemented and reserved command groups with usage prompts.",
        "when_to_use": "Use when an agent needs to discover what named interfaces exist.",
        "example": "agentctl commands --json",
        "json_fields": ["commands", "guides"],
        "next_steps": ["agentctl help <command> --json"],
    },
    "help": {
        "intent": "Return a focused helper prompt for one command or all command groups.",
        "when_to_use": "Use before running an unfamiliar command.",
        "example": "agentctl help run --json",
        "json_fields": ["command", "guide"],
        "next_steps": ["Run the command's example with --json."],
    },
    "doctor": {
        "intent": "Check writable work areas, command availability, policy files, and failed systemd units.",
        "when_to_use": "Run before making changes, after boot, and after a failed workflow.",
        "example": "agentctl doctor --json",
        "json_fields": ["status", "writable_failures", "checks"],
        "safety_notes": ["A degraded result means inspect the failing path or unit before continuing."],
        "next_steps": ["agentctl paths --json", "systemctl --failed --no-pager --plain"],
    },
    "paths": {
        "intent": "Show the stable Aegix filesystem map and quick commands.",
        "when_to_use": "Run when deciding where memory, receipts, sessions, logs, or rollback metadata belong.",
        "example": "agentctl paths --json",
        "json_fields": ["root", "paths", "quick_commands"],
        "next_steps": ["Read /aegix/runbooks/first-agent.md", "agentctl events --json"],
    },
    "index": {
        "intent": "Build a local file metadata graph and SQLite text index for agent navigation.",
        "when_to_use": "Run after boot, after adding project files, or before searching a large tree.",
        "example": "agentctl index --scope /aegix/projects --scope /aegix/notes --json",
        "json_fields": ["status", "files_indexed", "graph_path", "sqlite_path", "vector_registry_path"],
        "safety_notes": [
            "The preview index stores metadata and text snippets only for readable text-like files.",
            "Do not index secret stores or credential dumps.",
        ],
        "next_steps": ["agentctl search-index \"query\" --json", "agentctl graph --json"],
    },
    "search-index": {
        "intent": "Search the local SQLite FTS index produced by agentctl index.",
        "when_to_use": "Use before recursively scanning massive trees or asking the user where something is.",
        "example": "agentctl search-index \"rollback policy\" --json",
        "json_fields": ["query", "matches", "sqlite_path"],
        "next_steps": ["Open the matched file path and cite it in receipts or notes."],
    },
    "graph": {
        "intent": "Show the current file graph summary and graph artifact paths.",
        "when_to_use": "Use when an agent needs to understand indexed roots, file counts, or reference edges.",
        "example": "agentctl graph --json",
        "json_fields": ["summary", "graph_path", "files_path", "vector_registry_path"],
        "next_steps": ["agentctl search-index \"query\" --json", "agentctl index --json"],
    },
    "run": {
        "intent": "Create a preview-safe local agent session, write session state, perform a scoped local write, and generate a receipt.",
        "when_to_use": "Use for demo work or preview-safe tasks under /aegix/scratch or /aegix/projects.",
        "example": "agentctl run demo-agent --task \"Create preview receipt\" --workspace /aegix/scratch/demo --json",
        "json_fields": ["session_id", "status", "session", "receipt", "session_path", "receipt_path"],
        "safety_notes": [
            "Only /aegix/scratch and /aegix/projects are writable without approval in this preview.",
            "A blocked status is useful evidence; inspect the receipt instead of retrying blindly.",
        ],
        "next_steps": [
            "agentctl inspect <session_id> --json",
            "agentctl snapshot <session_id> --json",
            "agentctl receipts --json",
        ],
    },
    "receipts": {
        "intent": "List JSON receipts created by agent sessions.",
        "when_to_use": "Use to prove what changed, what was verified, and what rollback command applies.",
        "example": "agentctl receipts --json",
        "json_fields": ["receipts"],
        "next_steps": ["agentctl inspect <session_id> --json"],
    },
    "events": {
        "intent": "Show recent JSONL control-plane events.",
        "when_to_use": "Use for lightweight debugging and timeline reconstruction.",
        "example": "agentctl events --limit 50 --json",
        "json_fields": ["events", "log_path"],
        "next_steps": ["tail -n 50 /aegix/logs/events.jsonl"],
    },
    "inspect": {
        "intent": "Read session and receipt details for one session id.",
        "when_to_use": "Use before rollback, approval, or reporting completion.",
        "example": "agentctl inspect 20260603T044522Z-demo-agent-69150e6b --json",
        "json_fields": ["found", "session_id", "session", "receipt"],
        "next_steps": ["agentctl snapshot <session_id> --json", "agentctl rollback <session_id> --json"],
    },
    "caps": {
        "intent": "Show the preview capability policy and approval-required categories.",
        "when_to_use": "Use before shell, network, service, package, auth, or secret-related actions.",
        "example": "agentctl caps --json",
        "json_fields": ["mode", "allowed_without_approval", "local_write_roots", "approval_required"],
        "safety_notes": ["Do not perform external writes, secret reads, service restarts, package installs, or auth changes without approval metadata."],
        "next_steps": ["agentctl approve <session_id> --cap <capability> --json"],
    },
    "approve": {
        "intent": "Create narrow approval metadata for a capability and session.",
        "when_to_use": "Use to scaffold approval intent before v0.3 enforcement.",
        "example": "agentctl approve <session_id> --cap service.restart:ollama --reason \"operator requested restart\" --json",
        "json_fields": ["approval"],
        "safety_notes": ["This does not execute the dangerous action; execution remains disabled in preview v0.2."],
        "next_steps": ["agentctl approvals --json", "agentctl inspect <session_id> --json"],
    },
    "approvals": {
        "intent": "List approval metadata files.",
        "when_to_use": "Use when auditing pending or historical approval scaffolds.",
        "example": "agentctl approvals --json",
        "json_fields": ["approvals"],
        "next_steps": ["agentctl inspect <session_id> --json"],
    },
    "snapshot": {
        "intent": "Write snapshot and checkpoint metadata for rollback planning.",
        "when_to_use": "Use before any rollback proposal or risky follow-up action.",
        "example": "agentctl snapshot <session_id> --json",
        "json_fields": ["snapshot", "snapshot_path", "checkpoint_path"],
        "safety_notes": ["This is metadata-only; it does not create btrfs/ZFS snapshots yet."],
        "next_steps": ["agentctl rollback <session_id> --json"],
    },
    "snapshots": {
        "intent": "List snapshot metadata files.",
        "when_to_use": "Use to find checkpoint records for rollback planning.",
        "example": "agentctl snapshots --json",
        "json_fields": ["snapshots"],
        "next_steps": ["agentctl rollback <session_id> --json"],
    },
    "rollback": {
        "intent": "Report the planned non-destructive rollback behavior for a session.",
        "when_to_use": "Use after inspecting a receipt and creating snapshot metadata.",
        "example": "agentctl rollback <session_id> --json",
        "json_fields": ["session_id", "status", "rollback_mode", "planned_behavior", "operator_next_step"],
        "safety_notes": ["Preview v0.2 never performs destructive rollback; it only explains the plan."],
        "next_steps": ["Get explicit approval before any future destructive rollback implementation."],
    },
    "verify": {
        "intent": "Run the Preview v0.2 control-plane verification harness end to end.",
        "when_to_use": "Run after boot, before demos, after changing agentctl, or when an agent needs proof that rollback and AI-first surfaces work.",
        "example": "agentctl verify --json",
        "json_fields": ["status", "report_id", "checks", "session_id", "report_path"],
        "safety_notes": [
            "This creates preview-safe files only under /aegix/scratch and metadata under /aegix.",
            "Rollback remains metadata-only in v0.2; this command proves rollback traceability, not destructive restore.",
        ],
        "next_steps": [
            "agentctl receipts --json",
            "agentctl inspect <session_id> --json",
            "agentctl rollback <session_id> --json",
        ],
    },
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
        "scratch": root / "scratch",
        "projects": root / "projects",
        "sessions": root / "sessions",
        "receipts": root / "receipts",
        "approvals": root / "approvals",
        "snapshots": root / "snapshots",
        "checkpoints": root / "checkpoints",
        "logs": root / "logs",
        "index": root / "index",
        "runbooks": root / "runbooks",
        "policy": root / "policy",
        "verify_reports": root / "logs" / "verify",
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


def read_text_preview(path: Path, max_bytes: int) -> tuple[str, bool]:
    try:
        data = path.read_bytes()[:max_bytes]
    except OSError:
        return "", False
    if b"\x00" in data:
        return "", False
    try:
        return data.decode("utf-8", errors="replace"), True
    except OSError:
        return "", False


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


def default_index_scopes(root: Path) -> list[Path]:
    return [
        root / "projects",
        root / "scratch",
        root / "notes",
        root / "runbooks",
        root / "policy",
        root / "receipts",
        root / "sessions",
    ]


def file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".rst", ".adoc"}:
        return "notes"
    if suffix in {".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini"}:
        return "structured"
    if suffix in {".py", ".sh", ".nix", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".c", ".h"}:
        return "code"
    if suffix in {".sqlite", ".db"}:
        return "database"
    return "file"


def extract_references(text: str) -> list[str]:
    refs = set()
    for match in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        refs.add(match.strip())
    for match in re.findall(r"\[\[([^\]]+)\]\]", text):
        refs.add(match.strip())
    for match in re.findall(r"(?:(?:/aegix)|(?:\./)|(?:\.\./))[A-Za-z0-9_./:@+-]+", text):
        refs.add(match.strip())
    return sorted(refs)[:50]


def sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def write_index_sqlite(sqlite_path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute("drop table if exists files")
        conn.execute("drop table if exists file_search")
        conn.execute(
            """
            create table files (
              path text primary key,
              kind text,
              size integer,
              mtime real,
              sha256 text,
              title text,
              snippet text
            )
            """
        )
        try:
            conn.execute("create virtual table file_search using fts5(path, title, snippet)")
            fts_enabled = True
        except sqlite3.OperationalError:
            conn.execute("create table file_search (path text, title text, snippet text)")
            fts_enabled = False
        for record in records:
            conn.execute(
                "insert into files(path, kind, size, mtime, sha256, title, snippet) values (?, ?, ?, ?, ?, ?, ?)",
                (
                    record["path"],
                    record["kind"],
                    record["size"],
                    record["mtime"],
                    record["sha256"],
                    record["title"],
                    record["snippet"],
                ),
            )
            conn.execute(
                "insert into file_search(path, title, snippet) values (?, ?, ?)",
                (record["path"], record["title"], record["snippet"]),
            )
        conn.commit()
        return {"sqlite_fts": fts_enabled, "sqlite_path": str(sqlite_path)}
    finally:
        conn.close()


def search_sqlite(sqlite_path: Path, query: str, limit: int) -> list[dict[str, Any]]:
    if not sqlite_path.exists():
        return []
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = []
        try:
            rows = conn.execute(
                """
                select f.path, f.kind, f.size, f.title, f.snippet
                from file_search s join files f on f.path = s.path
                where file_search match ?
                limit ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            like = f"%{query}%"
            rows = conn.execute(
                """
                select path, kind, size, title, snippet
                from files
                where path like ? or title like ? or snippet like ?
                limit ?
                """,
                (like, like, like, limit),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def policy_payload(root: Path) -> dict[str, Any]:
    policy = dict(PREVIEW_POLICY)
    policy["local_write_roots"] = [str(root / "scratch"), str(root / "projects")]
    policy["policy_file"] = str(root / "policy" / "capabilities.yaml")
    return policy


def guide_for(command: str) -> dict[str, Any]:
    guide = COMMAND_GUIDES.get(command, DEFAULT_AGENT_PROMPT)
    payload = dict(guide)
    payload.setdefault("command", command)
    payload.setdefault("example", f"agentctl {command} --json")
    payload.setdefault("json_tip", "Use --json for machine-readable output.")
    return payload


def add_help(payload: dict[str, Any], command: str) -> dict[str, Any]:
    payload.setdefault("agent_help", guide_for(command))
    return payload


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
    return emit(args, add_help(payload, "status"))


def cmd_commands(args: argparse.Namespace) -> int:
    guides = {command: guide_for(command) for command in COMMANDS}
    return emit(args, add_help({"commands": COMMANDS, "guides": guides}, "commands"))


def cmd_help(args: argparse.Namespace) -> int:
    command = args.topic or "commands"
    if command == "all":
        payload = {"commands": COMMANDS, "guides": {name: guide_for(name) for name in COMMANDS}}
    else:
        payload = {"command": command, "guide": guide_for(command)}
    return emit(args, add_help(payload, "help"))


def cmd_paths(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    p = paths(root)
    payload = {
        "root": str(root),
        "paths": {name: str(path) for name, path in p.items()},
        "quick_commands": [
            "agentctl doctor --json",
            "agentctl run demo-agent --task \"Create preview receipt\" --workspace /aegix/scratch/demo --json",
            "agentctl index --json",
            "agentctl search-index \"rollback\" --json",
            "agentctl graph --json",
            "agentctl receipts --json",
            "agentctl events --json",
            "agentctl rollback <session_id> --json",
        ],
    }
    append_event(root, {"command": "paths", "status": "reported"})
    return emit(args, add_help(payload, "paths"))


def cmd_index(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    ensure_dirs(root)
    index_dir = root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    scopes = [Path(scope).expanduser() for scope in (args.scope or [])] or default_index_scopes(root)
    scopes = [scope if scope.is_absolute() else root / scope for scope in scopes]

    records: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    max_bytes = args.max_bytes

    for scope in scopes:
        if not scope.exists():
            skipped.append({"path": str(scope), "reason": "scope does not exist"})
            continue
        for current, dirs, files in os.walk(scope):
            dirs[:] = [name for name in dirs if name not in {".git", ".hg", ".svn", "__pycache__", "node_modules"}]
            current_path = Path(current)
            for directory in dirs:
                edges.append({"from": str(current_path), "to": str(current_path / directory), "type": "contains"})
            for filename in files:
                if len(records) >= args.max_files:
                    skipped.append({"path": str(scope), "reason": "max_files reached"})
                    break
                path = current_path / filename
                edges.append({"from": str(current_path), "to": str(path), "type": "contains"})
                try:
                    stat = path.stat()
                except OSError as exc:
                    skipped.append({"path": str(path), "reason": str(exc)})
                    continue
                text, is_text = read_text_preview(path, max_bytes)
                if not is_text:
                    record = {
                        "path": str(path),
                        "kind": file_kind(path),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "sha256": "",
                        "title": path.name,
                        "snippet": "",
                        "text_indexed": False,
                        "references": [],
                    }
                else:
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    title = lines[0].lstrip("# ").strip() if lines else path.name
                    snippet = " ".join(lines[:12])[:2000]
                    refs = extract_references(text)
                    for ref in refs:
                        edges.append({"from": str(path), "to": ref, "type": "references"})
                    record = {
                        "path": str(path),
                        "kind": file_kind(path),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "sha256": sha256_text(text),
                        "title": title,
                        "snippet": snippet,
                        "text_indexed": True,
                        "references": refs,
                    }
                records.append(record)

    files_path = index_dir / "files.jsonl"
    graph_path = index_dir / "graph.json"
    sqlite_path = index_dir / "aegix_index.sqlite"
    vector_registry_path = index_dir / "vector-registry.json"
    files_path.write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + ("\n" if records else ""), encoding="utf-8")
    graph = {
        "created_at": iso_now(),
        "root": str(root),
        "scopes": [str(scope) for scope in scopes],
        "nodes": [{"id": record["path"], "kind": record["kind"], "title": record["title"]} for record in records],
        "edges": edges,
        "summary": {
            "files_indexed": len(records),
            "text_files_indexed": sum(1 for record in records if record["text_indexed"]),
            "edges": len(edges),
            "skipped": len(skipped),
        },
    }
    write_json(graph_path, graph)
    sqlite_info = write_index_sqlite(sqlite_path, records)
    vector_registry = {
        "status": "planned",
        "purpose": "Vector DB attachment point for semantic file search over canonical file/index records.",
        "recommended_preview_backend": "qdrant",
        "collection": "aegix_files",
        "source_of_truth": str(files_path),
        "graph_source": str(graph_path),
        "embedding_status": "not-generated-in-preview-v0.2",
        "notes": [
            "Keep canonical memory in files and SQLite/JSON graph records.",
            "Use vector storage as an index, not source of truth.",
            "Do not embed secrets or credential-adjacent files without explicit policy.",
        ],
    }
    write_json(vector_registry_path, vector_registry)
    payload = {
        "status": "completed",
        "root": str(root),
        "scopes": [str(scope) for scope in scopes],
        "files_indexed": len(records),
        "text_files_indexed": graph["summary"]["text_files_indexed"],
        "edges": len(edges),
        "skipped": skipped[:50],
        "files_path": str(files_path),
        "graph_path": str(graph_path),
        "sqlite_path": str(sqlite_path),
        "vector_registry_path": str(vector_registry_path),
        **sqlite_info,
    }
    append_event(root, {"command": "index", "status": "completed", "files_indexed": len(records), "edges": len(edges)})
    return emit(args, add_help(payload, "index"))


def cmd_search_index(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    sqlite_path = root / "index" / "aegix_index.sqlite"
    matches = search_sqlite(sqlite_path, args.query, args.limit)
    payload = {
        "query": args.query,
        "matches": matches,
        "sqlite_path": str(sqlite_path),
        "index_exists": sqlite_path.exists(),
    }
    append_event(root, {"command": "search-index", "status": "searched", "query": args.query, "matches": len(matches)})
    return emit(args, add_help(payload, "search-index"))


def cmd_graph(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    graph_path = root / "index" / "graph.json"
    files_path = root / "index" / "files.jsonl"
    vector_registry_path = root / "index" / "vector-registry.json"
    graph = read_json(graph_path) or {}
    payload = {
        "summary": graph.get("summary", {}),
        "scopes": graph.get("scopes", []),
        "created_at": graph.get("created_at"),
        "graph_path": str(graph_path),
        "files_path": str(files_path),
        "sqlite_path": str(root / "index" / "aegix_index.sqlite"),
        "vector_registry_path": str(vector_registry_path),
        "graph_exists": graph_path.exists(),
    }
    append_event(root, {"command": "graph", "status": "reported", "graph_exists": graph_path.exists()})
    return emit(args, add_help(payload, "graph"))


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
    return emit(args, add_help(payload, "doctor"), 0 if status == "passed" else 1)


def cmd_caps(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    append_event(root, {"command": "caps", "status": "reported"})
    return emit(args, add_help(policy_payload(root), "caps"))


def create_preview_session(root: Path, agent: str, task: str, workspace_value: str, risk_level: str) -> dict[str, Any]:
    """Create the same preview session and receipt used by agentctl run.

    Future agents should keep state-changing workflows behind small helpers like
    this so verification can exercise the real command path without screen
    scraping CLI output.
    """
    ensure_dirs(root)
    session_id = make_session_id(agent)
    workspace = Path(workspace_value).expanduser()
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

    # The preview runner intentionally performs one tiny, inspectable write.
    # Future runners should keep this pattern: decide policy, act, verify, then
    # write a receipt that tells the next agent exactly how to inspect/rollback.
    if permitted:
        artifact_path = workspace / f"aegix-session-{session_id}.md"
        try:
            workspace.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                "\n".join(
                    [
                        f"# Aegix Preview Session {session_id}",
                        "",
                        f"- agent: {agent}",
                        f"- task: {task}",
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
        "agent": agent,
        "task": task,
        "workspace": str(workspace),
        "risk_level": risk_level,
        "created_at": created_at,
        "status": status,
        "session_dir": str(session_dir),
    }
    receipt = {
        "session_id": session_id,
        "agent": agent,
        "task": task,
        "workspace": str(workspace),
        "capabilities_used": capabilities_used,
        "actions": actions,
        "verification": verification,
        "rollback": {
            "status": "metadata-only",
            "rollback_mode": "metadata_only",
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
            "agent": agent,
            "workspace": str(workspace),
            "status": status,
        },
    )

    return {
        "session_id": session_id,
        "status": status,
        "session": session,
        "receipt": receipt,
        "session_path": str(session_path),
        "receipt_path": str(receipt_path),
    }


def cmd_run(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    payload = create_preview_session(root, args.agent, args.task, args.workspace, args.risk_level)
    return emit(args, add_help(payload, "run"), 0 if payload["status"] != "failed" else 1)


def cmd_receipts(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    payload = {"receipts": list_json_files(root / "receipts")}
    append_event(root, {"command": "receipts", "status": "listed", "count": len(payload["receipts"])})
    return emit(args, add_help(payload, "receipts"))


def cmd_events(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    payload = {"events": list_events(root, args.limit), "log_path": str(root / "logs" / "events.jsonl")}
    return emit(args, add_help(payload, "events"))


def cmd_inspect(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    session_path = root / "sessions" / args.session_id / "session.json"
    receipt_path = root / "receipts" / f"{args.session_id}.json"
    session = read_json(session_path)
    receipt = read_json(receipt_path)
    if session is None and receipt is None:
        return emit(
            args,
            add_help({
                "found": False,
                "session_id": args.session_id,
                "session_path": str(session_path),
                "receipt_path": str(receipt_path),
            }, "inspect"),
            1,
        )
    return emit(
        args,
        add_help({
            "found": True,
            "session_id": args.session_id,
            "session": session,
            "receipt": receipt,
        }, "inspect"),
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
    return emit(args, add_help({"approval": approval}, "approve"))


def cmd_approvals(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    return emit(args, add_help({"approvals": list_json_files(root / "approvals")}, "approvals"))


def create_snapshot_metadata(root: Path, session_id: str) -> dict[str, Any]:
    """Write rollback checkpoint metadata without touching user files."""
    ensure_dirs(root)
    created_at = iso_now()
    snapshot_id = f"{session_id}-{uuid.uuid4().hex[:8]}"
    snapshot_path = root / "snapshots" / f"{snapshot_id}.json"
    checkpoint_path = root / "checkpoints" / f"{snapshot_id}.json"
    snapshot = {
        "snapshot_id": snapshot_id,
        "session_id": session_id,
        "created_at": created_at,
        "status": "metadata-only",
        "rollback_mode": "metadata_only",
        "destructive_actions": False,
        "rollback_available": False,
        "session_path": str(root / "sessions" / session_id / "session.json"),
        "receipt_path": str(root / "receipts" / f"{session_id}.json"),
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
    append_event(root, {"command": "snapshot", "session_id": session_id, "status": "metadata-only"})
    return {"snapshot": snapshot, "snapshot_path": str(snapshot_path), "checkpoint_path": str(checkpoint_path)}


def cmd_snapshot(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    return emit(args, add_help(create_snapshot_metadata(root, args.session_id), "snapshot"))


def cmd_snapshots(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    return emit(args, add_help({"snapshots": list_json_files(root / "snapshots")}, "snapshots"))


def planned_rollback_payload(root: Path, session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "status": "planned",
        "rollback_mode": "metadata_only",
        "destructive_actions": False,
        "rollback_executed": False,
        "planned_behavior": [
            "load session metadata",
            "load receipt diff and snapshot reference",
            "present rollback plan for operator approval",
            "apply filesystem or declarative config rollback in a later release",
        ],
        "operator_next_step": f"inspect receipt and snapshot metadata before approving rollback for {session_id}",
        "receipt_path": str(root / "receipts" / f"{session_id}.json"),
        "note": "Preview v0.2 rollback is metadata-only and performs no filesystem restore.",
    }


def cmd_rollback(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    payload = planned_rollback_payload(root, args.session_id)
    append_event(root, {"command": "rollback", "session_id": args.session_id, "status": "planned"})
    return emit(args, add_help(payload, "rollback"))


def ensure_policy_file(root: Path) -> Path:
    policy_path = root / "policy" / "capabilities.yaml"
    if policy_path.exists():
        return policy_path
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "mode: preview-friendly",
        "allowed_without_approval:",
        *[f"  - {item}" for item in PREVIEW_POLICY["allowed_without_approval"]],
        "local_write_roots:",
        f"  - {root / 'scratch'}",
        f"  - {root / 'projects'}",
        "approval_required:",
        *[f"  - {item}" for item in PREVIEW_POLICY["approval_required"]],
        "denied_by_default:",
        *[f"  - {item}" for item in PREVIEW_POLICY["denied_by_default"]],
        "",
    ]
    policy_path.write_text("\n".join(lines), encoding="utf-8")
    return policy_path


def run_json_process(command: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "exit_code": None,
            "command": command,
            "payload": None,
            "stdout": "",
            "stderr": "",
            "error": f"{exc.__class__.__name__}: {exc}",
        }
    stdout = result.stdout.strip()
    payload = None
    error = None
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            error = f"JSONDecodeError: {exc}"
    return {
        "ok": result.returncode == 0 and payload is not None,
        "exit_code": result.returncode,
        "command": command,
        "payload": payload,
        "stdout": stdout[-4000:],
        "stderr": result.stderr.strip()[-4000:],
        "error": error,
    }


def run_agentctl_json(root: Path, args: list[str], timeout: int = 60) -> dict[str, Any]:
    return run_json_process([sys.executable, str(Path(__file__)), "--root", str(root), *args], timeout=timeout)


def aegixai_command(root: Path, args: list[str]) -> list[str] | None:
    executable = shutil.which("aegixai")
    if executable:
        return [executable, "--root", str(root), *args]
    local_script = Path(__file__).resolve().parents[1] / "aegixai" / "aegixai.py"
    if local_script.exists():
        return [sys.executable, str(local_script), "--root", str(root), *args]
    return None


def verify_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    details: dict[str, Any] | None = None,
    *,
    required: bool = True,
    warning: bool = False,
) -> bool:
    status = "passed" if passed else ("warning" if warning or not required else "failed")
    checks.append(
        {
            "name": name,
            "status": status,
            "required": required,
            "details": details or {},
        }
    )
    return passed or warning or not required


def first_file_write(receipt: dict[str, Any]) -> Path | None:
    for action in receipt.get("actions", []):
        if action.get("type") == "file.write" and action.get("path"):
            return Path(action["path"])
    return None


def validate_snapshot_links(root: Path) -> dict[str, Any]:
    snapshots = list_json_files(root / "snapshots")
    invalid = []
    for snapshot in snapshots:
        session_id = snapshot.get("session_id")
        if not session_id:
            invalid.append({"snapshot_id": snapshot.get("snapshot_id"), "reason": "missing session_id"})
            continue
        session_path = root / "sessions" / session_id / "session.json"
        receipt_path = root / "receipts" / f"{session_id}.json"
        if not session_path.exists() or not receipt_path.exists():
            invalid.append(
                {
                    "snapshot_id": snapshot.get("snapshot_id"),
                    "session_id": session_id,
                    "session_exists": session_path.exists(),
                    "receipt_exists": receipt_path.exists(),
                }
            )
    return {"snapshots_checked": len(snapshots), "invalid": invalid}


def validate_session_receipts(root: Path) -> dict[str, Any]:
    missing = []
    session_paths = sorted((root / "sessions").glob("*/session.json"))
    for session_path in session_paths:
        session_id = session_path.parent.name
        receipt_path = root / "receipts" / f"{session_id}.json"
        if not receipt_path.exists():
            missing.append({"session_id": session_id, "receipt_path": str(receipt_path)})
    return {"sessions_checked": len(session_paths), "missing_receipts": missing}


def cmd_verify(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    ensure_dirs(root)
    policy_path = ensure_policy_file(root)
    report_id = f"{utc_now().strftime('%Y%m%dT%H%M%SZ')}-verify-{uuid.uuid4().hex[:8]}"
    report_path = root / "logs" / "verify" / f"{report_id}.json"
    checks: list[dict[str, Any]] = []

    required_paths = [
        root,
        root / "scratch",
        root / "projects",
        root / "sessions",
        root / "receipts",
        root / "approvals",
        root / "snapshots",
        root / "checkpoints",
        root / "logs",
        root / "logs" / "verify",
        root / "index",
        root / "policy",
        policy_path,
    ]
    missing_paths = [str(path) for path in required_paths if not path.exists()]
    verify_check(checks, "required_paths", not missing_paths, {"missing": missing_paths})

    doctor = run_agentctl_json(root, ["doctor", "--json"], timeout=45)
    doctor_payload = doctor.get("payload") or {}
    doctor_failed_units = doctor_payload.get("checks", {}).get("systemd_failed", {}).get("failed_count")
    doctor_failed = bool(doctor_payload.get("writable_failures")) or (
        doctor_failed_units not in (0, None)
    )
    verify_check(
        checks,
        "doctor",
        doctor.get("payload") is not None and not doctor_failed,
        {
            "exit_code": doctor.get("exit_code"),
            "doctor_status": doctor_payload.get("status"),
            "writable_failures": doctor_payload.get("writable_failures"),
            "systemd_failed_count": doctor_failed_units,
            "error": doctor.get("error"),
        },
        warning=doctor.get("payload") is not None and doctor_failed_units is None and not doctor_payload.get("writable_failures"),
    )

    caps = policy_payload(root)
    verify_check(
        checks,
        "capabilities_policy",
        "service.restart" in caps["approval_required"] and str(root / "scratch") in caps["local_write_roots"],
        {
            "mode": caps["mode"],
            "local_write_roots": caps["local_write_roots"],
            "approval_required": caps["approval_required"],
            "policy_file": str(policy_path),
        },
    )

    workspace = root / "scratch" / "verify" / report_id
    session_payload = create_preview_session(
        root,
        "verify-agent",
        "Verify rollback readiness and AI-first control-plane features",
        str(workspace),
        "L1",
    )
    session_id = session_payload["session_id"]
    receipt = session_payload["receipt"]
    artifact_path = first_file_write(receipt)
    artifact_before = artifact_path.read_text(encoding="utf-8") if artifact_path and artifact_path.exists() else None
    verify_check(
        checks,
        "session_and_receipt",
        session_payload["status"] == "completed"
        and Path(session_payload["session_path"]).exists()
        and Path(session_payload["receipt_path"]).exists(),
        {
            "session_id": session_id,
            "session_path": session_payload["session_path"],
            "receipt_path": session_payload["receipt_path"],
            "artifact_path": str(artifact_path) if artifact_path else None,
            "status": session_payload["status"],
        },
    )

    approval = run_agentctl_json(
        root,
        ["approve", session_id, "--cap", "service.restart:ollama", "--reason", "verify approval scaffold", "--json"],
        timeout=30,
    )
    approval_payload = approval.get("payload") or {}
    verify_check(
        checks,
        "approval_scaffold",
        approval_payload.get("approval", {}).get("execution_enabled") is False,
        {
            "exit_code": approval.get("exit_code"),
            "approval": approval_payload.get("approval"),
            "error": approval.get("error"),
        },
    )

    snapshot_payload = create_snapshot_metadata(root, session_id)
    snapshot = snapshot_payload["snapshot"]
    verify_check(
        checks,
        "snapshot_metadata",
        snapshot.get("session_id") == session_id
        and snapshot.get("rollback_mode") == "metadata_only"
        and Path(snapshot_payload["snapshot_path"]).exists()
        and Path(snapshot_payload["checkpoint_path"]).exists(),
        snapshot_payload,
    )

    rollback_payload = planned_rollback_payload(root, session_id)
    append_event(root, {"command": "rollback", "session_id": session_id, "status": "planned", "source": "verify"})
    artifact_after = artifact_path.read_text(encoding="utf-8") if artifact_path and artifact_path.exists() else None
    verify_check(
        checks,
        "rollback_metadata_only",
        rollback_payload.get("rollback_mode") == "metadata_only"
        and rollback_payload.get("rollback_executed") is False
        and artifact_before == artifact_after,
        {
            "rollback": rollback_payload,
            "artifact_path": str(artifact_path) if artifact_path else None,
            "artifact_preserved": artifact_before == artifact_after,
        },
    )

    receipt_validation = validate_session_receipts(root)
    verify_check(
        checks,
        "session_receipt_links",
        not receipt_validation["missing_receipts"],
        receipt_validation,
    )

    snapshot_validation = validate_snapshot_links(root)
    verify_check(
        checks,
        "snapshot_session_links",
        not snapshot_validation["invalid"],
        snapshot_validation,
    )

    index_result = run_agentctl_json(
        root,
        ["index", "--scope", str(root / "scratch"), "--max-files", "500", "--json"],
        timeout=60,
    )
    index_payload = index_result.get("payload") or {}
    verify_check(
        checks,
        "file_index",
        index_payload.get("status") == "completed"
        and Path(index_payload.get("graph_path", "")).exists()
        and Path(index_payload.get("sqlite_path", "")).exists(),
        {
            "exit_code": index_result.get("exit_code"),
            "files_indexed": index_payload.get("files_indexed"),
            "graph_path": index_payload.get("graph_path"),
            "sqlite_path": index_payload.get("sqlite_path"),
            "vector_registry_path": index_payload.get("vector_registry_path"),
            "error": index_result.get("error"),
        },
    )

    search_result = run_agentctl_json(root, ["search-index", "Preview", "--limit", "5", "--json"], timeout=30)
    search_payload = search_result.get("payload") or {}
    verify_check(
        checks,
        "file_index_search",
        bool(search_payload.get("index_exists")) and len(search_payload.get("matches", [])) >= 1,
        {
            "exit_code": search_result.get("exit_code"),
            "matches": len(search_payload.get("matches", [])),
            "sqlite_path": search_payload.get("sqlite_path"),
            "error": search_result.get("error"),
        },
    )

    graph_result = run_agentctl_json(root, ["graph", "--json"], timeout=30)
    graph_payload = graph_result.get("payload") or {}
    verify_check(
        checks,
        "file_graph",
        graph_payload.get("graph_exists") is True and graph_payload.get("summary", {}).get("files_indexed", 0) >= 1,
        {
            "exit_code": graph_result.get("exit_code"),
            "summary": graph_payload.get("summary"),
            "graph_path": graph_payload.get("graph_path"),
            "error": graph_result.get("error"),
        },
    )

    events = list_events(root, 50)
    verify_check(checks, "event_log", len(events) >= 1, {"events_seen": len(events), "log_path": str(root / "logs" / "events.jsonl")})

    ai_status_cmd = aegixai_command(root, ["status", "--json"])
    if ai_status_cmd is None:
        verify_check(checks, "aegixai_status", False, {"error": "aegixai command not found"})
        ai_status = {"payload": None}
    else:
        ai_status = run_json_process(ai_status_cmd, timeout=20)
        ai_status_payload = ai_status.get("payload") or {}
        verify_check(
            checks,
            "aegixai_status",
            ai_status_payload.get("command") == "status",
            {
                "exit_code": ai_status.get("exit_code"),
                "ollama_available": ai_status_payload.get("ollama_available"),
                "model_present": ai_status_payload.get("model_present"),
                "error": ai_status_payload.get("error") or ai_status.get("error"),
            },
            warning=ai_status.get("payload") is not None and not ai_status_payload.get("ollama_available"),
        )

    ai_diagnose_cmd = aegixai_command(root, ["diagnose", "--json"])
    if ai_diagnose_cmd is None:
        verify_check(checks, "aegixai_diagnose", False, {"error": "aegixai command not found"})
    else:
        ai_diagnose = run_json_process(ai_diagnose_cmd, timeout=75)
        ai_diagnose_payload = ai_diagnose.get("payload") or {}
        verify_check(
            checks,
            "aegixai_diagnose",
            ai_diagnose_payload.get("command") == "diagnose",
            {
                "exit_code": ai_diagnose.get("exit_code"),
                "ollama_available": ai_diagnose_payload.get("ollama_available"),
                "likely_issue": ai_diagnose_payload.get("likely_issue"),
                "error": ai_diagnose_payload.get("ollama_error") or ai_diagnose.get("error"),
            },
            warning=ai_diagnose.get("payload") is not None and not ai_diagnose_payload.get("ollama_available"),
        )

    ai_command_cmd = aegixai_command(
        root,
        ["--timeout", "1", "--num-predict", "24", "command", "inspect the system", "--json"],
    )
    if ai_command_cmd is None:
        verify_check(checks, "aegixai_command_safety", False, {"error": "aegixai command not found"})
    else:
        ai_command = run_json_process(ai_command_cmd, timeout=10)
        ai_command_payload = ai_command.get("payload") or {}
        verify_check(
            checks,
            "aegixai_command_safety",
            ai_command_payload.get("command") == "command" and ai_command_payload.get("executed") is False,
            {
                "exit_code": ai_command.get("exit_code"),
                "executed": ai_command_payload.get("executed"),
                "error": ai_command_payload.get("error") or ai_command.get("error"),
            },
            warning=ai_command.get("payload") is not None and ai_command_payload.get("executed") is False,
        )

    failed = [check for check in checks if check["status"] == "failed" and check["required"]]
    warnings = [check for check in checks if check["status"] == "warning"]
    status = "passed" if not failed else "failed"
    report = {
        "command": "verify",
        "status": status,
        "version": VERSION,
        "root": str(root),
        "report_id": report_id,
        "created_at": iso_now(),
        "session_id": session_id,
        "rollback_mode": "metadata_only",
        "checks": checks,
        "summary": {
            "passed": sum(1 for check in checks if check["status"] == "passed"),
            "warnings": len(warnings),
            "failed": len(failed),
        },
        "report_path": str(report_path),
        "operator_next_steps": [
            f"agentctl inspect {session_id} --json",
            f"agentctl rollback {session_id} --json",
            "agentctl receipts --json",
        ],
    }
    write_json(report_path, report)
    append_event(
        root,
        {
            "command": "verify",
            "status": status,
            "report_id": report_id,
            "session_id": session_id,
            "warnings": len(warnings),
            "failed": len(failed),
            "report_path": str(report_path),
        },
    )
    return emit(args, add_help(report, "verify"), 0 if status == "passed" else 1)


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
    return emit(args, add_help(payload, command))


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentctl",
        description=CLI_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Agent prompt:
  1. Start with: agentctl doctor --json
  2. Find paths: agentctl paths --json
  3. Check policy: agentctl caps --json
  4. Run scoped work: agentctl run demo-agent --task "..." --workspace /aegix/scratch/demo --json
  5. Inspect evidence: agentctl receipts --json

Use agentctl help <command> --json for command-specific guidance.
""",
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Aegix root path")
    add_json_flag(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show Aegix status")
    add_json_flag(status)
    status.set_defaults(func=cmd_status)

    commands = subparsers.add_parser("commands", help="list available commands")
    add_json_flag(commands)
    commands.set_defaults(func=cmd_commands)

    help_cmd = subparsers.add_parser("help", help="show command-specific agent guidance")
    help_cmd.add_argument("topic", nargs="?", help="command name, or 'all'")
    add_json_flag(help_cmd)
    help_cmd.set_defaults(func=cmd_help)

    doctor = subparsers.add_parser(
        "doctor",
        help="run preview health checks",
        description=guide_for("doctor")["intent"],
        epilog=f"Example: {guide_for('doctor')['example']}",
    )
    add_json_flag(doctor)
    doctor.set_defaults(func=cmd_doctor)

    path_cmd = subparsers.add_parser(
        "paths",
        help="show Aegix control-plane paths",
        description=guide_for("paths")["intent"],
        epilog=f"Example: {guide_for('paths')['example']}",
    )
    add_json_flag(path_cmd)
    path_cmd.set_defaults(func=cmd_paths)

    index = subparsers.add_parser(
        "index",
        help="build the local file graph and text index",
        description=guide_for("index")["intent"],
        epilog=f"Example: {guide_for('index')['example']}",
    )
    index.add_argument("--scope", action="append", help="Path to index. May be repeated.")
    index.add_argument("--max-files", type=int, default=5000, help="Maximum files to index in this run.")
    index.add_argument("--max-bytes", type=int, default=65536, help="Maximum bytes read from each text file.")
    add_json_flag(index)
    index.set_defaults(func=cmd_index)

    search_index = subparsers.add_parser(
        "search-index",
        help="search the local file index",
        description=guide_for("search-index")["intent"],
        epilog=f"Example: {guide_for('search-index')['example']}",
    )
    search_index.add_argument("query", help="Search query.")
    search_index.add_argument("--limit", type=int, default=20)
    add_json_flag(search_index)
    search_index.set_defaults(func=cmd_search_index)

    graph = subparsers.add_parser(
        "graph",
        help="show file graph summary",
        description=guide_for("graph")["intent"],
        epilog=f"Example: {guide_for('graph')['example']}",
    )
    add_json_flag(graph)
    graph.set_defaults(func=cmd_graph)

    run = subparsers.add_parser(
        "run",
        help="run a preview-safe agent session",
        description=guide_for("run")["intent"],
        epilog=f"Example: {guide_for('run')['example']}",
    )
    run.add_argument("agent", help="agent name")
    run.add_argument("--task", required=True, help="task text")
    run.add_argument("--workspace", required=True, help="workspace path")
    run.add_argument("--risk-level", default="L1", help="risk level label")
    add_json_flag(run)
    run.set_defaults(func=cmd_run)

    receipts = subparsers.add_parser("receipts", help="list receipts", epilog=f"Example: {guide_for('receipts')['example']}")
    add_json_flag(receipts)
    receipts.set_defaults(func=cmd_receipts)

    events = subparsers.add_parser("events", help="show recent Aegix event log entries", epilog=f"Example: {guide_for('events')['example']}")
    events.add_argument("--limit", type=int, default=25)
    add_json_flag(events)
    events.set_defaults(func=cmd_events)

    inspect = subparsers.add_parser("inspect", help="inspect a session", epilog=f"Example: {guide_for('inspect')['example']}")
    inspect.add_argument("session_id", help="session id")
    add_json_flag(inspect)
    inspect.set_defaults(func=cmd_inspect)

    caps = subparsers.add_parser("caps", help="show preview capability policy", epilog=f"Example: {guide_for('caps')['example']}")
    add_json_flag(caps)
    caps.set_defaults(func=cmd_caps)

    approve = subparsers.add_parser("approve", help="create approval token metadata", epilog=f"Example: {guide_for('approve')['example']}")
    approve.add_argument("session_id", help="session id")
    approve.add_argument("--cap", required=True, help="capability to approve")
    approve.add_argument("--approver", default=os.environ.get("USER") or os.environ.get("USERNAME") or "operator")
    approve.add_argument("--ttl-minutes", type=int, default=60)
    approve.add_argument("--reason", default="preview approval scaffold")
    add_json_flag(approve)
    approve.set_defaults(func=cmd_approve)

    approvals = subparsers.add_parser("approvals", help="list approval metadata", epilog=f"Example: {guide_for('approvals')['example']}")
    add_json_flag(approvals)
    approvals.set_defaults(func=cmd_approvals)

    snapshot = subparsers.add_parser("snapshot", help="create snapshot metadata", epilog=f"Example: {guide_for('snapshot')['example']}")
    snapshot.add_argument("session_id", help="session id")
    add_json_flag(snapshot)
    snapshot.set_defaults(func=cmd_snapshot)

    snapshots = subparsers.add_parser("snapshots", help="list snapshot metadata", epilog=f"Example: {guide_for('snapshots')['example']}")
    add_json_flag(snapshots)
    snapshots.set_defaults(func=cmd_snapshots)

    rollback = subparsers.add_parser("rollback", help="show planned rollback behavior", epilog=f"Example: {guide_for('rollback')['example']}")
    rollback.add_argument("session_id", help="session id")
    add_json_flag(rollback)
    rollback.set_defaults(func=cmd_rollback)

    verify = subparsers.add_parser(
        "verify",
        help="run Preview v0.2 control-plane verification",
        description=guide_for("verify")["intent"],
        epilog=f"Example: {guide_for('verify')['example']}",
    )
    add_json_flag(verify)
    verify.set_defaults(func=cmd_verify)

    for command in COMMANDS:
        if command in {
            "status",
            "commands",
            "help",
            "doctor",
            "paths",
            "index",
            "search-index",
            "graph",
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
            "verify",
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
