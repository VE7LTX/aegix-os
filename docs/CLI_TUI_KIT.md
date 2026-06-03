# CLI and TUI Kit

Aegix OS should make terminal tools first-class for humans and agents. A terminal command with stable output is easier to document, approve, replay, and audit than a hidden mouse path.

## Required CLI tools

These should be available in the base developer/operator profile:

- `agentctl` for Aegix sessions, receipts, commands, approvals, and system views
- `obsidianctl` for Obsidian AI memory vault operations
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

## Agent rules

- Prefer CLI/TUI commands with documented outputs before desktop automation.
- Prefer `--json` output when available.
- Use Obsidian vault files for primary memory.
- Leave receipts for tool actions that change files, system state, network appliances, or external systems.
