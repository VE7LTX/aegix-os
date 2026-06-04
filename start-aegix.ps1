param(
  [switch]$Restart,
  [switch]$Rebuild,
  [switch]$Gpu,
  [switch]$Ollama,
  [int]$MemoryMB = 4096,
  [int]$Cpus = 2
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$launchScript = Join-Path $repo "scripts\launch-preview-vm.ps1"
$vmPidFile = Join-Path $repo ".aegix-preview-vm.pid"

if (-not (Test-Path -LiteralPath $launchScript)) {
  throw "Could not find launcher: $launchScript"
}

function Get-AegixVmPid {
  param(
    [string]$RepoPath
  )

  $wslRepoPath = & wsl -d Ubuntu-22.04 -- wslpath -a "$RepoPath"
  $wslPidFile = "$wslRepoPath/.aegix-preview-vm.pid"

  $oldPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $pidTextOutput = @(& wsl -d Ubuntu-22.04 -- bash -lc "if [ -f '$wslPidFile' ]; then cat '$wslPidFile'; fi" 2>$null)
    $pidText = if ($pidTextOutput.Count -gt 0 -and $null -ne $pidTextOutput[0]) {
      $pidTextOutput[0].ToString().Trim()
    } else {
      ""
    }
    if (-not $pidText -or $pidText -notmatch '^\d+$') {
      return $null
    }

    $argsOutput = @(& wsl -d Ubuntu-22.04 -- bash -lc "ps -p $pidText -o args= 2>/dev/null || true" 2>$null)
    $argsLine = if ($argsOutput.Count -gt 0 -and $null -ne $argsOutput[0]) {
      $argsOutput[0].ToString()
    } else {
      ""
    }
    if ($argsLine -match 'qemu-system-x86_64.*aegix-preview') {
      return [int]$pidText
    }

    & wsl -d Ubuntu-22.04 -- bash -lc "rm -f '$wslPidFile'" 2>$null | Out-Null
    return $null
  } finally {
    $ErrorActionPreference = $oldPreference
  }
}

function Get-AegixVmProcessLine {
  $oldPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    return (& wsl -d Ubuntu-22.04 -- bash -lc "ps -eo pid,args | grep '[q]emu-system-x86_64.*aegix-preview' || true" 2>$null)
  } finally {
    $ErrorActionPreference = $oldPreference
  }
}

Write-Host "Aegix OS preview launcher"
Write-Host "Workspace: $repo"

$qemu = Get-AegixVmProcessLine
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
  $wslVmPidFile = & wsl -d Ubuntu-22.04 -- wslpath -a "$vmPidFile"
  $trackedPid = Get-AegixVmPid -RepoPath $repo
  if ($trackedPid) {
    & wsl -d Ubuntu-22.04 -- bash -lc "kill -TERM $trackedPid 2>/dev/null || true; rm -f '$wslVmPidFile'" 2>$null
  } else {
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & wsl -d Ubuntu-22.04 -- bash -lc "pkill -TERM -f 'qemu-system-x86_64.*aegix-preview' || true" 2>$null
    $ErrorActionPreference = $oldErrorActionPreference
  }
  Start-Sleep -Seconds 2
}

Write-Host "Starting Aegix preview VM..."
Write-Host "Memory (MB): $MemoryMB"
Write-Host "CPUs:      : $Cpus"
if ($Rebuild) {
  Write-Host "Rebuild:   : requested"
}
if ($Ollama -and -not $Gpu) {
  Write-Host "Starting Ollama-heavy VM profile (higher RAM/CPU)."
}
if ($Gpu -and -not $Ollama) {
  Write-Host "Starting GPU profile. On WSL this is currently graphics-enabled only."
}
if ($Gpu -and $Ollama) {
  Write-Host "Starting GPU + Ollama profile."
}

$launchArgs = @(
  "-NoProfile"
  "-ExecutionPolicy"
  "Bypass"
  "-File"
  $launchScript
  "-MemoryMB"
  "$MemoryMB"
  "-Cpus"
  "$Cpus"
)
if ($Rebuild) { $launchArgs += "-Rebuild" }
if ($Gpu) { $launchArgs += "-Gpu" }
if ($Ollama) { $launchArgs += "-Ollama" }
& "$PSHOME\powershell.exe" @launchArgs
