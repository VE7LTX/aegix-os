$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$wslRepo = wsl -d Ubuntu-22.04 -- wslpath -a "$repo"
$quotedWslRepo = "'" + ($wslRepo -replace "'", "'\''") + "'"

wsl -d Ubuntu-22.04 -- bash -lc "cd $quotedWslRepo && nix run .#aegix-vm && ./result/bin/run-aegix-preview-vm"
