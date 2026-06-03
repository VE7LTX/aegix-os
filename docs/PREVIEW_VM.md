# Aegix Preview VM

The preview VM is an Aegix-branded NixOS appliance profile for inspecting the current Aegix OS scaffold.

NixOS is still the reproducible base layer. The operator-facing console, login issue, message of the day, shell banner, filesystem layout, and installed tooling are branded and arranged around Aegix.

It includes:

- `/aegix` filesystem layout
- `agentctl` preview sessions, receipts, capabilities, events, doctor checks, approvals, and rollback placeholders
- `aegixtui`
- `codexcli` and `codex`
- `obsidianctl`
- `secretsctl`
- Obsidian vault folders
- Ollama service profile
- database/vector/time-series tool suite
- CLI/TUI operator tools
- terminal autologin as `operator`
- first-entry retro color TUI menu with help, demo sessions, receipts, capabilities, secrets, checks, paths, and shell handoff
- agent-readable event log at `/aegix/logs/events.jsonl`
- automatic file graph and SQLite search index under `/aegix/index`
- first-agent runbook at `/aegix/runbooks/first-agent.md`
- rollback policy scaffold at `/aegix/policy/rollback.yaml`
- Aegix console issue, MOTD, and shell banner
- quieter boot logging for a cleaner appliance-style startup

## Build

```bash
nix run .#aegix-vm
```

## Run

```bash
./result/bin/run-aegix-preview-vm
```

The preview is terminal-first. Login is automatic as `operator`; the password is `aegix` if needed.

After login, `aegixtui` opens as the first-entry operator menu. Press `q` to return to the shell. Run `aegixtui` again at any time to reopen the menu.

Early firmware lines from SeaBIOS, iPXE, or QEMU are expected in this VM preview. The OS login surface should present as Aegix OS Preview once the serial console starts.

## Inspect

```bash
aegixtui
agentctl status --json
agentctl doctor --json
agentctl paths --json
agentctl commands --json
agentctl caps --json
agentctl index --json
agentctl search-index Aegix --json
agentctl graph --json
agentctl run demo-agent --task "Create preview receipt" --workspace /aegix/scratch/demo --json
agentctl receipts --json
agentctl events --json
sid=$(basename "$(ls -1 /aegix/receipts/*.json | tail -n1)" .json)
agentctl inspect "$sid" --json
agentctl approve "$sid" --cap service.restart:ollama --json
agentctl snapshot "$sid" --json
agentctl rollback "$sid" --json
secretsctl status --json
secretsctl handles --json
codexcli --version
obsidianctl path --json
obsidianctl search Aegix --json
systemctl status aegix-agentd
systemctl status ollama
ls -la /aegix
```

`agentctl approve`, `agentctl snapshot`, and `agentctl rollback` are metadata scaffolds in this preview. They do not execute dangerous actions or destructive rollback.

Convenience aliases are available in the VM shell:

```bash
aegix-doctor
aegix-paths
aegix-index
aegix-search Aegix
aegix-graph
aegix-demo
aegix-receipts
aegix-events
aegix-failed
```

## Windows and WSL

From Windows, use Ubuntu WSL. If Nix is not installed yet, run this first in a visible PowerShell terminal so you can enter your WSL sudo password:

```powershell
.\scripts\setup-wsl-nix.ps1
```

Then launch the preview:

```powershell
.\scripts\launch-preview-vm.ps1
```

The script runs `nix run .#aegix-vm` inside Ubuntu WSL from this repository path.
