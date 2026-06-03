#!/usr/bin/env python3
"""Stdlib integration checks for the Aegix Preview v0.2 control plane."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
AGENTCTL = REPO / "tools" / "agentctl" / "agentctl.py"


def run_agentctl(root: Path, *args: str, timeout: int = 120) -> dict:
    env = os.environ.copy()
    env["AEGIX_ROOT"] = str(root)
    result = subprocess.run(
        [sys.executable, str(AGENTCTL), "--root", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"agentctl {' '.join(args)} failed with {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"expected JSON from agentctl {' '.join(args)}: {exc}\n{result.stdout}") from exc


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aegix-test-") as temp:
        root = Path(temp)

        verify = run_agentctl(root, "verify", "--json", timeout=180)
        assert verify["status"] == "passed", json.dumps(verify["checks"], indent=2)
        assert verify["rollback_mode"] == "metadata_only"
        assert Path(verify["report_path"]).exists()
        assert verify["summary"]["failed"] == 0

        by_name = {check["name"]: check for check in verify["checks"]}
        for required in [
            "required_paths",
            "session_and_receipt",
            "approval_scaffold",
            "snapshot_metadata",
            "rollback_metadata_only",
            "session_receipt_links",
            "snapshot_session_links",
            "file_index",
            "file_index_search",
            "file_graph",
            "event_log",
            "aegixai_command_safety",
        ]:
            assert by_name[required]["status"] in {"passed", "warning"}, required

        session_id = verify["session_id"]
        inspected = run_agentctl(root, "inspect", session_id, "--json")
        assert inspected["found"] is True
        assert inspected["receipt"]["rollback"]["rollback_mode"] == "metadata_only"

        rollback = run_agentctl(root, "rollback", session_id, "--json")
        assert rollback["rollback_mode"] == "metadata_only"
        assert rollback["rollback_executed"] is False
        assert rollback["destructive_actions"] is False

        receipts = run_agentctl(root, "receipts", "--json")
        assert any(receipt.get("session_id") == session_id for receipt in receipts["receipts"])

        graph = run_agentctl(root, "graph", "--json")
        assert graph["graph_exists"] is True
        assert graph["summary"]["files_indexed"] >= 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
