param(
  [string]$Destination = "ai/quarantine/manual-input/tokyo-20191019-10"
)

$ErrorActionPreference = "Stop"
$files = @{
  "official-race-card.csv" = "ai/samples/official-race-card.template.csv"
  "horses.csv" = "ai/samples/horses.template.csv"
  "jockeys.csv" = "ai/samples/jockeys.template.csv"
  "past_performances.csv" = "ai/samples/past_performances.template.csv"
  "source-review.json" = "ai/samples/manual-source-review.template.json"
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
foreach ($name in $files.Keys) {
  $target = Join-Path $Destination $name
  if (-not (Test-Path -LiteralPath $target)) {
    Copy-Item -LiteralPath $files[$name] -Destination $target
  }
}

Write-Output "Manual input folder is ready: $Destination"
Write-Output "Files were created only when absent; existing manual work was not overwritten."
