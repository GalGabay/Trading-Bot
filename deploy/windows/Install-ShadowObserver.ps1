[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param([string]$ReviewDirectory = '')
$ErrorActionPreference = 'Stop'
$repositoryPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($ReviewDirectory)) {
    $ReviewDirectory = Join-Path $repositoryPath 'data\shadow\schedule\review'
}
$pythonPath = Join-Path $repositoryPath '.venv\Scripts\python.exe'
Push-Location -LiteralPath $repositoryPath
try {
    & $pythonPath -m app.shadow.schedule verify --review-directory $ReviewDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Reviewed files or campaign preflight failed; nothing installed.' }
}
finally { Pop-Location }
$manifestPath = Join-Path $ReviewDirectory 'manifest.json'
$manifest = [IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
if ($manifest.platform -ne 'windows') { throw 'This review is not a Windows task definition.' }
$currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if ($manifest.windows_user_sid -ne $currentSid) { throw 'Reviewed principal differs from the current Windows user.' }
$taskName = 'TradingBot-ShadowObserver'
if (Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue) {
    throw 'Task already exists. Review/remove that task explicitly before a new installation.'
}
$xmlPath = Join-Path $ReviewDirectory 'windows-task.xml'
$xmlText = [IO.File]::ReadAllText($xmlPath)
$taskService = New-Object -ComObject Schedule.Service
$taskService.Connect()
$definition = $taskService.NewTask(0)
$definition.XmlText = $xmlText
if ($PSCmdlet.ShouldProcess($taskName, 'Register current-user shadow observation task; eligible triggers may run soon')) {
    Register-ScheduledTask -TaskName $taskName -TaskPath '\' -Xml $xmlText | Out-Null
    Write-Output 'Task registered. An eligible or missed trigger may run soon; inspect local reports and Task Scheduler.'
}
