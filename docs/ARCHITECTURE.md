# Architecture

Aegix OS is a pre-MVP scaffold for a Linux agent appliance where agents are operating-system principals and authority is granted through explicit capabilities.

## Planes

The architecture is split into seven planes:

| Plane | Responsibility |
|---|---|
| Host | Declarative NixOS substrate, rollback, filesystem snapshots, systemd supervision |
| Identity | Per-agent Unix identity, workspace, memory path, trust tier, budget profile |
| Runtime | Tiered execution from read-only process sandbox to disposable VM |
| Capability broker | Local authorization point for files, shell, network, secrets, tools, and escalation |
| Memory | File-backed facts, decisions, receipts, project notes, indexes, and session state |
| Action | Transactional task loop with verification, receipt, commit, rollback, or escalation |
| Human control | CLI, dashboard, approval tokens, receipt review, policy ownership |

## Operating Loop

```text
receive task -> classify risk -> create session -> request capabilities -> execute bounded action -> verify -> write receipt -> commit/rollback/escalate
```

No verification means no completion.

## Runtime Tiers

| Tier | Runtime | Intended use |
|---|---|---|
| T0 | Read-only process sandbox | Search, summarize, inspect |
| T1 | bubblewrap/Landlock sandbox | Local file-limited commands |
| T2 | Rootless Podman | Normal agent workloads and project tools |
| T3 | microVM | Untrusted repositories and risky web automation |
| T4 | Disposable VM | Hostile documents, malware-like analysis, unknown scripts |

The agent does not choose the tier. The broker or session runner selects it from policy.

## Repository Targets

Phase 1 should produce a reproducible NixOS VM appliance with:

- `agentctl` CLI
- `agentd` session runner
- `capd` capability broker
- rootless Podman runtime profile
- per-agent workspace and memory directories
- JSONL and Markdown receipts
- read-only `observer-agent`
