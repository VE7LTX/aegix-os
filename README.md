# Aegix OS

**Aegix OS** is an AI-first Linux workstation/server profile with built-in agent navigation, documented system controls, OpenClaw integration, Obsidian memory, and safe automation defaults.

The goal is not to ship "Linux with AI tools installed." The goal is to make a local system that new AI agents can understand and operate without rediscovering the machine through brittle mouse, keyboard, screenshot, and one-off script hacks.

## Status

Pre-MVP public scaffold. This repository is intended to become a reproducible test appliance first, then a proper installable Linux profile.

The first working target is a **NixOS VM/appliance profile**. A Fedora bootc/Atomic path is planned because Fedora is common in real homelab and workstation environments.

## What this is for

Aegix OS should be a preconfigured operating environment for local AI work:

- common operator shortcuts are built in as named commands
- system access is exposed through documented tools, not hidden desktop hacks
- projects, notes, receipts, screenshots, logs, memory, and configs live in predictable places
- OpenClaw runs as a managed suite component with clear permissions
- Obsidian provides the standard local AI memory vault for runbooks, decisions, project memory, receipts, and handoffs
- plugin, MCP, and local API servers are treated as first-class AI access surfaces
- local model services start with Ollama as a localhost-first model API
- database services include SQLite, Postgres, vector storage, and time-series storage options
- network/router and appliance controls are exposed through documented commands with approval gates
- safety boundaries are visible when actions touch secrets, services, external writes, or host state

The practical rule is simple:

> A new agent should be able to inspect the system, find the right tool, understand the permission boundary, act through a named interface, verify the result, and leave a readable record.

## Primary kit

The primary kit is tracked in [docs/PRIMARY_KIT.md](docs/PRIMARY_KIT.md). It currently defines:

- AI operator interface
- CLI/TUI operator kit
- native system access layer
- shortcut and command layer
- workspace layout
- Obsidian vault structure
- OpenClaw managed suite
- plugin, MCP, and API server layer
- network/router appliance controls
- browser automation profiles
- developer tools
- local model tools
- database, vector storage, and time-series tools
- system dashboard target
- documentation rules
- safety, backup, and rollback defaults

## Design laws

1. Agents should use documented system interfaces before mouse and keyboard automation.
2. Built-in shortcuts should be named, discoverable, and documented.
3. Memory should be file-backed and easy to grep, diff, back up, and delete.
4. Every meaningful action should leave a receipt.
5. Dangerous actions should require narrow approval, not broad trust.
6. Host state should be declarative where possible.
7. Verification and rollback should be part of the workflow.
8. External side effects should not be silent.
9. The human owns policy, shortcuts, secrets, and final approval.
10. OpenClaw gets useful local tools; Aegix owns the system boundary.

## MVP scope

The MVP is not a polished desktop distro. It is a reproducible agent workstation/server appliance that can be safely tested on a spare machine or VM.

### Phase 0: Repository skeleton

- Public project README
- Primary kit definition
- CLI/TUI kit definition
- Architecture notes
- NixOS module skeleton
- OpenClaw native integration plan
- Capability policy examples
- Receipt schema
- CLI command design
- Security model

### Phase 1: Local appliance

- NixOS flake for a VM profile
- `agentctl` CLI skeleton
- `agentd` session runner skeleton
- `capd` capability broker skeleton
- Rootless Podman runtime
- Standard workspace layout
- Obsidian vault profile
- OpenClaw managed profile
- MCP/API server profile
- plugin/tool registry
- Ollama service profile
- database/vector/time-series profile
- File-backed memory directories
- JSONL and Markdown receipts
- Read-only observer agent

### Phase 2: AI-first workstation/server kit

- Built-in shortcut command registry
- Plugin, MCP, and local API server registry
- Documented system access tools for files, windows, apps, logs, services, packages, browser, clipboard, screenshots, and audio
- Documented appliance controls for network, router, DNS, DHCP, firewall, NAS, and homelab systems
- Browser automation profiles
- VS Code and developer tool profile
- Local model profile
- Data service profile
- Dashboard/TUI for agents, commands, receipts, approvals, and system health

