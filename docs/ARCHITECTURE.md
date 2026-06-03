# Architecture

Aegix OS is a pre-MVP scaffold for an AI-first Linux workstation/server profile where agents can inspect, navigate, operate, document, and hand off through built-in system interfaces.

## Planes

The architecture is split into eight planes:

| Plane | Responsibility |
|---|---|
| Host | Declarative NixOS substrate, rollback, filesystem snapshots, systemd supervision |
| Identity | Per-agent Unix identity, workspace, memory path, trust tier, budget profile |
| Runtime | Tiered execution from read-only process sandbox to disposable VM |
| Capability broker | Local authorization point for files, shell, network, secrets, tools, and escalation |
| Memory | Obsidian-backed AI memory, file-backed facts, decisions, receipts, project notes, indexes, and session state |
| Integration | Plugin registry, MCP servers, local API servers, and appliance controls |
| Action | Transactional task loop with verification, receipt, commit, rollback, or escalation |
| Human control | CLI, dashboard, approval tokens, receipt review, policy ownership |

The primary kit is defined in [PRIMARY_KIT.md](PRIMARY_KIT.md). This architecture keeps that kit usable by agents without giving them ambient authority over the host.

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
