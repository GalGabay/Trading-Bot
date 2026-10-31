[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param([switch]$StopRunning)
$ErrorActionPreference = 'Stop'
$repositoryPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$taskName = 'TradingBot-ShadowObserver'
$task = Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
if (-not $task) { Write-Output 'Shadow task is not installed.'; return }
if ($task.Description -ne ('TradingBot shadow-only observer | ' + $repositoryPath)) {
    throw 'Task ownership description differs; inspect it manually. Nothing removed.'
}
if ($task.State -eq 'Running' -and -not $StopRunning) {
    throw 'Task is running. Let it finish, or use -StopRunning and review interrupted recovery afterward.'
}
if ($PSCmdlet.ShouldProcess($taskName, 'Remove this repository shadow task; retain all reports and budgets')) {
    if ($task.State -eq 'Running') { Stop-ScheduledTask -TaskName $taskName -TaskPath '\' }
    Unregister-ScheduledTask -TaskName $taskName -TaskPath '\' -Confirm:$false
    Write-Output 'Task removed. Campaign, budgets, reports and logs retained.'
}
