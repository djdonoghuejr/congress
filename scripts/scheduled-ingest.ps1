param(
    [ValidateRange(1, 90)]
    [int]$SenateLookbackDays = 14
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDirectory = Join-Path $projectRoot "logs\ingestion"
$runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDirectory "scheduled-ingest-$runStamp.log"
$lockPath = Join-Path $logDirectory "scheduled-ingest.lock"
$lockStream = $null
$transcriptStarted = $false
$failures = [System.Collections.Generic.List[string]]::new()

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Start-Transcript -Path $logPath -Force | Out-Null
$transcriptStarted = $true

try {
    try {
        $lockStream = [System.IO.File]::Open(
            $lockPath,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    }
    catch [System.IO.IOException] {
        Write-Output "Another scheduled ingestion run is active; this run will exit."
        exit 0
    }

    if (-not (Test-Path -LiteralPath $python)) {
        throw "Project virtualenv Python was not found at $python. Create the venv and install the project first."
    }

    Push-Location $projectRoot
    try {
        $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
        if ($dockerCommand) {
            $dockerExe = $dockerCommand.Source
        }
        else {
            $dockerExe = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
        }
        if (-not (Test-Path -LiteralPath $dockerExe)) {
            throw "Docker CLI was not found on PATH or at $dockerExe. Start or repair Docker Desktop."
        }

        Write-Output "Ensuring the PostgreSQL container is running..."
        & $dockerExe compose up -d postgres
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose up failed with exit code $LASTEXITCODE. Is Docker Desktop running?"
        }

        $databaseReady = $false
        for ($attempt = 1; $attempt -le 30; $attempt++) {
            & $dockerExe compose exec -T postgres pg_isready -U postgres -d congress *> $null
            if ($LASTEXITCODE -eq 0) {
                $databaseReady = $true
                break
            }
            Start-Sleep -Seconds 2
        }
        if (-not $databaseReady) {
            throw "PostgreSQL did not become ready within 60 seconds."
        }

        $today = (Get-Date).Date
        $startDate = $today.AddDays(-$SenateLookbackDays).ToString("yyyy-MM-dd")
        $endDate = $today.ToString("yyyy-MM-dd")
        $skipBefore = $today.AddDays(-$SenateLookbackDays).ToString("yyyy-MM-dd")

        Write-Output "Running Senate ingestion for $startDate through $endDate..."
        & $python -m app.cli ingest-senate `
            --start-date $startDate `
            --end-date $endDate `
            --skip-existing-before $skipBefore
        if ($LASTEXITCODE -ne 0) {
            $failures.Add("Senate ingestion failed with exit code $LASTEXITCODE.")
        }

        if ((Get-Date).DayOfWeek -eq [System.DayOfWeek]::Sunday) {
            $houseYear = (Get-Date).Year
            Write-Output "Running weekly House ingestion for filing year $houseYear..."
            & $python -m app.cli ingest-house `
                --year $houseYear `
                --skip-existing-before $skipBefore
            if ($LASTEXITCODE -ne 0) {
                $failures.Add("House ingestion for $houseYear failed with exit code $LASTEXITCODE.")
            }
        }

        if ($failures.Count -gt 0) {
            $failures | ForEach-Object { Write-Error $_ }
            throw "Scheduled ingestion completed with $($failures.Count) failure(s). See this run's log."
        }
        Write-Output "Scheduled ingestion completed successfully."
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($null -ne $lockStream) {
        $lockStream.Dispose()
    }
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}
