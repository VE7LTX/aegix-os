# Aegix OS

**Aegix OS** is a security-first Linux agent appliance for running local AI agents with explicit capabilities, reversible actions, file-backed memory, and inspectable receipts.

> Not “Linux with an AI chatbot installed.” Aegix is an operating model for agents as first-class local actors: scoped authority, mandatory verification, and no silent external side effects.

## Status

Pre-MVP public scaffold. This repository is intended to become a reproducible test appliance first, then a proper installable agent-oriented Linux profile.

The first working target is a **NixOS VM/appliance profile**. A Fedora bootc/Atomic path is planned because Fedora is common in real homelab and workstation environments.

## Why this exists

Local AI agents are useful because they can touch the real machine: files, repos, browsers, services, calendars, CRMs, and automation jobs. That is also exactly why they are dangerous.

Aegix OS is built around one operating principle:

> Agents should be able to act locally with high leverage, but every risky boundary must be explicit, inspectable, temporary, and easy to revoke.

## Core laws

1. Agents are principals, not scripts.
2. Authority is capability-scoped, temporary, and revocable.
3. Memory is file-backed and inspectable.
4. Every meaningful action produces a receipt.
5. Dangerous actions require narrow approval tokens.
6. Host state is declarative.
7. Verification is mandatory.
8. Rollback is a first-class operation.
9. External side effects are never silent.
10. The human owns policy, not the model.

## MVP scope

The MVP is not a polished desktop distro. It is a reproducible agent appliance that can be safely tested on a spare machine or VM.

### Phase 0: Repository skeleton

- Public project README
- Architecture notes
- NixOS module skeleton
- OpenClaw native integration plan
- Capability policy examples
- Receipt schema
- CLI command design
- Security model

### Phase 1: Local appliance

- NixOS flake for a VM profile
- `agentd` session runner skeleton
- `capd` capability broker skeleton
- `agentctl` CLI skeleton
- Rootless Podman runtime
- Per-agent workspaces
- File-backed memory directories
- JSONL and Markdown receipts
- Read-only observer agent

### Phase 2: OpenClaw-native suite

- OpenClaw installed as a managed agent suite component
- OpenClaw skills mounted as scoped workspaces
- Skills wrapped by the Aegix capability broker
- OpenClaw gateway isolated from host authority
- Per-skill receipts and capability manifests

### Phase 3: Hardened runtime

- Per-agent network policy
- Secret broker
- Approval tokens
- Browser automation sandbox
- Snapshot/rollback integration
- MicroVM tier for untrusted workloads

## Recommended base

### Primary base: NixOS

NixOS is the cleanest first base because the system model is already declarative and rollback-oriented. That matches Aegix's desired host-state model.

### Secondary base: Fedora bootc / Atomic

Fedora bootc is a strong later path for building bootable OCI-derived systems. This matters because many practical machines, including homelab nodes and laptops, are already Fedora-oriented.

## OpenClaw position

OpenClaw should not be treated as “the OS.” It should be treated as a powerful native agent suite running inside Aegix boundaries.

Aegix should provide:

- OpenClaw install profile
- OpenClaw workspace layout
- OpenClaw skill policy wrapper
- OpenClaw secret mediation
- OpenClaw network policy
- OpenClaw receipt generator
- OpenClaw update/snapshot controls

OpenClaw gets the benefit of local tools. Aegix owns the boundary.

## Target file layout

```text
/aegix
  agents/
    observer-agent/
    code-agent/
    openclaw-agent/
  projects/
  memory/
  receipts/
  policy/
  secrets/
  snapshots/
  logs/
```

## Agent loop

```text
inspect -> classify risk -> request capability -> act -> verify -> receipt -> commit/rollback/escalate
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

## Quick local start, planned

```bash
git clone https://github.com/VE7LTX/aegix-os.git
cd aegix-os
nix flake check
nix run .#aegix-vm
```

The commands above are target commands. The current repository is a scaffold and planning base.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.

Apache-2.0 was selected for this project because Aegix is expected to become infrastructure/security software, and Apache-2.0 includes a more explicit patent grant while remaining business-friendly and permissive.
