#!/usr/bin/env python3
"""Aegix secret handle CLI scaffold.

This preview command intentionally reports handles and status only. It must not
print raw secret values.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ROOT = Path(os.environ.get("AEGIX_SECRETS_ROOT", "/aegix/secrets"))
DEFAULT_HANDLES = [
    {
        "handle": "codex.operator.auth",
        "purpose": "Codex CLI operator authentication state",
        "raw_value_access": False,
        "status": "managed-by-tool-cache",
    },
    {
        "handle": "openclaw.operator.auth",
        "purpose": "OpenClaw operator authentication placeholder",
        "raw_value_access": False,
        "status": "planned",
    },
    {
        "handle": "hubspot.crm.proxy",
        "purpose": "Scoped CRM API proxy placeholder",
        "raw_value_access": False,
        "status": "planned",
    },
]

COMMAND_GUIDES = {
    "status": {
        "intent": "Report secret-store status without exposing secret values.",
        "when_to_use": "Run before any secret-related task to confirm the metadata root and policy posture.",
        "example": "secretsctl status --json",
        "safety_notes": ["This command must never print raw secret values."],
        "next_steps": ["secretsctl handles --json", "agentctl caps --json"],
    },
    "handles": {
        "intent": "List secret handles, purposes, and statuses without values.",
        "when_to_use": "Use when an agent needs to know which credential-like capabilities may exist.",
        "example": "secretsctl handles --json",
        "safety_notes": [
            "A handle is not a secret value.",
            "Use brokered access in future milestones rather than copying credentials into prompts or files.",
        ],
        "next_steps": ["secretsctl policy --json", "agentctl approve <session_id> --cap secret.read:<handle> --json"],
    },
    "policy": {
        "intent": "Show the Aegix secret handling rules.",
        "when_to_use": "Use before attempting CRM, Codex, OpenClaw, router, or API work that might touch credentials.",
        "example": "secretsctl policy --json",
        "safety_notes": ["External writes and authority changes need explicit approval metadata."],
        "next_steps": ["agentctl caps --json", "agentctl events --json"],
    },
}


def emit(args: argparse.Namespace, payload: dict[str, object]) -> int:
    command = getattr(args, "command", None)
    if command:
        payload.setdefault("agent_help", COMMAND_GUIDES.get(command, {}))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            if isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")
    return 0


def root_path(args: argparse.Namespace) -> Path:
    return Path(args.root).expanduser()


def cmd_status(args: argparse.Namespace) -> int:
    root = root_path(args)
    payload = {
        "command": "status",
        "project": "aegix-os",
        "status": "scaffold",
        "root": str(root),
        "root_exists": root.exists(),
        "policy": "handle-only; raw secret values must not be printed",
        "backend": "planned: secretsd with age/sops/pass-compatible storage",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return emit(args, payload)


def cmd_handles(args: argparse.Namespace) -> int:
    root = root_path(args)
    manifest = root / "handles.json"
    handles: list[dict[str, object]] = DEFAULT_HANDLES
    if manifest.exists():
        try:
            loaded = json.loads(manifest.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                handles = loaded
        except json.JSONDecodeError:
            handles = DEFAULT_HANDLES + [
                {
                    "handle": "manifest.error",
                    "purpose": f"Could not parse {manifest}",
                    "raw_value_access": False,
                    "status": "error",
                }
            ]

    return emit(
        args,
        {
            "command": "handles",
            "root": str(root),
            "handles": handles,
            "raw_values_returned": False,
        },
    )


def cmd_policy(args: argparse.Namespace) -> int:
    return emit(
        args,
        {
            "command": "policy",
            "rules": [
                "agents receive secret handles, not raw long-lived values",
                "secret use must be tied to agent, session, capability, and destination",
                "external writes and authority changes require explicit approval",
                "preview commands must never print raw secret values",
            ],
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secretsctl",
        description="Aegix secret handle and broker scaffold.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Agent prompt:
  Secrets are handles, not raw prompt text. Start with status and handles.
  Do not print, store, summarize, or guess raw secret values.

Common flow:
  secretsctl status --json
  secretsctl handles --json
  secretsctl policy --json
  agentctl approve <session_id> --cap secret.read:<handle> --json
""",
    )
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help="Secret metadata root. Defaults to AEGIX_SECRETS_ROOT or /aegix/secrets.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    for name, help_text, func in [
        ("status", "Show secret broker/store status without values.", cmd_status),
        ("handles", "List known secret handles without values.", cmd_handles),
        ("policy", "Show the Aegix secret handling rules.", cmd_policy),
    ]:
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        command.add_argument("--root", default=argparse.SUPPRESS)
        command.set_defaults(func=func)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
