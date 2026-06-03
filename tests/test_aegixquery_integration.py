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

        fake_ai = root / "fake_chat_backend.py"
        request_log = root / "chat-requests.jsonl"
        state_file = root / "chat-state.txt"
        fake_ai.write_text(
            """#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


state_file = Path(os.environ["FAKE_CHAT_STATE"])
request_log = Path(os.environ["FAKE_CHAT_LOG"])
count = int(state_file.read_text(encoding="utf-8")) if state_file.exists() else 0
request = json.load(sys.stdin)
request_log.parent.mkdir(parents=True, exist_ok=True)
with request_log.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(request, sort_keys=True) + "\\n")

if count == 0:
    content = {
        "tool_calls": [
            {"name": "procfs.telemetry", "arguments": {}}
        ],
        "final_answer": None,
    }
else:
    content = {
        "tool_calls": [],
        "final_answer": "RAM usage comes from procfs after the tool call.",
    }

state_file.write_text(str(count + 1), encoding="utf-8")
print(json.dumps({"message": {"role": "assistant", "content": json.dumps(content)}}))
""",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["AEGIX_ROOT"] = str(root)
        env["AEGIX_OBSIDIAN_VAULT"] = str(root / "notes" / "obsidian")
        env["AEGIX_QUERY_CONTEXT_FILE"] = str(tail_file)
        env["AEGIX_QUERY_CHAT_CMD"] = f'"{sys.executable}" "{fake_ai}"'
        env["FAKE_CHAT_STATE"] = str(state_file)
        env["FAKE_CHAT_LOG"] = str(request_log)
        env["AEGIX_QUERY_TELEMETRY_JSON"] = json.dumps(
            {
                "ram_used_bytes": 123456789,
                "ram_total_bytes": 987654321,
                "ram_available_bytes": 864197532,
                "loadavg": [0.12, 0.34, 0.56],
                "uptime_seconds": 3723,
                "source": "test-override",
            }
        )

        result = subprocess.run(
            [sys.executable, str(QUERY), "--root", str(root), "--json", "what", "is", "the", "ram", "usage", "right", "now"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise AssertionError(f"query failed: rc={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")

        payload = json.loads(result.stdout)
        assert payload["mode"] == "tool-calling"
        assert payload["response"] == "RAM usage comes from procfs after the tool call."
        assert Path(payload["tail_path"]).exists()
        note_path = Path(payload["note_path"])
        assert note_path.exists()
        assert payload["tool_trace"], payload
        first_call = payload["tool_trace"][0]
        assert first_call["call"]["name"] == "procfs.telemetry"
        assert first_call["observation"]["ram_total_bytes"] == 987654321
        assert first_call["observation"]["source"] == "test-override"

        requests = request_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(requests) == 2, requests
        first_request = json.loads(requests[0])
        second_request = json.loads(requests[1])
        assert first_request["messages"][0]["role"] == "system"
        assert "Available tools" in first_request["messages"][0]["content"]
        assert any("Tool observations" in message.get("content", "") for message in second_request["messages"]), second_request

        empty_backend = root / "empty_chat_backend.py"
        empty_backend.write_text(
            """#!/usr/bin/env python3
from __future__ import annotations

import json

print(json.dumps({"message": {"content": ""}}))
""",
            encoding="utf-8",
        )

        fallback_env = env.copy()
        fallback_env["AEGIX_QUERY_CHAT_CMD"] = f'"{sys.executable}" "{empty_backend}"'
        fallback = subprocess.run(
            [sys.executable, str(QUERY), "--root", str(root), "--json", "what", "is", "the", "ram", "usage", "right", "now"],
            check=False,
            capture_output=True,
            text=True,
            env=fallback_env,
        )
        assert fallback.returncode == 0, fallback.stderr
        fallback_payload = json.loads(fallback.stdout)
        assert fallback_payload["mode"] == "fallback-telemetry"
        assert fallback_payload["response"].startswith("RAM used:")
        assert fallback_payload["fallback"] == "telemetry"

        vm_specs = subprocess.run(
            [sys.executable, str(QUERY), "--root", str(root), "--json", "what", "are", "the", "vm", "specs", "this", "instance", "is", "running", "in"],
            check=False,
            capture_output=True,
            text=True,
            env=fallback_env,
        )
        assert vm_specs.returncode == 0, vm_specs.stderr
        vm_specs_payload = json.loads(vm_specs.stdout)
        assert vm_specs_payload["mode"] == "fallback-system-specs"
        assert "CPU" in vm_specs_payload["response"] or "Memory" in vm_specs_payload["response"]
        assert vm_specs_payload["fallback"] == "system-specs"

        switch_backend = root / "switching_chat_backend.py"
        switch_backend.write_text(
            """#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time


request = json.load(sys.stdin)
model = request.get("model", "")
if model.startswith("qwen"):
    time.sleep(3)
else:
    content = {
        "tool_calls": [],
        "final_answer": "tinyllama answered after qwen timed out.",
    }
    print(json.dumps({"message": {"role": "assistant", "content": json.dumps(content)}}))
""",
            encoding="utf-8",
        )

        tiny_env = env.copy()
        tiny_env["AEGIX_QUERY_CHAT_CMD"] = f'"{sys.executable}" "{switch_backend}"'
        tiny_env["AEGIX_QUERY_TELEMETRY_JSON"] = ""
        tiny_env["AEGIX_QUERY_CONTEXT_FILE"] = str(tail_file)
        tiny = subprocess.run(
            [sys.executable, str(QUERY), "--root", str(root), "--timeout", "1", "--json", "what", "should", "I", "inspect", "first"],
            check=False,
            capture_output=True,
            text=True,
            env=tiny_env,
        )
        assert tiny.returncode == 0, tiny.stderr
        tiny_payload = json.loads(tiny.stdout)
        assert tiny_payload["mode"] == "tool-calling"
        assert tiny_payload["model"] == "tinyllama"
        assert tiny_payload["requested_model"] == "qwen3.5:0.8b"
        assert tiny_payload["backend"]["fallback_used"] is True
        assert tiny_payload["backend"]["attempts"][0]["model"] == "qwen3.5:0.8b"
        assert tiny_payload["backend"]["attempts"][1]["model"] == "tinyllama"
        assert tiny_payload["response"] == "tinyllama answered after qwen timed out."

        indexed = subprocess.run(
            [sys.executable, str(REPO / "tools" / "agentctl" / "agentctl.py"), "--root", str(root), "search-index", "ram usage", "--json"],
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
