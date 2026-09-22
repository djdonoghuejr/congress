param(
    [string]$TaskName = "Congress Trades Scheduled Ingestion",
    [ValidatePattern("^([01]\d|2[0-3]):[0-5]\d$")]
    [string]$StartTime = "06:00"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ingestionScript = Join-Path $PSScriptRoot "scheduled-ingest.ps1"
$timeParts = $StartTime.Split(":")
$startBoundary = (Get-Date).Date.AddHours([int]$timeParts[0]).AddMinutes([int]$timeParts[1])

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ingestionScript`"" `
    -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $startBoundary
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 15) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)
$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Daily Senate and weekly House congressional trade disclosure ingestion." `
    -Force | Out-Null

Write-Output "Registered '$TaskName' to run daily at $StartTime. House ingestion runs on Sundays."
Write-Output "Run it once now in Task Scheduler to confirm Docker Desktop and database access."
