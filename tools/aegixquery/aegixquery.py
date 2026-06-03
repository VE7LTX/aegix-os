#!/usr/bin/env python3
"""Aegix terminal-to-local-AI query helper."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(os.environ.get("AEGIX_ROOT", "/aegix"))
DEFAULT_MODEL = os.environ.get("AEGIX_AI_MODEL", "qwen2.5:0.5b")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_TIMEOUT = int(os.environ.get("AEGIX_AI_TIMEOUT", "600"))
DEFAULT_NUM_PREDICT = int(os.environ.get("AEGIX_AI_NUM_PREDICT", "192"))
DEFAULT_CONTEXT_FILE = os.environ.get("AEGIX_QUERY_CONTEXT_FILE")
DEFAULT_CHAT_CMD = os.environ.get("AEGIX_QUERY_CHAT_CMD") or os.environ.get("AEGIX_QUERY_AEGIXAI")


def split_command(value: str | None) -> list[str] | None:
    if not value:
        return None
    tokens = shlex.split(value, posix=os.name != "nt")
    return [token.strip('"').strip("'") for token in tokens if token.strip('"').strip("'")]


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return value.strip("-") or "query"


def root_from_args(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "root", DEFAULT_ROOT)).expanduser()


def obsidian_vault(root: Path) -> Path:
    return Path(os.environ.get("AEGIX_OBSIDIAN_VAULT", str(root / "notes" / "obsidian"))).expanduser()


def terminal_tail_path(root: Path) -> Path:
    return root / "logs" / "terminal-tail.md"


def chat_log_path(vault: Path, prompt: str) -> Path:
    chat_dir = vault / "90-terminal-chat"
    chat_dir.mkdir(parents=True, exist_ok=True)
    stamp = iso_now().replace(":", "-")
    return chat_dir / f"{stamp}-{slugify(prompt[:40])}.md"


def redact(text: str) -> str:
    patterns = [
        (re.compile(r"(?i)\b(password|token|secret|apikey|api_key|auth|credential|passphrase)\s*=\s*\S+"), r"\1=[REDACTED]"),
        (re.compile(r"(?i)\b(password|token|secret|apikey|api_key|auth|credential|passphrase)\b.*"), "[REDACTED SENSITIVE LINE]"),
        (re.compile(r"(?i)(ghp_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+|xox[pbar]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16})"), "[REDACTED]"),
    ]
    redacted = text
    for pattern, replacement in patterns:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return default


def build_context(root: Path, prompt: str, tail_text: str, history_text: str) -> str:
    parts = [
        "# Terminal Context",
        "",
        f"- captured_at: {iso_now()}",
        f"- cwd: {os.getcwd()}",
        f"- user: {os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'}",
        f"- root: {root}",
        f"- model: {DEFAULT_MODEL}",
        "",
        "## Prompt",
        "",
        prompt.strip(),
    ]
    if tail_text.strip():
        parts.extend(["", "## Terminal Tail", "", tail_text.strip()])
    if history_text.strip():
        parts.extend(["", "## Recent History", "", history_text.strip()])
    return "\n".join(parts).strip() + "\n"


def prompt_requests_telemetry(prompt: str) -> bool:
    return bool(re.search(r"\b(ram|memory|load|uptime|swap)\b", prompt, re.IGNORECASE))


def telemetry_context(telemetry: dict[str, Any]) -> str:
    return "\n".join(
        [
            "## Prefetched Local Telemetry",
            "",
            json.dumps(telemetry, indent=2, sort_keys=True),
        ]
    )


def format_telemetry_answer(telemetry: dict[str, Any]) -> str:
    total = telemetry.get("ram_total_bytes")
    available = telemetry.get("ram_available_bytes")
    used = telemetry.get("ram_used_bytes")
    loadavg = telemetry.get("loadavg") or []
    parts = [
        f"RAM used: {human_bytes(used)}",
        f"RAM total: {human_bytes(total)}",
    ]
    if available is not None:
        parts.append(f"RAM available: {human_bytes(available)}")
    if loadavg:
        parts.append("Load average: " + ", ".join(f"{value:.2f}" for value in loadavg[:3]))
    return "\n".join(parts)


def write_tail_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def human_bytes(value: int | None) -> str:
    if value is None:
        return "unknown"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    num = float(value)
    for unit in units:
        if num < 1024 or unit == units[-1]:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{value} B"


def parse_meminfo() -> dict[str, int]:
    meminfo: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            if not value:
                continue
            match = re.search(r"(\d+)", value)
            if match:
                meminfo[key] = int(match.group(1)) * 1024
    except OSError:
        return {}
    return meminfo


def collect_telemetry(args: dict[str, Any] | None = None) -> dict[str, Any]:
    override_json = os.environ.get("AEGIX_QUERY_TELEMETRY_JSON")
    if args and args.get("override_json"):
        override_json = str(args["override_json"])
    if override_json:
        try:
            return json.loads(override_json)
        except json.JSONDecodeError:
            pass
    meminfo = parse_meminfo()
    total = meminfo.get("MemTotal")
    available = meminfo.get("MemAvailable")
    used = (total - available) if total is not None and available is not None else None
    loadavg = []
    try:
        loadavg = [float(part) for part in Path("/proc/loadavg").read_text(encoding="utf-8").split()[:3]]
    except OSError:
        loadavg = []
    uptime = None
    try:
        uptime = Path("/proc/uptime").read_text(encoding="utf-8").split()[0]
    except OSError:
        uptime = None
    return {
        "ram_total_bytes": total,
        "ram_available_bytes": available,
        "ram_used_bytes": used,
        "loadavg": loadavg,
        "uptime_seconds": float(uptime) if uptime else None,
        "source": "procfs",
    }


def local_tool_command(executable_name: str, script_relative: str) -> list[str] | None:
    executable = shutil.which(executable_name)
    if executable:
        return [executable]
    local_script = Path(__file__).resolve().parents[1] / script_relative
    if local_script.exists():
        return [sys.executable, str(local_script)]
    return None


def find_agentctl() -> list[str] | None:
    return local_tool_command("agentctl", "agentctl/agentctl.py")


def find_aegixai() -> list[str] | None:
    return local_tool_command("aegixai", "aegixai/aegixai.py")


def command_result(command: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit_code": None, "error": f"{exc.__class__.__name__}: {exc}"}


def systemctl_status(unit: str) -> dict[str, Any]:
    return command_result(["systemctl", "status", unit, "--no-pager", "--plain"])


def systemctl_failed() -> dict[str, Any]:
    return command_result(["systemctl", "--failed", "--no-pager", "--plain"])


def agentctl_json(root: Path, args: list[str], timeout: int = 60) -> dict[str, Any]:
    cmd = local_tool_command("agentctl", "agentctl/agentctl.py")
    if cmd is None:
        return {"error": "agentctl not found"}
    result = subprocess.run([*cmd, "--root", str(root), *args, "--json"], capture_output=True, text=True, check=False, timeout=timeout)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "exit_code": result.returncode}
    return payload


def obsidianctl_json(args: list[str], timeout: int = 60) -> dict[str, Any]:
    cmd = local_tool_command("obsidianctl", "obsidianctl/obsidianctl.py")
    if cmd is None:
        return {"error": "obsidianctl not found"}
    result = subprocess.run([*cmd, *args, "--json"], capture_output=True, text=True, check=False, timeout=timeout)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "exit_code": result.returncode}


def aegixai_json(args: list[str], timeout: int = 120) -> dict[str, Any]:
    cmd = find_aegixai()
    if cmd is None:
        return {"error": "aegixai not found"}
    result = subprocess.run([*cmd, *args, "--json"], capture_output=True, text=True, check=False, timeout=timeout)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "exit_code": result.returncode}


def secretsctl_json(args: list[str], timeout: int = 30) -> dict[str, Any]:
    cmd = local_tool_command("secretsctl", "secretsctl/secretsctl.py")
    if cmd is None:
        return {"error": "secretsctl not found"}
    result = subprocess.run([*cmd, *args, "--json"], capture_output=True, text=True, check=False, timeout=timeout)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "exit_code": result.returncode}


def tool_catalog() -> list[dict[str, Any]]:
    return [
        {"name": "procfs.telemetry", "description": "Read RAM, load average, and uptime from procfs.", "arguments": {"override_json": "string?"}},
        {"name": "terminal.tail", "description": "Read the current terminal tail note.", "arguments": {}},
        {"name": "agentctl.status", "description": "Show Aegix status and counts.", "arguments": {}},
        {"name": "agentctl.commands", "description": "List the command surface and guidance.", "arguments": {}},
        {"name": "agentctl.help", "description": "Show help for one Aegix command topic.", "arguments": {"topic": "string?"}},
        {"name": "agentctl.doctor", "description": "Run health checks for the Aegix preview control plane.", "arguments": {}},
        {"name": "agentctl.paths", "description": "Show stable Aegix paths.", "arguments": {}},
        {"name": "agentctl.index", "description": "Build the file index.", "arguments": {"scope": "string?", "max_files": "integer?", "max_bytes": "integer?"}},
        {"name": "agentctl.search_index", "description": "Search the local file index.", "arguments": {"query": "string", "limit": "integer?"}},
        {"name": "agentctl.graph", "description": "Show file graph summary.", "arguments": {}},
        {"name": "agentctl.run", "description": "Create a preview-safe session and receipt.", "arguments": {"agent": "string", "task": "string", "workspace": "string", "risk_level": "string?"}},
        {"name": "agentctl.inspect", "description": "Inspect a session and receipt by session id.", "arguments": {"session_id": "string"}},
        {"name": "agentctl.receipts", "description": "List receipts.", "arguments": {}},
        {"name": "agentctl.events", "description": "Show recent Aegix events.", "arguments": {"limit": "integer?"}},
        {"name": "agentctl.caps", "description": "Show preview capability policy.", "arguments": {}},
        {"name": "agentctl.approve", "description": "Create approval metadata for a session and capability.", "arguments": {"session_id": "string", "cap": "string", "approver": "string?", "ttl_minutes": "integer?", "reason": "string?"}},
        {"name": "agentctl.approvals", "description": "List approval metadata.", "arguments": {}},
        {"name": "agentctl.snapshot", "description": "Create snapshot metadata for a session.", "arguments": {"session_id": "string"}},
        {"name": "agentctl.snapshots", "description": "List snapshot metadata.", "arguments": {}},
        {"name": "agentctl.rollback", "description": "Show planned rollback behavior for a session.", "arguments": {"session_id": "string"}},
        {"name": "agentctl.verify", "description": "Run Preview v0.2 verification checks.", "arguments": {}},
        {"name": "obsidian.path", "description": "Show the Obsidian vault path.", "arguments": {}},
        {"name": "obsidian.init", "description": "Create the standard Obsidian vault folders.", "arguments": {}},
        {"name": "obsidian.new", "description": "Create a timestamped Markdown note.", "arguments": {"title": "string", "folder": "string?"}},
        {"name": "obsidian.search", "description": "Search Obsidian memory.", "arguments": {"query": "string"}},
        {"name": "secrets.status", "description": "Show secret broker status.", "arguments": {}},
        {"name": "secrets.handles", "description": "List secret handles.", "arguments": {}},
        {"name": "secrets.policy", "description": "Show secret policy.", "arguments": {}},
        {"name": "aegixai.status", "description": "Show local model availability and loaded models.", "arguments": {}},
        {"name": "aegixai.models", "description": "List local Ollama models.", "arguments": {}},
        {"name": "aegixai.diagnose", "description": "Show local model logs and likely failure mode.", "arguments": {}},
        {"name": "aegixai.warmup", "description": "Load the model with a tiny prompt.", "arguments": {}},
        {"name": "systemctl.status", "description": "Show a systemd unit status.", "arguments": {"unit": "string"}},
        {"name": "systemctl.failed", "description": "Show failed systemd units.", "arguments": {}},
    ]


def query_system_prompt(tool_json: str) -> str:
    return "\n".join(
        [
            "You are Aegix Native, a local terminal assistant with tool access.",
            "You must answer by choosing tools when needed instead of guessing.",
            "Use tools directly for system state, memory, files, receipts, and local services.",
            "Prefer these tool families when relevant:",
            "- procfs.telemetry for RAM, load, and uptime",
            "- agentctl.* for status, docs, indexing, receipts, sessions, approvals, snapshots, rollback, and verify",
            "- obsidian.* for durable Markdown memory",
            "- secrets.* for handle-based secret metadata only",
            "- aegixai.* for local model and Ollama health",
            "- systemctl.* for local unit status and failed services",
            "Reply with JSON only.",
            "Schema:",
            '{"tool_calls":[{"name":"tool.name","arguments":{}}],"final_answer":null}',
            '{"tool_calls":[],"final_answer":"answer text"}',
            "If you need more information, call tools. If you already have enough, set tool_calls to an empty list and provide final_answer.",
            "Never claim a tool result you did not observe.",
            "Available tools:",
            tool_json,
        ]
    )


def chat_backend_request(messages: list[dict[str, Any]], model: str, ollama_url: str, timeout: int, num_predict: int) -> dict[str, Any]:
    command = split_command(DEFAULT_CHAT_CMD)
    request = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": num_predict,
            "temperature": 0.2,
        },
    }
    if command:
        try:
            completed = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True, check=False, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            return {"error": f"TimeoutExpired: {exc}"}
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {"message": {"content": completed.stdout.strip()}, "stderr": completed.stderr.strip(), "exit_code": completed.returncode}
    try:
        import urllib.request

        req = urllib.request.Request(
            ollama_url.rstrip("/") + "/api/chat",
            data=json.dumps(request).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"error": f"{exc.__class__.__name__}: {exc}"}


def parse_json_text(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def tool_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    arguments = tool_call.get("arguments") or {}
    return arguments if isinstance(arguments, dict) else {}


def execute_tool(root: Path, tool_call: dict[str, Any], tail_path: Path) -> dict[str, Any]:
    name = tool_call.get("name")
    arguments = tool_arguments(tool_call)
    if name == "procfs.telemetry":
        return collect_telemetry(arguments if isinstance(arguments, dict) else {})
    if name == "terminal.tail":
        return {"path": str(tail_path), "content": redact(read_text(tail_path))}
    if name == "agentctl.status":
        return agentctl_json(root, ["status"])
    if name == "agentctl.commands":
        return agentctl_json(root, ["commands"])
    if name == "agentctl.help":
        topic = arguments.get("topic")
        cmd = ["help"]
        if topic:
            cmd.append(str(topic))
        return agentctl_json(root, cmd)
    if name == "agentctl.doctor":
        return agentctl_json(root, ["doctor"])
    if name == "agentctl.paths":
        return agentctl_json(root, ["paths"])
    if name == "agentctl.caps":
        return agentctl_json(root, ["caps"])
    if name == "agentctl.index":
        scope = arguments.get("scope") if isinstance(arguments, dict) else None
        max_files = arguments.get("max_files") if isinstance(arguments, dict) else None
        max_bytes = arguments.get("max_bytes") if isinstance(arguments, dict) else None
        args = ["index"]
        if scope:
            args.extend(["--scope", str(scope)])
        if max_files:
            args.extend(["--max-files", str(max_files)])
        if max_bytes:
            args.extend(["--max-bytes", str(max_bytes)])
        return agentctl_json(root, args)
    if name == "agentctl.search_index":
        query = arguments.get("query") if isinstance(arguments, dict) else None
        limit = arguments.get("limit") if isinstance(arguments, dict) else None
        if not query:
            return {"error": "missing query"}
        args = ["search-index", str(query)]
        if limit:
            args.extend(["--limit", str(limit)])
        return agentctl_json(root, args)
    if name == "agentctl.graph":
        return agentctl_json(root, ["graph"])
    if name == "agentctl.run":
        agent = arguments.get("agent") if isinstance(arguments, dict) else None
        task = arguments.get("task") if isinstance(arguments, dict) else None
        workspace = arguments.get("workspace") if isinstance(arguments, dict) else None
        risk_level = arguments.get("risk_level") if isinstance(arguments, dict) else None
        if not agent or not task or not workspace:
            return {"error": "missing agent, task, or workspace"}
        cmd = ["run", str(agent), "--task", str(task), "--workspace", str(workspace)]
        if risk_level:
            cmd.extend(["--risk-level", str(risk_level)])
        return agentctl_json(root, cmd)
    if name == "agentctl.inspect":
        session_id = arguments.get("session_id") if isinstance(arguments, dict) else None
        if not session_id:
            return {"error": "missing session_id"}
        return agentctl_json(root, ["inspect", str(session_id)])
    if name == "agentctl.events":
        limit = arguments.get("limit") if isinstance(arguments, dict) else None
        args = ["events"]
        if limit:
            args.extend(["--limit", str(limit)])
        return agentctl_json(root, args)
    if name == "agentctl.receipts":
        return agentctl_json(root, ["receipts"])
    if name == "agentctl.approve":
        session_id = arguments.get("session_id") if isinstance(arguments, dict) else None
        cap = arguments.get("cap") if isinstance(arguments, dict) else None
        if not session_id or not cap:
            return {"error": "missing session_id or cap"}
        cmd = ["approve", str(session_id), "--cap", str(cap)]
        if arguments.get("approver"):
            cmd.extend(["--approver", str(arguments["approver"])])
        if arguments.get("ttl_minutes"):
            cmd.extend(["--ttl-minutes", str(arguments["ttl_minutes"])])
        if arguments.get("reason"):
            cmd.extend(["--reason", str(arguments["reason"])])
        return agentctl_json(root, cmd)
    if name == "agentctl.approvals":
        return agentctl_json(root, ["approvals"])
    if name == "agentctl.snapshot":
        session_id = arguments.get("session_id") if isinstance(arguments, dict) else None
        if not session_id:
            return {"error": "missing session_id"}
        return agentctl_json(root, ["snapshot", str(session_id)])
    if name == "agentctl.snapshots":
        return agentctl_json(root, ["snapshots"])
    if name == "agentctl.rollback":
        session_id = arguments.get("session_id") if isinstance(arguments, dict) else None
        if not session_id:
            return {"error": "missing session_id"}
        return agentctl_json(root, ["rollback", str(session_id)])
    if name == "agentctl.verify":
        return agentctl_json(root, ["verify"])
    if name == "obsidian.path":
        return obsidianctl_json(["path"])
    if name == "obsidian.init":
        return obsidianctl_json(["init"])
    if name == "obsidian.new":
        title = arguments.get("title") if isinstance(arguments, dict) else None
        folder = arguments.get("folder") if isinstance(arguments, dict) else None
        if not title:
            return {"error": "missing title"}
        cmd = ["new", str(title)]
        if folder:
            cmd.extend(["--folder", str(folder)])
        return obsidianctl_json(cmd)
    if name == "obsidian.search":
        query = arguments.get("query") if isinstance(arguments, dict) else None
        if not query:
            return {"error": "missing query"}
        return obsidianctl_json(["search", str(query)])
    if name == "secrets.status":
        return secretsctl_json(["status"])
    if name == "secrets.handles":
        return secretsctl_json(["handles"])
    if name == "secrets.policy":
        return secretsctl_json(["policy"])
    if name == "aegixai.status":
        return aegixai_json(["status"])
    if name == "aegixai.models":
        return aegixai_json(["models"])
    if name == "aegixai.diagnose":
        return aegixai_json(["diagnose"])
    if name == "aegixai.warmup":
        return aegixai_json(["warmup"])
    if name == "systemctl.status":
        unit = arguments.get("unit") if isinstance(arguments, dict) else None
        if not unit:
            return {"error": "missing unit"}
        return systemctl_status(str(unit))
    if name == "systemctl.failed":
        return systemctl_failed()
    return {"error": f"unknown tool: {name}"}


def run_tool_loop(
    root: Path,
    prompt: str,
    tail_path: Path,
    tail_text: str,
    history_text: str,
    prefetch_text: str,
    model: str,
    ollama_url: str,
    timeout: int,
    num_predict: int,
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    tool_json = json.dumps(tool_catalog(), indent=2, sort_keys=True)
    context_text = build_context(root, prompt, tail_text, history_text)
    if prefetch_text.strip():
        context_text = context_text + "\n" + prefetch_text.strip() + "\n"
    messages = [
        {"role": "system", "content": query_system_prompt(tool_json)},
        {"role": "user", "content": context_text},
    ]
    trace: list[dict[str, Any]] = []
    last_response: dict[str, Any] = {}

    for _ in range(4):
        last_response = chat_backend_request(messages, model, ollama_url, timeout, num_predict)
        if last_response.get("error"):
            return "", trace, last_response
        message = last_response.get("message") or {}
        content = (message.get("content") or "").strip()
        parsed = parse_json_text(content)
        if parsed is None:
            return content, trace, last_response
        tool_calls = parsed.get("tool_calls") or []
        final_answer = parsed.get("final_answer")
        if tool_calls:
            observations = []
            for call in tool_calls:
                observation = execute_tool(root, call, tail_path=tail_path)
                observations.append({"call": call, "observation": observation})
                trace.append({"call": call, "observation": observation})
            messages.append({"role": "assistant", "content": json.dumps(parsed, indent=2, sort_keys=True)})
            messages.append(
                {
                    "role": "user",
                    "content": "Tool observations:\n" + json.dumps(observations, indent=2, sort_keys=True) + "\nReturn JSON with tool_calls as an empty list and final_answer as the user-facing answer.",
                }
            )
            continue
        if final_answer:
            return str(final_answer), trace, last_response
        return content, trace, last_response
    return "", trace, last_response


def write_chat_note(
    vault: Path,
    prompt: str,
    tail_text: str,
    response: str,
    model: str,
    root: Path,
    tool_trace: list[dict[str, Any]] | None = None,
) -> Path:
    note_path = chat_log_path(vault, prompt)
    note = [
        "---",
        f"created_at: {iso_now()}",
        f"model: {model}",
        f"root: {root}",
        f"prompt: {json.dumps(prompt)}",
        "source: aegix-query",
        "tags:",
        "  - terminal-chat",
        "  - local-ai",
        "---",
        "",
        "# Prompt",
        "",
        prompt.strip(),
        "",
        "# Context",
        "",
        tail_text.strip() or "_No saved terminal tail context._",
    ]
    if tool_trace:
        note.extend(
            [
                "",
                "# Tool Trace",
                "",
                "```json",
                json.dumps(tool_trace, indent=2, sort_keys=True),
                "```",
            ]
        )
    note.extend(
        [
            "",
            "# Response",
            "",
            response.strip() or "_No response text._",
            "",
        ]
    )
    note_path.write_text("\n".join(note), encoding="utf-8")
    return note_path


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def emit(args: argparse.Namespace, payload: dict[str, Any], exit_code: int = 0) -> int:
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        output = payload.get("response") or payload.get("error") or ""
        print(output)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aegix-query",
        description="Send a short shell query plus terminal context to the local Aegix model.",
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--num-predict", type=int, default=DEFAULT_NUM_PREDICT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--context-file", default=DEFAULT_CONTEXT_FILE)
    parser.add_argument("prompt", nargs=argparse.REMAINDER, help="Question to send to local AI.")
    args = parser.parse_args(argv)

    root = root_from_args(args)
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        return emit(args, {"error": "missing prompt"}, 2)

    tail_path = Path(args.context_file).expanduser() if args.context_file else terminal_tail_path(root)
    tail_text = redact(read_text(tail_path))
    history_text = redact(read_text(Path(os.environ.get("HISTFILE", "")), "")) if os.environ.get("HISTFILE") else ""
    if not history_text and os.environ.get("HISTCMD"):
        history_text = redact(os.environ["HISTCMD"])
    telemetry = collect_telemetry() if prompt_requests_telemetry(prompt) else None
    prefetch_text = telemetry_context(telemetry) if telemetry else ""

    write_tail_file(
        tail_path,
        "\n".join(
            [
                "# Aegix Terminal Tail",
                "",
                f"- captured_at: {iso_now()}",
                f"- prompt: {prompt}",
                f"- cwd: {os.getcwd()}",
                "",
                "```text",
                tail_text.strip() or history_text.strip() or prompt,
                "```",
                "",
            ]
        ),
    )

    response, tool_trace, backend_payload = run_tool_loop(
        root=root,
        prompt=prompt,
        tail_path=tail_path,
        tail_text=tail_text,
        history_text=history_text,
        prefetch_text=prefetch_text,
        model=args.model,
        ollama_url=args.ollama_url,
        timeout=args.timeout,
        num_predict=args.num_predict,
    )
    error = backend_payload.get("error") if isinstance(backend_payload, dict) else None
    if not response and not error:
        error = "model returned no final answer"
    fallback_mode = None
    if not response and telemetry is not None:
        response = format_telemetry_answer(telemetry)
        tool_trace.insert(
            0,
            {
                "call": {"name": "procfs.telemetry", "arguments": {}},
                "observation": telemetry,
                "prefetched": True,
            },
        )
        fallback_mode = "telemetry"
    if not response and error:
        response = error

    vault = obsidian_vault(root)
    vault.mkdir(parents=True, exist_ok=True)
    note_path = write_chat_note(vault, prompt, tail_text, response, args.model, root, tool_trace=tool_trace)

    index_result = None
    agentctl_cmd = find_agentctl()
    if agentctl_cmd is not None:
        index_result = run_json([*agentctl_cmd, "--root", str(root), "index", "--scope", str(root / "notes"), "--json"])

    final_payload = {
        "command": "query",
        "prompt": prompt,
        "response": response,
        "tail_path": str(tail_path),
        "note_path": str(note_path),
        "model": args.model,
        "mode": "fallback-telemetry" if fallback_mode else "tool-calling",
        "tool_trace": tool_trace,
        "backend": backend_payload,
        "index_result": index_result,
    }
    exit_code = 0 if response else 1
    if error:
        final_payload["error"] = error
    if fallback_mode:
        final_payload["fallback"] = fallback_mode
    return emit(args, final_payload, exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
