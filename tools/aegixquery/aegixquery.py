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
DEFAULT_AEGIXAI = os.environ.get("AEGIX_QUERY_AEGIXAI")
DEFAULT_AGENTCTL = os.environ.get("AEGIX_QUERY_AGENTCTL")
DEFAULT_TELEMETRY_JSON = os.environ.get("AEGIX_QUERY_TELEMETRY_JSON")


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


def telemetry_question(prompt: str) -> bool:
    lowered = prompt.lower()
    return bool(
        re.search(r"\b(ram|memory usage|memory load|used memory|available memory|free memory)\b", lowered)
        or re.search(r"\b(load average|load avg|cpu usage|disk usage|disk free|uptime)\b", lowered)
    )


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


def collect_telemetry() -> dict[str, Any]:
    if DEFAULT_TELEMETRY_JSON:
        try:
            return json.loads(DEFAULT_TELEMETRY_JSON)
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


def format_telemetry(prompt: str, telemetry: dict[str, Any]) -> str:
    total = telemetry.get("ram_total_bytes")
    available = telemetry.get("ram_available_bytes")
    used = telemetry.get("ram_used_bytes")
    loadavg = telemetry.get("loadavg") or []
    parts = [
        f"RAM usage right now: {human_bytes(used)} used / {human_bytes(total)} total",
        f"Available: {human_bytes(available)}",
    ]
    if total and used is not None:
        parts.append(f"Utilization: {used / total:.1%}")
    if loadavg:
        parts.append("Load average: " + ", ".join(f"{value:.2f}" for value in loadavg))
    uptime = telemetry.get("uptime_seconds")
    if uptime is not None:
        parts.append(f"Uptime: {int(uptime // 3600)}h {int((uptime % 3600) // 60)}m")
    return "\n".join(parts)


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return default


def find_aegixai() -> list[str] | None:
    env_command = split_command(DEFAULT_AEGIXAI)
    if env_command:
        return env_command
    executable = shutil.which("aegixai")
    if executable:
        return [executable]
    local_script = Path(__file__).resolve().parents[1] / "aegixai" / "aegixai.py"
    if local_script.exists():
        return [sys.executable, str(local_script)]
    return None


def find_agentctl() -> list[str] | None:
    env_command = split_command(DEFAULT_AGENTCTL)
    if env_command:
        return env_command
    executable = shutil.which("agentctl")
    if executable:
        return [executable]
    local_script = Path(__file__).resolve().parents[1] / "agentctl" / "agentctl.py"
    if local_script.exists():
        return [sys.executable, str(local_script)]
    return None


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


def write_tail_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_chat_note(vault: Path, prompt: str, tail_text: str, response: str, model: str, root: Path) -> Path:
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
        "",
        "# Response",
        "",
        response.strip() or "_No response text._",
        "",
    ]
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

    context = build_context(root, prompt, tail_text, history_text)
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

    telemetry = None
    if telemetry_question(prompt):
        telemetry = collect_telemetry()
        response = format_telemetry(prompt, telemetry)
        vault = obsidian_vault(root)
        vault.mkdir(parents=True, exist_ok=True)
        note_path = write_chat_note(vault, prompt, tail_text, response, args.model, root)
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
            "executed": False,
            "mode": "direct-telemetry",
            "telemetry": telemetry,
            "index_result": index_result,
        }
        return emit(args, final_payload, 0)

    aegixai_cmd = find_aegixai()
    if aegixai_cmd is None:
        return emit(args, {"error": "aegixai command not found"}, 1)

    request = [
        *aegixai_cmd,
        "--root",
        str(root),
        "--model",
        args.model,
        "--ollama-url",
        args.ollama_url,
        "--timeout",
        str(args.timeout),
        "--num-predict",
        str(args.num_predict),
        "ask",
        context + "\nAnswer the user's prompt using the terminal context above.\n",
        "--json",
    ]
    result = subprocess.run(request, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {
            "command": "ask",
            "response": result.stdout.strip(),
            "error": result.stderr.strip() or f"exit_code={result.returncode}",
        }

    response = payload.get("response", "")
    vault = obsidian_vault(root)
    vault.mkdir(parents=True, exist_ok=True)
    note_path = write_chat_note(vault, prompt, tail_text, response, args.model, root)

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
        "executed": False,
        "mode": "local-ai",
        "aegixai": payload,
        "index_result": index_result,
    }
    exit_code = 0 if response else 1
    if result.returncode != 0 and not response:
        final_payload["error"] = payload.get("error") or result.stderr.strip() or f"exit_code={result.returncode}"
    return emit(args, final_payload, exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
