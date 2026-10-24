param(
  [string]$FeatureAsOf = "2026-11-06T00:00:00Z"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDirectory = Join-Path $ProjectRoot "ai\quarantine\logs"
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogDirectory "target-watch-$Timestamp.log"

try {
  Push-Location $ProjectRoot
  $env:PYTHONPATH = "ai"
  & "$ProjectRoot\.venv\Scripts\python.exe" -m ai.cli watch-target-research `
    --intake-dir "ai\quarantine\intake" `
    --output-dir "ai\quarantine\predictions" `
    --model "ai\quarantine\artifacts\candidate-20261023T110126Z" `
    --registry "ai\quarantine\research-active.json" `
    --feature-as-of $FeatureAsOf *>&1 | Tee-Object -FilePath $LogFile
  exit $LASTEXITCODE
} catch {
  $_ | Out-String | Tee-Object -FilePath $LogFile -Append
  exit 1
} finally {
  Pop-Location -ErrorAction SilentlyContinue
}
