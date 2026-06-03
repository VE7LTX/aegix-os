$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$wslRepo = wsl -d Ubuntu-22.04 -- wslpath -a "$repo"
$quotedWslRepo = "'" + ($wslRepo -replace "'", "'\''") + "'"

param(
  [switch]$Gpu
)

$vmPackage = "aegix-vm"
if ($Gpu) {
  $vmPackage = "aegix-vm-gpu"
}

wsl -d Ubuntu-22.04 -- bash -lc "cd $quotedWslRepo && nix run .#$vmPackage && ./result/bin/run-aegix-preview-vm"
