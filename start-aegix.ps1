param(
  [switch]$Restart,
  [switch]$Gpu
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$launchScript = Join-Path $repo "scripts\launch-preview-vm.ps1"

if (-not (Test-Path -LiteralPath $launchScript)) {
  throw "Could not find launcher: $launchScript"
}

Write-Host "Aegix OS preview launcher"
Write-Host "Workspace: $repo"

$oldErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$qemu = & wsl -d Ubuntu-22.04 -- bash -lc "ps -eo pid,args | grep '[q]emu-system-x86_64.*aegix-preview' || true" 2>$null
$ErrorActionPreference = $oldErrorActionPreference
if ($qemu -and -not $Restart) {
  Write-Host ""
  Write-Host "Aegix preview VM already appears to be running:"
  Write-Host $qemu
  Write-Host ""
  Write-Host "Use this to restart it:"
  Write-Host "  .\start-aegix.ps1 -Restart"
  return
}

if ($Restart) {
  Write-Host "Stopping any existing Aegix preview VM..."
  $oldErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & wsl -d Ubuntu-22.04 -- bash -lc "pkill -TERM -f 'qemu-system-x86_64.*aegix-preview' || true" 2>$null
  $ErrorActionPreference = $oldErrorActionPreference
  Start-Sleep -Seconds 2
}

Write-Host "Starting Aegix preview VM..."
if ($Gpu) {
  & $launchScript -Gpu
} else {
  & $launchScript
}