### Phase 3: Hardened runtime

- Per-agent network policy
- Secret broker
- Approval tokens
- Browser automation sandbox
- Snapshot/rollback integration
- MicroVM tier for untrusted workloads

## Recommended base

### Primary base: NixOS

NixOS is the cleanest first base because the system model is declarative and rollback-oriented. That matches the desired host-state model.

### Secondary base: Fedora bootc / Atomic

Fedora bootc is a strong later path for building bootable OCI-derived systems. This matters because many practical machines, including homelab nodes and laptops, are already Fedora-oriented.

## OpenClaw position

OpenClaw should be a first-class managed suite inside Aegix OS, not the root architecture.

Aegix should provide:

- OpenClaw install profile
- OpenClaw workspace layout
- OpenClaw skill policy wrapper
- OpenClaw secret mediation
- OpenClaw network policy
- OpenClaw receipt generator
- OpenClaw update/snapshot controls
- OpenClaw handoff docs for new agents

OpenClaw gets the benefit of local tools. Aegix owns the boundary.

## Target file layout

```text
/aegix
  agents/
    observer-agent/
    code-agent/
    openclaw-agent/
  commands/
  projects/
  sessions/
  checkpoints/
  memory/
  models/
    ollama/
  data/
    sqlite/
    postgres/
    vector/
    timeseries/
  notes/
    obsidian/
  mcp/
  api/
  plugins/
  receipts/
  approvals/
  policy/
  secrets/
  appliances/
  snapshots/
  logs/
  screenshots/
  runbooks/
```

## Agent loop

```text
inspect -> find tool -> request capability -> act -> verify -> receipt -> commit/rollback/escalate
```

No verification means no completion.

## Risk model

| Level | Name | Examples | Default behavior |
|---|---|---|---|
| L0 | Observe | Read scoped files, summarize logs | Allowed if scoped |
| L1 | Draft | Create scratch files, propose diffs | Allowed in workspace |
| L2 | Local modify | Patch project files, run tests | Allowed by project policy |
| L3 | System modify | Packages, services, firewall, NGINX | Approval required |
| L4 | External write | Email, CRM, Git push, web posts | Approval required |
| L5 | Authority change | Secrets, auth, users, exposed ports | Approval required, narrow token |
| L6 | Device/sensor | Mic, camera, clipboard, USB, radio | Approval required, visible grant |

## Example receipt

```yaml
receipt_id: 2026-06-02T21-14-33Z-openclaw-agent-0001
agent: openclaw-agent
task: "Install workspace skill in isolated mode"
workspace: /aegix/agents/openclaw-agent/workspace
capabilities_used:
  - files.write:/aegix/agents/openclaw-agent/workspace/skills
  - shell:npm_install_sandboxed
  - network:github.com
external_effects: []
verification:
  command: "agentctl verify openclaw-agent"
  result: "passed"
rollback:
  snapshot: "aegix-snapshot-0001"
status: committed
```

## Quick local start

```bash
git clone https://github.com/VE7LTX/aegix-os.git
cd aegix-os
nix flake check
nix run .#agentctl -- --help
nix run .#agentctl -- --root ./.aegix-preview doctor --json
nix run .#agentctl -- --root ./.aegix-preview paths --json
nix run .#agentctl -- --root ./.aegix-preview caps --json
nix run .#agentctl -- --root ./.aegix-preview run demo-agent --task "Create preview receipt" --workspace scratch/demo --json
nix run .#agentctl -- --root ./.aegix-preview receipts --json
nix run .#agentctl -- --root ./.aegix-preview events --json
nix run .#obsidianctl -- path
nix run .#aegix-vm
```

`agentctl` now includes Preview v0.2 session, receipt, event log, doctor, path map, capability, approval metadata, snapshot/checkpoint metadata, and rollback planning commands. `aegix-vm` builds the preview NixOS VM described in [docs/PREVIEW_VM.md](docs/PREVIEW_VM.md).

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.

Apache-2.0 was selected for this project because Aegix is expected to become infrastructure/system software, and Apache-2.0 includes a more explicit patent grant while remaining business-friendly and permissive.
