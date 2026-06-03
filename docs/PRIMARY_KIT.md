# Primary Kit

This document defines the default Aegix OS kit. The purpose is to make the machine easy for a new local AI agent to inspect, navigate, operate, remember, document, and hand off without relying on fragile desktop automation.

## Required by default

### AI operator interface

- `agentctl` CLI/TUI entrypoint
- `aegixtui` first-entry operator menu
- `obsidianctl` CLI for Obsidian AI memory
- `secretsctl` CLI for secret handles, status, and policy
- `aegixai` CLI for local Ollama chat and command suggestions
- `codexcli` CLI for Codex-assisted code and system work
- agent registry
- session history
- receipts
- approvals
- capability inspection
- rollback and replay commands
- plugin and MCP inspection
- appliance control inspection

### Native system access layer

Agents should get documented commands and APIs for common system work:

- files and directories
- apps and windows
- services and systemd units
- logs and journal queries
- network status and egress checks
- packages and declarative config proposals
- processes and resource use
- clipboard
- screenshots
- audio devices
- browser profiles
- MCP servers
- local API servers
- plugin registry
- local model services
- database services
- vector storage
- time-series storage
- workspace state

Mouse and keyboard automation should be a fallback, not the normal control path.

### Shortcut and command layer

All common custom shortcuts should be shipped as named commands:

- each command has a stable name
- each command has a short doc page
- each command declares inputs, outputs, side effects, required capabilities, verification, and rollback
- commands are listed through `agentctl commands`

Target layout:

```text
/aegix/commands/
  system.inspect/
  window.focus/
  browser.open_profile/
  screenshot.capture/
  clipboard.read/
  clipboard.write/
  service.status/
  logs.search/
  mcp.list_servers/
  api.list_services/
  router.status/
```

### Workspace system

The default filesystem should be predictable:

```text
/aegix
  agents/
  commands/
  projects/
  memory/
  models/
  data/
  notes/
  mcp/
  api/
  plugins/
  receipts/
  policy/
  secrets/
  appliances/
  snapshots/
  logs/
  screenshots/
  runbooks/
  scratch/
```

Project-local agent state should live beside the work:

```text
/projects/example/
  .agent/
    goals.md
    constraints.md
    receipts/
    checkpoints/
    task-state.sqlite
```

### Obsidian AI memory

Obsidian should be included as the standard human-readable AI memory system. It is where humans and agents should both be able to find the system map, operating notes, decisions, and handoff context.

`obsidianctl` is the standard CLI for agents and scripts. The GUI Obsidian app is useful for humans, but the agent path should be file-backed Markdown plus predictable CLI commands.

Default vault target:

```text
/aegix/notes/obsidian/
  00-inbox/
  10-runbooks/
  20-projects/
  30-decisions/
  40-agent-handoffs/
  50-receipts/
  60-system-map/
  70-shortcuts/
  80-troubleshooting/
  90-terminal-chat/
```

The vault should contain:

- system map
- machine inventory
- command catalog
- shortcut catalog
- plugin catalog
- MCP server catalog
- API server catalog
- appliance/router control catalog
- agent handoff notes
- project notes
- ADRs and decisions
- runbooks
- receipt index
- terminal chat transcripts
- memory index
- model routing notes
- troubleshooting notes

Primary agent memory should be written into this vault or into canonical project files first. Vector search and embeddings may index this material, but should not replace it as the source of truth.

### CLI and TUI tool kit

The terminal kit is defined in [CLI_TUI_KIT.md](CLI_TUI_KIT.md). The default profile should include fast, scriptable tools for search, navigation, editing, previews, Git, process inspection, disk usage, and Markdown reading.

The important rule is that agents should prefer documented command access over GUI automation whenever command access is available.

The first operator login should open `aegixtui`, a console home screen that shows help, common actions, core health checks, important paths, and a clear exit to the shell.

Codex CLI should be available through the Aegix-managed `codexcli` command, with `codex` kept as a compatibility alias. In the final system, Codex should run as an agent/tool client inside Aegix capability boundaries rather than as an unconstrained host shell.

Secret management should be visible from the first-entry TUI through `secretsctl`. The preview surface should show status, handles, and policy, never raw secret values.

### OpenClaw managed suite

OpenClaw should be installed as a managed suite component:

- scoped workspace
- scoped memory
- documented tool access
- capability policy wrapper
- isolated browser profile
- receipt generation
- upgrade snapshot
- agent handoff page

OpenClaw should not receive broad host authority by default.

### Plugin, MCP, and API server layer

Aegix should make AI-facing integrations first-class and inspectable:

- local MCP server registry
- local API server registry
- plugin registry
- tool manifests
- schema documentation
- capability requirements
- side-effect declarations
- health checks
- version and update notes
- receipt hooks

