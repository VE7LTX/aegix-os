# CLI and TUI Kit

Aegix OS should make terminal tools first-class for humans and agents. A terminal command with stable output is easier to document, approve, replay, and audit than a hidden mouse path.

## Required CLI tools

These should be available in the base developer/operator profile:

- `agentctl` for Aegix sessions, receipts, commands, approvals, and system views
- `aegixtui` for the first-entry operator home screen
- `obsidianctl` for Obsidian AI memory vault operations
- `secretsctl` for secret handles, status, and policy without exposing values
- `codexcli` for Codex CLI access through the Aegix operator environment
- `codex` as a compatibility alias for operators who expect the upstream command name
- `git` for source control
- `ripgrep` for fast text search
- `fd` for file discovery
- `jq` and `yq` for structured data
- `bat` for readable file previews
- `eza` for directory listing
- `fzf` for fuzzy selection
- `zoxide` for path navigation
- `direnv` for project environments
- `just` for command recipes
- `sd` for safer structured replacements

## Required TUI tools

These should be available where a terminal interface is useful:

- `aegixtui` for first-run help, command menus, system checks, and shell handoff
- `tmux` for persistent sessions
- `neovim` and `helix` for terminal editing
- `lazygit` for Git inspection and staging
- `btop` for process and resource view
- `ncdu` for disk usage
- `glow` for Markdown viewing

## Obsidian CLI standard

`obsidianctl` is the Aegix-owned CLI for the Obsidian vault. It should stay boring and stable:

- `obsidianctl path`
- `obsidianctl init`
- `obsidianctl new "Title"`
- `obsidianctl search "text"`

The GUI Obsidian app can be installed separately, but agents should write and inspect memory through file-backed Markdown and `obsidianctl` first.

The shell shortcut `? question` sends the current shell context to local AI and writes the exchange into `/aegix/notes/obsidian/90-terminal-chat/` so it can be indexed like other memory.

## Codex CLI standard

`codexcli` is the Aegix-owned entrypoint for Codex CLI. It currently bootstraps the pinned npm package `@openai/codex@0.136.0` through Node/npm and keeps npm cache data under the operator cache path by default.

The compatibility command `codex` should remain available, but Aegix docs and receipts should prefer `codexcli` so policies can distinguish the distro-managed entrypoint from any host-installed Codex command.

Planned Aegix policy behavior:

- launch Codex inside a scoped project workspace
- route file, shell, network, and secret access through the capability broker
- write receipts for agent actions
- expose version and auth status through `agentctl codex`

## First-entry TUI standard

`aegixtui` should be the default first screen for the preview operator account. It is not a desktop shell; it is a console home screen with a retro ANSI-style color palette that answers:

- what can I do here?
- where are the important files?
- which commands should I run first?
- are core services healthy?
- what secret handles exist?
- how do I get back to the shell?

The TUI should always preserve a clean console escape path. Pressing `q` exits to the normal shell, and `aegixtui` can be launched again manually. Color should be used where the terminal supports it, with a monochrome fallback for limited serial consoles.

Preview v0.2 TUI entries:

- `Agent Doctor` checks writable paths, tool entrypoints, and failed systemd units.
- `Verify Control Plane` runs end-to-end Preview v0.2 checks and writes `/aegix/logs/verify/<report>.json`.
- `Aegix Paths` shows stable agent-facing paths and quick commands.
- `Build File Index` writes `/aegix/index` graph, SQLite FTS, and vector registry artifacts.
- `Search File Index` searches the local SQLite text index.
- `File Graph` shows indexed roots, graph paths, and vector registry status.
- `Run Demo Session` creates a scoped local session and JSON receipt.
- `Recent Receipts` lists receipt metadata.
- `Event Log` shows recent JSONL control-plane events.
- `Capabilities` shows the preview-friendly policy.
- `Approvals` lists approval token metadata.
- `Snapshots` lists snapshot metadata.

Preview v0.2 CLI commands:

- `agentctl doctor --json`
- `agentctl verify --json`
- `agentctl paths --json`
- `agentctl help run --json`
- `agentctl index --json`
- `agentctl search-index "rollback policy" --json`
- `agentctl graph --json`
- `agentctl run demo-agent --task "Create preview receipt" --workspace /aegix/scratch/demo --json`
- `agentctl receipts --json`
- `agentctl events --json`
- `agentctl inspect <session_id> --json`
- `agentctl caps --json`
- `agentctl approve <session_id> --cap service.restart:ollama --json`
- `agentctl snapshot <session_id> --json`
- `agentctl rollback <session_id> --json`

## Secrets CLI standard

`secretsctl` is the preview operator surface for secret management. It should report secret-store status, known handles, and policy rules, but it must not print raw secret values.

Preview commands:

- `secretsctl status --json`
- `secretsctl handles --json`
- `secretsctl policy --json`

The final backend should be `secretsd` with age/sops/pass-compatible storage and scoped broker calls for agents.

## Event log standard

Preview control commands append small JSONL records to `/aegix/logs/events.jsonl`. This is not the final audit log, but it gives agents and operators a simple timeline while receipts, approvals, and rollback metadata mature.

Use:

- `agentctl events --json`
- `tail -n 50 /aegix/logs/events.jsonl`

## Rollback scaffold standard

Preview rollback is metadata-only. `agentctl snapshot <session_id> --json` writes snapshot and checkpoint records, and `agentctl rollback <session_id> --json` reports the planned restore behavior without changing files.

`agentctl verify --json` proves this contract by creating a preview-safe session, taking metadata snapshots, running metadata-only rollback planning, and confirming the session artifact is unchanged. Its JSON includes `rollback_mode: metadata_only`.

The seeded policy file `/aegix/policy/rollback.yaml` documents the intended future backends: btrfs/ZFS snapshots, Nix generation rollback, and declarative config patch reversal.

## Verification standard

Use `agentctl verify --json` after boot, after CLI changes, and before demos. It checks:

- required Aegix paths and the preview capabilities policy
- session, receipt, approval, snapshot, and rollback metadata links
- file index, SQLite search, graph, vector registry scaffold, and event log
- `aegixai` status/diagnostics shape and command-suggestion non-execution

Reports are written under `/aegix/logs/verify/` and summarized in `/aegix/logs/events.jsonl`.

## Command help standard

Agent-facing commands should include `agent_help` in JSON output. That field should explain intent, when to use the command, examples, safety notes, and next steps.

Use:

- `agentctl help run --json`
- `agentctl commands --json`
- `obsidianctl path --json`
- `secretsctl policy --json`

## File graph standard

The file index lives under `/aegix/index` and is refreshed automatically in the preview VM by `aegix-index-refresh.service` and `aegix-index-refresh.timer`.

The source of truth remains normal files plus SQLite/JSON index artifacts. Vector DB storage is a secondary index planned through `/aegix/index/vector-registry.json`.

## Agent rules

- Prefer CLI/TUI commands with documented outputs before desktop automation.
- Prefer `--json` output when available.
- Use Obsidian vault files for primary memory.
- Leave receipts for tool actions that change files, system state, network appliances, or external systems.
