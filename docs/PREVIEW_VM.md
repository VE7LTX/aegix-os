# Aegix Preview VM

The preview VM is an Aegix-branded NixOS appliance profile for inspecting the current Aegix OS scaffold.

NixOS is still the reproducible base layer. The operator-facing console, login issue, message of the day, shell banner, filesystem layout, and installed tooling are branded and arranged around Aegix.

It includes:

- `/aegix` filesystem layout
- `agentctl`
- `codexcli` and `codex`
- `obsidianctl`
- Obsidian vault folders
- Ollama service profile
- database/vector/time-series tool suite
- CLI/TUI operator tools
- terminal autologin as `operator`
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

Early firmware lines from SeaBIOS, iPXE, or QEMU are expected in this VM preview. The OS login surface should present as Aegix OS Preview once the serial console starts.

## Inspect

```bash
agentctl status --json
agentctl commands --json
codexcli --version
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
