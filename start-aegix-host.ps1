param(
  [string]$Root = "",
  [switch]$NoTui
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) {
  $Root = Join-Path $repo ".aegix-host"
}
$rootPath = (New-Item -ItemType Directory -Force -Path $Root).FullName

$env:AEGIX_ROOT = $rootPath
$env:PYTHONUTF8 = "1"
$env:NO_COLOR = "1"

function Invoke-AegixPython {
  param(
    [string]$ToolPath,
    [string[]]$ToolArgs
  )

  & python $ToolPath @ToolArgs
}

$agentctl = Join-Path $repo "tools\agentctl\agentctl.py"
$aegixtui = Join-Path $repo "tools\aegixtui\aegixtui.py"

Write-Host "Aegix native host preview"
Write-Host "Workspace: $repo"
Write-Host "AEGIX_ROOT: $rootPath"
Write-Host ""
Write-Host "Bootstrapping local preview state..."

Invoke-AegixPython $agentctl @("--root", $rootPath, "doctor", "--json") | Out-Host
Invoke-AegixPython $agentctl @("--root", $rootPath, "paths", "--json") | Out-Host
Invoke-AegixPython $agentctl @("--root", $rootPath, "index", "--scope", $rootPath, "--max-files", "1000", "--json") | Out-Host

Write-Host ""
Write-Host "Useful host-preview commands:"
Write-Host "  `$env:AEGIX_ROOT = `"$rootPath`""
Write-Host "  python tools\agentctl\agentctl.py --root `"$rootPath`" verify --json"
Write-Host "  python tools\agentctl\agentctl.py --root `"$rootPath`" run demo-agent --task `"Preview`" --workspace `"$rootPath\scratch\demo`" --json"
Write-Host "  python tools\aegixtui\aegixtui.py"
Write-Host ""

if (-not $NoTui) {
  Write-Host "Opening Aegix TUI in host preview mode. Press q to exit."
  & python $aegixtui
}
