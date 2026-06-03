# Roadmap

## Phase 0: Public Scaffold

- README, license, notice, contribution rules, and security policy
- primary kit, CLI/TUI kit, architecture, security model, OpenClaw, and roadmap docs
- flake with `agentctl` and placeholder `aegix-vm` commands
- NixOS module skeleton
- policy and receipt examples
- CI that checks flake evaluation and Python syntax when Nix is available

## Phase 1: Local Appliance

- runnable NixOS VM profile
- `agentctl` command groups
- `agentd` session runner
- `capd` capability broker
- rootless Podman runtime
- per-agent directories
- Obsidian vault profile
- `obsidianctl` vault CLI
- terminal/TUI operator tools
- MCP/API server profile
- plugin registry
- Ollama local model service profile
- database/vector/time-series service profile
- documented shortcut command registry
- JSONL receipts
- read-only observer agent

## Phase 2: Managed Agent Suite

- OpenClaw native integration profile
- MCP-compatible tool gateway behind the broker
- local API server registry
- network/router appliance control profile
- approval tokens
- secret broker
- workspace snapshots
- local model router
- Ollama health/model inventory commands
- database service inventory commands
- vector and time-series service inventory commands

## Phase 3: Hardened Runtime

- per-agent egress policy
- browser automation isolation
- microVM tier
- signed receipts
- multi-node policy packs
- dashboard for active agents, diffs, capabilities, secrets, and pending approvals
