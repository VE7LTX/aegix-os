#!/usr/bin/env python3
"""Integration test for the Aegix `?` terminal-to-AI shortcut."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
QUERY = REPO / "tools" / "aegixquery" / "aegixquery.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aegix-query-test-") as temp:
        root = Path(temp)
        tail_file = root / "logs" / "terminal-tail.md"
        tail_file.parent.mkdir(parents=True, exist_ok=True)
        tail_file.write_text(
            "# Aegix Terminal Tail\n\n```text\npwd\nagentctl status --json\n```\n",
            encoding="utf-8",
        )

        fake_ai = root / "fake_aegixai.py"
        fake_ai.write_text(
            """#!/usr/bin/env python3
import json
import sys

prompt = " ".join(sys.argv[sys.argv.index('ask') + 1:-1])
print(json.dumps({
    "command": "ask",
    "response": "memory load is moderate",
    "prompt_seen": prompt,
    "model": "stub-model",
}))
""",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["AEGIX_ROOT"] = str(root)
        env["AEGIX_OBSIDIAN_VAULT"] = str(root / "notes" / "obsidian")
        env["AEGIX_QUERY_CONTEXT_FILE"] = str(tail_file)
        env["AEGIX_QUERY_AEGIXAI"] = f'"{sys.executable}" "{fake_ai}"'

        result = subprocess.run(
            [sys.executable, str(QUERY), "--root", str(root), "--json", "what", "is", "the", "memory", "load", "right", "now"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise AssertionError(f"query failed: rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")

        payload = json.loads(result.stdout)
        assert payload["executed"] is False
        assert payload["response"] == "memory load is moderate"
        assert Path(payload["tail_path"]).exists()
        note_path = Path(payload["note_path"])
        assert note_path.exists()

        indexed = subprocess.run(
            [sys.executable, str(REPO / "tools" / "agentctl" / "agentctl.py"), "--root", str(root), "search-index", "memory load", "--json"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        assert indexed.returncode == 0, indexed.stderr
        search_payload = json.loads(indexed.stdout)
        assert any(note_path.name in match.get("path", "") for match in search_payload.get("matches", [])), search_payload

        graph = subprocess.run(
            [sys.executable, str(REPO / "tools" / "agentctl" / "agentctl.py"), "--root", str(root), "graph", "--json"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        assert graph.returncode == 0, graph.stderr
        graph_payload = json.loads(graph.stdout)
        assert graph_payload["summary"]["files_indexed"] >= 1
        assert Path(graph_payload["vector_registry_path"]).exists()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