Target layout:

```text
/aegix/mcp/
  servers/
  manifests/
  policies/
/aegix/api/
  services/
  schemas/
  health/
/aegix/plugins/
  installed/
  available/
  policies/
```

MCP servers and plugins should not become ambient authority. They should sit behind the same capability, secret, network, and approval model as every other tool.

### Network, router, and appliance controls

Aegix should include documented appliance controls for the systems a homelab/workstation agent is likely to touch:

- router status
- DNS records
- DHCP leases
- firewall rules
- port forwards
- VPN status
- Wi-Fi status
- NAS status
- backup jobs
- UPS status
- local service health

These controls should be API-first where possible. Browser automation should be reserved for routers or appliances that do not expose usable APIs.

Router and appliance writes should require approval by default:

- firewall changes
- port forwards
- DNS changes
- DHCP reservations
- VPN changes
- public exposure changes
- credential changes

### Developer tools

Default developer profile:

- VS Code
- Git
- Python
- Node.js
- Nix
- Podman
- ripgrep
- fd
- jq
- yq
- bat
- eza
- fzf
- zoxide
- direnv
- tmux
- neovim
- helix
- lazygit
- btop
- ncdu
- glow
- just
- sd
- tree-sitter
- language servers
- test runners

### Browser automation

Default browser profiles:

- research
- admin
- testing
- openclaw
- risky/disposable

Profiles should have separate cookies, downloads, history, and permissions.

### Local model tools

Default local model profile should support:

- Ollama service
- `aegixai` native terminal copilot
- default starter model `qwen3.5:0.8b`
- llama.cpp adapter
- model cache directory
- model registry notes
- local/cloud routing policy
- data classification rules
- cost and budget controls

Ollama should be available as the first local model service because it gives agents a simple local API for model discovery and inference. The default Aegix posture should bind Ollama to localhost, store model state under `/aegix/models/ollama`, and require explicit policy before exposing it to the LAN.

The native copilot should be small, local, and bounded. It may answer questions, suggest commands, and write growth proposals, but it should not silently execute commands, pull larger models, install packages, restart services, or change auth.

See [LOCAL_MODELS.md](LOCAL_MODELS.md) for the service profile.

### Data service suite

Aegix should include a documented data service suite because agents need boring storage for memory, indexes, metrics, receipts, queues, and local application state.

Default data paths:

```text
/aegix/data/
  sqlite/
  postgres/
  vector/
  timeseries/
  cache/
  warehouse/
```

Default options:

- SQLite for local app state, task state, and small indexes
- Postgres for durable multi-user/project services
- DuckDB for local analytical work
- Redis-compatible cache/queue where needed
- Qdrant or equivalent vector storage for embeddings over canonical files
- Prometheus-compatible time-series storage for metrics and service health

Vector storage is an index, not the source of truth. Obsidian Markdown, project files, receipts, and structured DB records remain canonical.

See [DATA_SERVICES.md](DATA_SERVICES.md) for the storage profiles.

### Documentation rules

Every built-in command or tool should document:

- purpose
- examples
- inputs
- outputs
- side effects
- required capabilities
- verification method
- rollback method
- common failure modes

## Optional profile

These should be available but not required on every install:

- dashboard web UI
- NAS management profile
- CRM/email/calendar integration node
- research/RAG node
- local vector index
- microVM runtime
- backup server integration
- media/device access profile
- Home Assistant or homelab integration
- advanced router vendor packs

## Experimental

These should remain clearly marked until proven:

- multi-agent scheduling
- model router
- MCP gateway
- local API gateway
- policy-generated UI
- signed receipts
- remote attestation
- agent marketplace
- disposable VM workflows
- browser action replay

## Not included yet

These are intentionally not part of the first kit:

- broad root shell access for agents
- raw long-lived secrets in agent environments
- silent outbound email or CRM writes
- automatic public posting
- unreviewed privileged OpenClaw skill installation
- hidden primary memory stores
- production hardening claims

## First implementation target

The first practical build should make these commands real:

- `agentctl status`
- `aegixtui`
- `agentctl commands`
- `agentctl inspect`
- `agentctl receipts`
- `agentctl secrets`
- `agentctl notes`
- `agentctl codex`
- `agentctl openclaw`
- `agentctl obsidian`
- `agentctl plugins`
- `agentctl mcp`
- `agentctl api`
- `agentctl router`
- `agentctl appliances`
- `agentctl models`
- `agentctl ollama`
- `agentctl db`
- `agentctl vector`
- `agentctl timeseries`
- `agentctl screenshot`
- `agentctl logs`
- `agentctl services`
- `obsidianctl path`
- `obsidianctl init`
- `obsidianctl new`
- `obsidianctl search`

Each one should start as a small, boring, documented system interface that an agent can call reliably.
