[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$Campaign,
    [Parameter(Mandatory = $true)][string]$ReportDirectory,
    [Parameter(Mandatory = $true)][string]$ReviewDirectory
)
$ErrorActionPreference = 'Stop'
$exitCode = 2
try {
    $repositoryPath = (Resolve-Path -LiteralPath $Repository).Path
    $pythonPath = Join-Path $repositoryPath '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw 'Python environment missing'
    }
    New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null
    $launchLogDirectory = Join-Path $ReportDirectory 'launcher_logs'
    New-Item -ItemType Directory -Path $launchLogDirectory -Force | Out-Null
    $runName = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmss') + '-' + [Guid]::NewGuid().ToString('N')
    Push-Location -LiteralPath $repositoryPath
    try {
        & $pythonPath -m app.shadow.scheduled tick --directory $Campaign --report-directory $ReportDirectory --review-directory $ReviewDirectory `
            1> (Join-Path $launchLogDirectory ($runName + '.stdout.log')) `
            2> (Join-Path $launchLogDirectory ($runName + '.stderr.log'))
        $exitCode = $LASTEXITCODE
    }
    finally { Pop-Location }
    if ($exitCode -eq 0 -or $exitCode -eq 3) { exit $exitCode }
    throw 'Observer returned a failure'
}
catch {
    # A fixed message avoids persisting exception/header/key values.
    try {
        New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null
        $failure = @{ failed_at = [DateTime]::UtcNow.ToString('o'); exit_code = $exitCode;
            issue = 'launcher_or_observer_failed'; message = 'Inspect local heartbeat and Task Scheduler result.' }
        $temporaryPath = Join-Path $ReportDirectory ('.launcher-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        [IO.File]::WriteAllText($temporaryPath, ($failure | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
        Move-Item -LiteralPath $temporaryPath -Destination (Join-Path $ReportDirectory 'launcher_failure.json') -Force
    }
    catch { Write-Error 'Could not write local launcher failure report.' -ErrorAction Continue }
    exit 2
}
