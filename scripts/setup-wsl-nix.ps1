$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$wslRepo = wsl -d Ubuntu-22.04 -- wslpath -a "$repo"
$quotedWslRepo = "'" + ($wslRepo -replace "'", "'\''") + "'"

wsl -d Ubuntu-22.04 -- bash -lc "cd $quotedWslRepo && bash scripts/setup-wsl-nix.sh"
