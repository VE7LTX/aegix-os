param(
    [int]$MemoryMB = 24576,
    [int]$Cpus = 6,
    [switch]$Gpu,
    [switch]$Ollama
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$wslRepo = wsl -d Ubuntu-22.04 -- wslpath -a "$repo"
$hostFallbackLimitMB = 16384
$minMemoryMB = 512
$preferredMemoryMB = $MemoryMB
$kvmAvailable = $false
$emulationMemoryCeilingMB = if ($Ollama) { 6144 } else { 4096 }
$emulationCpuCeiling = 2

if ($MemoryMB -lt $minMemoryMB) { throw "MemoryMB must be >= $minMemoryMB." }
if ($Cpus -lt 1) { throw "Cpus must be >= 1." }

$vmPackage = "aegix-vm"
if ($Gpu) {
  if ($Ollama) {
    $vmPackage = "aegix-vm-gpu-ollama"
  } else {
    $vmPackage = "aegix-vm-gpu"
  }
} elseif ($Ollama) {
  $vmPackage = "aegix-vm-ollama"
}

try {
  $wslMemText = wsl -d Ubuntu-22.04 -- cat /proc/meminfo 2>$null
  $memInfo = [string]::Join("`n", @($wslMemText))
  $memMatch = [regex]::Match($memInfo, "MemTotal:\s+(\d+)\s+kB")
  if ($memMatch.Success) {
    $wslMemFromHost = [int]$memMatch.Groups[1].Value / 1024
    $hostFallbackLimitMB = [int][Math]::Floor($wslMemFromHost)
  } else {
    $hostFallbackLimitMB = 16384
  }
} catch {
  $hostFallbackLimitMB = 16384
}

try {
  & wsl -d Ubuntu-22.04 -- bash -lc "test -r /dev/kvm -a -w /dev/kvm"
  if ($LASTEXITCODE -eq 0) {
    $kvmAvailable = $true
  }
} catch {
  $kvmAvailable = $false
}

if (-not $kvmAvailable) {
  Write-Host "KVM is not available in this WSL session. Aegix will use QEMU software emulation."
  if ($Cpus -gt $emulationCpuCeiling) {
    Write-Host "Clamping CPUs from $Cpus to $emulationCpuCeiling for TCG boot stability."
    $Cpus = $emulationCpuCeiling
  }
  if ($preferredMemoryMB -gt $emulationMemoryCeilingMB) {
    Write-Host "Clamping memory from $preferredMemoryMB MB to $emulationMemoryCeilingMB MB for software emulation."
    $preferredMemoryMB = $emulationMemoryCeilingMB
  }
}

$safeHostLimitMB = [Math]::Max($minMemoryMB, [Math]::Floor($hostFallbackLimitMB * 0.80))
if ($preferredMemoryMB -gt $safeHostLimitMB) {
  Write-Host "Requested memory ($preferredMemoryMB MB) exceeds host-safe WSL limit ($safeHostLimitMB MB)."
  Write-Host "Clamping launch memory to $safeHostLimitMB MB."
  $preferredMemoryMB = $safeHostLimitMB
}

$effectiveMemoryMB = $preferredMemoryMB

function Get-MemoryAttempts {
  param([int]$StartMB, [int]$MinimumMB)

  $seen = @{}
  $memory = $StartMB
  $attempts = @()

  while ($memory -ge $MinimumMB -and -not $seen.ContainsKey($memory)) {
    $attempts += $memory
    $seen[$memory] = $true
    $next = [Math]::Max($MinimumMB, [Math]::Floor($memory * 0.75))
    if ($next -eq $memory) {
      $next = $memory - 256
    }
    if ($next -lt $MinimumMB -or $next -eq $memory) {
      break
    }
    $memory = $next
  }

  return $attempts
}

function Invoke-AegixBuild {
  param([string]$Package, [string]$WslRepo, [int]$Memory, [int]$Cpus)

  $buildCommand = "cd '$WslRepo' && nix run .#$Package -- --memory `"$Memory`" --cpus `"$Cpus`""
  $oldErrorAction = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $output = wsl -d Ubuntu-22.04 -- bash -lc $buildCommand 2>&1
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $oldErrorAction

  if ($null -eq $output) {
    Write-Host "(no build output captured)"
  } else {
    $output | ForEach-Object { Write-Host $_ }
  }

  if ($exitCode -ne 0) {
    throw "Nix VM build failed with exit code $exitCode."
  }
}

function Invoke-AegixRun {
  param([int]$Memory, [int]$Cpus, [string]$WslRepo)

  $runScript = @'
set -euo pipefail

repo="$1"
memory="$2"
cpus="$3"

run_script_source="$(readlink -f "$repo/result/bin/run-aegix-preview-vm")"
run_script_target="$(mktemp -u "/tmp/run-aegix-preview-vm-${memory}M-${cpus}C-XXXXXX")"
pid_file="$repo/.aegix-preview-vm.pid"

cp "$run_script_source" "$run_script_target"
sed -i -E "s/-m [0-9]+/-m $memory/" "$run_script_target"
sed -i -E "s/-smp [0-9]+/-smp $cpus/" "$run_script_target"
sed -i -E 's/[[:space:]]+-nographic([[:space:]]|$)/ -display none -serial stdio -monitor none /' "$run_script_target"
chmod +x "$run_script_target"
printf '%s\n' "$$" > "$pid_file"

echo "Launching preview VM with ${memory}MB memory and ${cpus} CPUs."
exec "$run_script_target"
'@

  $encodedRunScript = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($runScript))
  $runCommand = "echo '$encodedRunScript' | base64 -d | bash -s -- '$WslRepo' '$Memory' '$Cpus'"

  $oldErrorAction = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $output = wsl -d Ubuntu-22.04 -- bash -lc $runCommand 2>&1
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $oldErrorAction

  if ($null -eq $output) {
    Write-Host "(no launch output captured for this attempt)"
  } else {
    $output | ForEach-Object { Write-Host $_ }
  }

  return [PSCustomObject]@{
    ExitCode = $exitCode
    MemoryMB = $Memory
    Output = ($output -join "`n")
  }
}

