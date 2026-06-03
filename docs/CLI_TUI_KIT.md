# CLI and TUI Kit

Aegix OS should make terminal tools first-class for humans and agents. A terminal command with stable output is easier to document, approve, replay, and audit than a hidden mouse path.

## Required CLI tools

These should be available in the base developer/operator profile:

- `agentctl` for Aegix sessions, receipts, commands, approvals, and system views
- `aegixtui` for the first-entry operator home screen
- `obsidianctl` for Obsidian AI memory vault operations
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

## Codex CLI standard

`codexcli` is the Aegix-owned entrypoint for Codex CLI. It currently bootstraps the pinned npm package `@openai/codex@0.136.0` through Node/npm and keeps npm cache data under the operator cache path by default.

The compatibility command `codex` should remain available, but Aegix docs and receipts should prefer `codexcli` so policies can distinguish the distro-managed entrypoint from any host-installed Codex command.

Planned Aegix policy behavior:

- launch Codex inside a scoped project workspace
- route file, shell, network, and secret access through the capability broker
- write receipts for agent actions
- expose version and auth status through `agentctl codex`

## First-entry TUI standard

`aegixtui` should be the default first screen for the preview operator account. It is not a desktop shell; it is a console home screen that answers:

- what can I do here?
- where are the important files?
- which commands should I run first?
- are core services healthy?
- how do I get back to the shell?

The TUI should always preserve a clean console escape path. Pressing `q` exits to the normal shell, and `aegixtui` can be launched again manually.

## Agent rules

- Prefer CLI/TUI commands with documented outputs before desktop automation.
- Prefer `--json` output when available.
- Use Obsidian vault files for primary memory.
- Leave receipts for tool actions that change files, system state, network appliances, or external systems.
