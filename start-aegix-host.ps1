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

function Test-PythonCurses {
  $oldPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & python -c "import curses" 2>$null
    return ($LASTEXITCODE -eq 0)
  } finally {
    $ErrorActionPreference = $oldPreference
  }
}

function Show-HostPreviewMenu {
  param(
    [string]$AgentctlPath,
    [string]$RootPath
  )

  while ($true) {
    Write-Host ""
    Write-Host "Aegix Host Preview Menu"
    Write-Host "  1. Doctor"
    Write-Host "  2. Verify control plane"
    Write-Host "  3. Run demo session"
    Write-Host "  4. Recent receipts"
    Write-Host "  5. Build file index"
    Write-Host "  6. File graph"
    Write-Host "  7. Capabilities"
    Write-Host "  q. Exit"
    $choice = Read-Host "Select"

    switch ($choice) {
      "1" { Invoke-AegixPython $AgentctlPath @("--root", $RootPath, "doctor", "--json") | Out-Host }
      "2" { Invoke-AegixPython $AgentctlPath @("--root", $RootPath, "verify", "--json") | Out-Host }
      "3" {
        $workspace = Join-Path $RootPath "scratch\demo"
        Invoke-AegixPython $AgentctlPath @("--root", $RootPath, "run", "demo-agent", "--task", "Host preview demo", "--workspace", $workspace, "--json") | Out-Host
      }
      "4" { Invoke-AegixPython $AgentctlPath @("--root", $RootPath, "receipts", "--json") | Out-Host }
      "5" { Invoke-AegixPython $AgentctlPath @("--root", $RootPath, "index", "--scope", $RootPath, "--max-files", "1000", "--json") | Out-Host }
      "6" { Invoke-AegixPython $AgentctlPath @("--root", $RootPath, "graph", "--json") | Out-Host }
      "7" { Invoke-AegixPython $AgentctlPath @("--root", $RootPath, "caps", "--json") | Out-Host }
      { $_ -in @("q", "Q", "quit", "exit") } { return }
      default { Write-Host "Unknown selection: $choice" }
    }
  }
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
  if (Test-PythonCurses) {
    Write-Host "Opening Aegix TUI in host preview mode. Press q to exit."
    & python $aegixtui
  } else {
    Write-Host "Python curses is not available on this Windows Python. Opening fallback host menu."
    Show-HostPreviewMenu -AgentctlPath $agentctl -RootPath $rootPath
  }
}
