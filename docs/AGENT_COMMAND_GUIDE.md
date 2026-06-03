# Agent Command Guide

Aegix commands should explain themselves to future agents.

Use `--json` by default and look for `agent_help` in command output. That field tells an agent what the command is for, when to use it, safety notes, expected JSON fields, and next commands.

## First Commands

```bash
agentctl doctor --json
agentctl paths --json
agentctl caps --json
agentctl commands --json
agentctl help run --json
```

## Session Flow

```bash
agentctl run demo-agent --task "Create preview receipt" --workspace /aegix/scratch/demo --json
agentctl receipts --json
agentctl inspect <session_id> --json
agentctl snapshot <session_id> --json
agentctl rollback <session_id> --json
```

## File Search Flow

```bash
agentctl index --json
agentctl search-index "rollback policy" --json
agentctl graph --json
```

The index writes:

- `/aegix/index/files.jsonl`
- `/aegix/index/graph.json`
- `/aegix/index/aegix_index.sqlite`
- `/aegix/index/vector-registry.json`

## Memory Flow

```bash
obsidianctl path --json
obsidianctl init --json
obsidianctl search Aegix --json
obsidianctl new "Agent handoff" --folder 40-agent-handoffs --json
```

Use Markdown files for durable memory. Do not write raw secrets into notes.

## Secrets Flow

```bash
secretsctl status --json
secretsctl handles --json
secretsctl policy --json
```

Secret handles are metadata, not raw values. Dangerous secret use needs approval metadata and a future broker.

