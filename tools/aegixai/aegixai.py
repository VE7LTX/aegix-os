#!/usr/bin/env python3
"""Aegix local Ollama terminal copilot."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(os.environ.get("AEGIX_ROOT", "/aegix"))
DEFAULT_MODEL = os.environ.get("AEGIX_AI_MODEL", "qwen2.5:0.5b")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_TIMEOUT = int(os.environ.get("AEGIX_AI_TIMEOUT", "600"))
DEFAULT_NUM_PREDICT = int(os.environ.get("AEGIX_AI_NUM_PREDICT", "192"))

SYSTEM_PROMPT = """\
You are Aegix Native, the small local operator copilot inside Aegix OS.

Rules:
- Be concise and terminal-friendly.
- Keep normal answers under 8 short lines.
- Prefer documented Aegix commands over ad hoc shell use.
- Do not claim an action was done unless a command or receipt proves it.
- For dangerous actions, prepare a plan and ask for approval metadata.
- Use /aegix/scratch for experiments and /aegix/projects for project work.
- Tell the operator when Ollama/model capability is degraded.
"""

COMMAND_ASSIST_PROMPT = """\
Return shell commands only as suggestions. Do not pretend to execute them.
Prefer Aegix commands such as agentctl doctor, agentctl paths, agentctl caps,
agentctl index, agentctl receipts, agentctl snapshot, and agentctl rollback.
Include a short safety note when the request touches services, secrets,
packages, auth, network, or external writes.
"""


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def emit(args: argparse.Namespace, payload: dict[str, Any], exit_code: int = 0) -> int:
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, sort_keys=True)}")
            else:
                print(f"{key}: {value}")
    return exit_code


def root_from_args(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "root", DEFAULT_ROOT)).expanduser()


def ollama_url(args: argparse.Namespace, path: str) -> str:
    base = getattr(args, "ollama_url", DEFAULT_OLLAMA_URL).rstrip("/")
    return f"{base}{path}"


def ollama_json(args: argparse.Namespace, path: str, payload: dict[str, Any] | None = None, timeout: int = 120) -> dict[str, Any]:
    data = None
    method = "GET"
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(ollama_url(args, path), data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class Spinner:
    def __init__(self, args: argparse.Namespace, message: str) -> None:
        self.enabled = (
            not getattr(args, "json", False)
            and not getattr(args, "no_spinner", False)
            and sys.stderr.isatty()
        )
        self.message = message
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "Spinner":
        if self.enabled:
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
        elif not getattr(self, "json", False):
            print(self.message, file=sys.stderr)
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)
            print("\r" + " " * min(100, len(self.message) + 8) + "\r", end="", file=sys.stderr)

    def _run(self) -> None:
        frames = "|/-\\"
        idx = 0
        while not self.stop.is_set():
            print(f"\r{frames[idx % len(frames)]} {self.message}", end="", file=sys.stderr, flush=True)
            idx += 1
            time.sleep(0.2)


def read_tail(path: Path, lines: int = 80) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "tail": []}
    try:
        return {
            "path": str(path),
            "exists": True,
            "tail": path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:],
        }
    except OSError as exc:
        return {"path": str(path), "exists": True, "error": f"{exc.__class__.__name__}: {exc}", "tail": []}


def run_log_command(command: list[str], timeout: int = 20) -> dict[str, Any]:
    if shutil.which(command[0]) is None:
        return {"available": False, "command": command, "output": ""}
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
        return {
            "available": True,
            "command": command,
            "exit_code": result.returncode,
            "output": (result.stdout + result.stderr).strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "command": command, "error": f"{exc.__class__.__name__}: {exc}", "output": ""}


def helper_prompt(command: str) -> dict[str, Any]:
    return {
        "intent": f"aegixai {command} talks to local Ollama through localhost only.",
        "default_model": DEFAULT_MODEL,
        "timeout_seconds": DEFAULT_TIMEOUT,
        "safety_notes": [
            "This copilot suggests commands; it does not execute commands on your behalf.",
            "Use agentctl receipts and snapshots for work that changes files or state.",
            "Dangerous actions require approval metadata before execution in future milestones.",
        ],
        "next_steps": [
            "agentctl doctor --json",
            "agentctl caps --json",
            "agentctl index --json",
            "agentctl receipts --json",
        ],
    }


def cmd_status(args: argparse.Namespace) -> int:
    try:
        tags = ollama_json(args, "/api/tags", timeout=10)
        models = [model.get("name") for model in tags.get("models", [])]
        available = True
        error = None
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        models = []
        available = False
        error = f"{exc.__class__.__name__}: {exc}"
    payload = {
        "command": "status",
        "ollama_available": available,
        "ollama_url": getattr(args, "ollama_url", DEFAULT_OLLAMA_URL),
        "default_model": args.model,
        "models": models,
        "model_present": args.model in models,
        "error": error,
        "agent_help": helper_prompt("status"),
    }
    return emit(args, payload, 0 if available else 1)


def cmd_models(args: argparse.Namespace) -> int:
    try:
        tags = ollama_json(args, "/api/tags", timeout=10)
        payload = {
            "command": "models",
            "models": tags.get("models", []),
            "default_model": args.model,
            "agent_help": helper_prompt("models"),
        }
        return emit(args, payload)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return emit(
            args,
            {
                "command": "models",
                "models": [],
                "error": f"{exc.__class__.__name__}: {exc}",
                "agent_help": helper_prompt("models"),
            },
            1,
        )


def cmd_diagnose(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    try:
        tags = ollama_json(args, "/api/tags", timeout=15)
        models = [model.get("name") for model in tags.get("models", [])]
        ollama_available = True
        ollama_error = None
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        models = []
        ollama_available = False
        ollama_error = f"{exc.__class__.__name__}: {exc}"

    payload = {
        "command": "diagnose",
        "ollama_available": ollama_available,
        "ollama_error": ollama_error,
        "default_model": args.model,
        "model_present": args.model in models,
        "models": models,
        "timeout_seconds": args.timeout,
        "likely_issue": "cold model load or slow software-emulated inference" if ollama_available and args.model in models else "ollama unavailable or model missing",
        "logs": {
            "model_pull": read_tail(root / "logs" / "ollama-model-pull.log"),
            "ollama_service": run_log_command(["systemctl", "status", "ollama", "--no-pager", "--plain"]),
            "ollama_journal": run_log_command(["journalctl", "-u", "ollama", "-n", "80", "--no-pager", "--plain"]),
            "pull_service_journal": run_log_command(["journalctl", "-u", "aegix-ollama-model-pull", "-n", "80", "--no-pager", "--plain"]),
        },
        "agent_help": helper_prompt("diagnose"),
    }
    return emit(args, payload, 0 if ollama_available else 1)


def ask_model(args: argparse.Namespace, prompt: str, system: str) -> dict[str, Any]:
    response = ollama_json(
        args,
        "/api/chat",
        {
            "model": args.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "options": {
                "num_predict": args.num_predict,
                "temperature": 0.2,
            },
        },
        timeout=args.timeout,
    )
    message = response.get("message", {})
    return {
        "model": args.model,
        "response": message.get("content", ""),
        "raw": response,
    }


def cmd_warmup(args: argparse.Namespace) -> int:
    try:
        with Spinner(args, f"warming {args.model}; first load can be slow on this VM"):
            result = ask_model(args, "Reply with exactly: ready", SYSTEM_PROMPT)
        payload = {"command": "warmup", "status": "completed", **result, "agent_help": helper_prompt("warmup")}
        if args.json:
            return emit(args, payload)
        print("ready")
        return 0
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return emit(
            args,
            {
                "command": "warmup",
                "status": "degraded",
                "error": f"{exc.__class__.__name__}: {exc}",
                "hint": "Run aegixai diagnose --json and consider retrying with --timeout 900.",
                "agent_help": helper_prompt("warmup"),
            },
            1,
        )


def cmd_ask(args: argparse.Namespace) -> int:
    try:
        with Spinner(args, f"waiting for {args.model}; first response may take several minutes under QEMU TCG"):
            result = ask_model(args, args.prompt, SYSTEM_PROMPT)
        payload = {"command": "ask", **result, "agent_help": helper_prompt("ask")}
        if args.json:
            return emit(args, payload)
        print(result["response"])
        return 0
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return emit(
            args,
            {
                "command": "ask",
                "error": f"{exc.__class__.__name__}: {exc}",
                "hint": "Run aegixai diagnose --json. If the model is present, retry with aegixai warmup --timeout 900.",
                "agent_help": helper_prompt("ask"),
            },
            1,
        )


def cmd_command(args: argparse.Namespace) -> int:
    prompt = f"Operator request: {args.prompt}\nReturn suggested terminal commands and explain approval needs."
    try:
        with Spinner(args, f"waiting for {args.model}; generating command suggestions"):
            result = ask_model(args, prompt, SYSTEM_PROMPT + "\n" + COMMAND_ASSIST_PROMPT)
        payload = {
            "command": "command",
            "request": args.prompt,
            "suggestion": result["response"],
            "executed": False,
            "agent_help": helper_prompt("command"),
        }
        if args.json:
            return emit(args, payload)
        print(result["response"])
        print("\nNot executed. Review first; use receipts/snapshots for state-changing work.")
        return 0
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return emit(
            args,
            {
                "command": "command",
                "error": f"{exc.__class__.__name__}: {exc}",
                "executed": False,
                "hint": "Run aegixai diagnose --json. If Ollama is healthy, retry with --timeout 900.",
                "agent_help": helper_prompt("command"),
            },
            1,
        )


def cmd_grow(args: argparse.Namespace) -> int:
    root = root_from_args(args)
    growth_dir = root / "models" / "growth"
    growth_dir.mkdir(parents=True, exist_ok=True)
    path = growth_dir / f"{iso_now().replace(':', '-')}-growth-proposal.md"
    content = [
        "# Aegix Native Growth Proposal",
        "",
        f"created_at: {iso_now()}",
        f"current_model: {args.model}",
        "status: proposal-only",
        "",
        "## Purpose",
        "",
        "Track how the local copilot should improve without granting it ambient authority.",
        "",
        "## Proposed Growth Loop",
        "",
        "1. Read receipts and event logs.",
        "2. Identify repeated operator tasks.",
        "3. Propose command helpers, runbooks, or model changes.",
        "4. Require operator approval for package, service, model, secret, or external changes.",
        "5. Write receipts for accepted changes.",
        "",
        "## Safe Upgrade Rule",
        "",
        "The local model may recommend upgrades. It may not silently upgrade itself.",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return emit(
        args,
        {
            "command": "grow",
            "status": "proposal-written",
            "path": str(path),
            "executed_upgrade": False,
            "agent_help": helper_prompt("grow"),
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegixai",
        description="Aegix native local Ollama copilot for terminal chat and command suggestions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Common flow:
  aegixai status --json
  aegixai diagnose --json
  aegixai warmup
  aegixai ask "What should I inspect first?"
  aegixai command "show me failed services"
  aegixai grow --json

This tool suggests and explains. It does not execute shell commands.
""",
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Aegix root path.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name.")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama HTTP URL.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Ollama request timeout seconds.")
    parser.add_argument("--num-predict", type=int, default=DEFAULT_NUM_PREDICT, help="Maximum response tokens.")
    parser.add_argument("--no-spinner", action="store_true", help="Disable non-JSON wait indicator.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    def add_common(command: argparse.ArgumentParser) -> None:
        command.add_argument("--root", default=argparse.SUPPRESS, help="Aegix root path.")
        command.add_argument("--model", default=argparse.SUPPRESS, help="Ollama model name.")
        command.add_argument("--ollama-url", default=argparse.SUPPRESS, help="Ollama HTTP URL.")
        command.add_argument("--timeout", type=int, default=argparse.SUPPRESS, help="Ollama request timeout seconds.")
        command.add_argument("--num-predict", type=int, default=argparse.SUPPRESS, help="Maximum response tokens.")
        command.add_argument("--no-spinner", action="store_true", default=argparse.SUPPRESS, help="Disable non-JSON wait indicator.")
        command.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit JSON output.")

    for name, help_text, func in [
        ("status", "Show Ollama and default model status.", cmd_status),
        ("models", "List local Ollama models.", cmd_models),
        ("diagnose", "Show local AI service logs and likely failure mode.", cmd_diagnose),
        ("warmup", "Load the model with a tiny prompt before interactive use.", cmd_warmup),
        ("grow", "Write a bounded self-improvement proposal.", cmd_grow),
    ]:
        command = subcommands.add_parser(name, help=help_text)
        add_common(command)
        command.set_defaults(func=func)

    ask = subcommands.add_parser("ask", help="Ask the local Aegix model a question.")
    ask.add_argument("prompt", help="Question or instruction.")
    add_common(ask)
    ask.set_defaults(func=cmd_ask)

    command = subcommands.add_parser("command", help="Ask for terminal command suggestions without execution.")
    command.add_argument("prompt", help="Desired terminal task.")
    add_common(command)
    command.set_defaults(func=cmd_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