Invoke-AegixBuild -Package $vmPackage -WslRepo $wslRepo -Memory $effectiveMemoryMB -Cpus $Cpus

$retryCandidates = @(Get-MemoryAttempts -StartMB $effectiveMemoryMB -MinimumMB $minMemoryMB)
$lastAttempt = $null
foreach ($candidate in $retryCandidates) {
  Write-Host "Starting preview VM with $candidate MB (CPUs: $Cpus) ..."
  if (-not $kvmAvailable) {
    Write-Host "Serial boot can take 1-3 minutes under TCG. Boot logs should appear below."
  }
  $result = Invoke-AegixRun -Memory $candidate -Cpus $Cpus -WslRepo $wslRepo
  if ($result.ExitCode -eq 0) {
    exit 0
  }
  $lastAttempt = $result
  $memoryError = $result.Output -match "cannot set up guest memory 'pc\.ram': Cannot allocate memory"
  $nonRetryError = $result.Output -notmatch "Could not access KVM kernel module|failed to initialize kvm|Permission denied|failed to set up guest memory 'pc\.ram': Cannot allocate memory|Cannot allocate memory"

  if (-not $memoryError -and $nonRetryError) {
    throw "Preview VM launch failed before memory allocation fallback; see output above."
  }

  if ($candidate -eq $minMemoryMB) {
    break
  }

  Write-Host "Guest memory allocation failed. Retrying with lower memory..."
}

if ($null -ne $lastAttempt) {
  if ($lastAttempt.Output -match "cannot set up guest memory 'pc\.ram': Cannot allocate memory") {
    Write-Host ""
    Write-Host "Detected memory allocation failure in guest startup."
    Write-Host "Common fix: raise WSL memory limit in `%USERPROFILE%\\.wslconfig` and restart WSL:"
    Write-Host "  .wslconfig example: [wsl2]`nmemory=20GB`nprocessors=6"
    Write-Host "Then rerun: wsl --shutdown"
  }
  throw "Failed to launch preview VM after fallback attempts. Last attempt: $($lastAttempt.MemoryMB) MB. Check output above."
}

throw "No launch attempt could be started."
