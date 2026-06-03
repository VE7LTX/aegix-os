# Preview VM

The preview VM is a NixOS VM profile for inspecting the current Aegix OS scaffold.

It includes:

- `/aegix` filesystem layout
- `agentctl`
- `obsidianctl`
- Obsidian vault folders
- Ollama service profile
- database/vector/time-series tool suite
- CLI/TUI operator tools
- terminal autologin as `operator`

## Build

```bash
nix run .#aegix-vm
```

## Run

```bash
./result/bin/run-aegix-preview-vm
```

The preview is terminal-first. Login is automatic as `operator`; the password is `aegix` if needed.

## Inspect

```bash
agentctl status --json
agentctl commands --json
obsidianctl path --json
obsidianctl search Aegix --json
systemctl status aegix-agentd
systemctl status ollama
ls -la /aegix
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
