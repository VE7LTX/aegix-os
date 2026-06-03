#!/usr/bin/env python3
"""Obsidian vault CLI scaffold for Aegix AI memory."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_VAULT = Path(os.environ.get("AEGIX_OBSIDIAN_VAULT", "/aegix/notes/obsidian"))
DEFAULT_FOLDERS = [
    "00-inbox",
    "10-runbooks",
    "20-projects",
    "30-decisions",
    "40-agent-handoffs",
    "50-receipts",
    "60-system-map",
    "70-shortcuts",
    "80-troubleshooting",
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "note"


def vault_path(args: argparse.Namespace) -> Path:
    return Path(args.vault).expanduser()


def emit(args: argparse.Namespace, payload: dict[str, object]) -> int:
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


def cmd_path(args: argparse.Namespace) -> int:
    vault = vault_path(args)
    return emit(args, {"vault": str(vault), "exists": vault.exists()})


def cmd_init(args: argparse.Namespace) -> int:
    vault = vault_path(args)
    created = []
    for folder in DEFAULT_FOLDERS:
        path = vault / folder
        path.mkdir(parents=True, exist_ok=True)
        created.append(str(path))
    return emit(args, {"vault": str(vault), "folders": created})


def cmd_new(args: argparse.Namespace) -> int:
    vault = vault_path(args)
    folder = vault / args.folder
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    path = folder / f"{timestamp}-{slugify(args.title)}.md"
    content = [
        f"# {args.title}",
        "",
        f"created: {datetime.now(timezone.utc).isoformat()}",
        "source: obsidianctl",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return emit(args, {"created": str(path)})


def cmd_search(args: argparse.Namespace) -> int:
    vault = vault_path(args)
    if not vault.exists():
        return emit(args, {"error": "vault does not exist", "vault": str(vault)})
    result = subprocess.run(
        ["rg", "--line-number", "--fixed-strings", args.query, str(vault)],
        check=False,
        capture_output=True,
        text=True,
    )
    matches = [line for line in result.stdout.splitlines() if line.strip()]
    return emit(args, {"query": args.query, "matches": matches})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsidianctl",
        description="Aegix Obsidian AI memory CLI scaffold.",
    )
    parser.add_argument(
        "--vault",
        default=str(DEFAULT_VAULT),
        help="Obsidian vault path. Defaults to AEGIX_OBSIDIAN_VAULT or /aegix/notes/obsidian.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    def add_common_options(command: argparse.ArgumentParser) -> argparse.ArgumentParser:
        command.add_argument(
            "--vault",
            default=argparse.SUPPRESS,
            help="Obsidian vault path. May also be passed before the subcommand.",
        )
        command.add_argument(
            "--json",
            action="store_true",
            default=argparse.SUPPRESS,
            help="Emit JSON output. May also be passed before the subcommand.",
        )
        return command

    add_common_options(
        subcommands.add_parser("path", help="Show the configured vault path.")
    ).set_defaults(func=cmd_path)
    add_common_options(
        subcommands.add_parser("init", help="Create the standard Aegix vault folders.")
    ).set_defaults(func=cmd_init)

    new_note = subcommands.add_parser("new", help="Create a timestamped Markdown note.")
    add_common_options(new_note)
    new_note.add_argument("title", help="Note title.")
    new_note.add_argument("--folder", default="00-inbox", help="Vault-relative folder.")
    new_note.set_defaults(func=cmd_new)

    search = subcommands.add_parser("search", help="Search the vault with ripgrep.")
    add_common_options(search)
    search.add_argument("query", help="Fixed-string search query.")
    search.set_defaults(func=cmd_search)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
